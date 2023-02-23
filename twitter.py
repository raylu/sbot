import base64
import datetime
import math
import mimetypes
import hmac
import io
import time
import urllib.parse

import PIL.Image
import requests
import requests_oauthlib

import config
import log
import timer

def new_tweets(bot):
	rs = requests.Session()
	for account, channel_id in config.bot.twitter['accounts'].items():
		last_tweet = config.state.tweet_ids.get(account)
		if last_tweet:
			last_tweet_timestamp = tweet_id_to_ts(last_tweet)
		else:
			last_tweet_timestamp = 0

		r = rs.get('https://api.twitter.com/1.1/statuses/user_timeline.json',
			params={'screen_name': account, 'count': 25, 'tweet_mode': 'extended'},
			headers={'Authorization': 'Bearer ' + config.bot.twitter['bearer_token']})
		r.raise_for_status()
		embeds = []
		tweets = r.json()
		for tweet in tweets:
			timestamp = tweet_id_to_ts(tweet['id'])
			if timestamp <= last_tweet_timestamp:
				break # tweets are newest first

			if len(tweet['entities']['user_mentions']) > 0:
				continue

			author_url = 'https://twitter.com/' + account
			embed = {
				'description': tweet['full_text'],
				'url': author_url + '/status/' + tweet['id_str'],
				'author': {'name': account, 'url': author_url, 'icon_url': tweet['user']['profile_image_url_https']},
			}
			media = tweet['entities'].get('media')
			if media:
				embed['image'] = {'url': media[0]['media_url_https'] + ':small'}
			embeds.append(embed)

		for embed in reversed(embeds):
			bot.send_message(channel_id, '<%s>' % embed['url'], embed)
			time.sleep(2)
		config.state.tweet_ids[account] = tweets[0]['id']
	config.state.save()

MAX_SIZE = 5000000

def post(bot, message_id):
	rs = requests.Session()
	channel = config.bot.twitter_post['channel']
	message = bot.get_message(channel, message_id)

	oauth = requests_oauthlib.OAuth1(config.bot.twitter_post['consumer_key'],
	  client_secret=config.bot.twitter_post['consumer_secret'],
	  resource_owner_key=config.bot.twitter_post['token'],
	  resource_owner_secret=config.bot.twitter_post['token_secret'])
	media_ids = []
	upload_url = 'https://upload.twitter.com/1.1/media/upload.json'
	for attachment in message['attachments'][:4]:
		media = rs.get(attachment['url']).content

		media_type, _ = mimetypes.guess_type(attachment['filename'])
		if media_type.startswith('image/'):
			media = optimize_image(media)
			media_type = 'image/jpeg'
			if len(media) > MAX_SIZE:
				log.write("skipping %s %s because we couldn't compress to under 5MB" %
						(message_id, attachment['filename']))
				continue
		response = rs.post(upload_url, data={
			'command': 'INIT',
			'media_type': media_type,
			'total_bytes': str(len(media)),
		}, auth=oauth)
		response.raise_for_status()
		media_id = response.json()['media_id_string']

		response = rs.post(upload_url, data={
			'command': 'APPEND',
			'media_id': media_id,
			'segment_index': '0',
		}, files={'media': media}, auth=oauth)
		response.raise_for_status()

		response = rs.post(upload_url, data={
			'command': 'FINALIZE',
			'media_id': media_id,
		}, auth=oauth)
		response.raise_for_status()

		media_ids.append(media_id)

	if len(media_ids) > 0:
		discord_link = 'https://discord.com/channels/%s/%s/%s' % (
				config.bot.twitter_post['server'], config.bot.twitter_post['channel'], message_id)
		tweet = '%s on %s\n%s' % (message['author']['username'], message['timestamp'][:10], discord_link)
		response = rs.post('https://api.twitter.com/1.1/statuses/update.json', data={
			'status': tweet,
			'media_ids': ','.join(media_ids),
			'trim_user': '1',
		}, auth=oauth)
		response.raise_for_status()
		log.write('tweeted %s' % response.json()['id'])

		emoji = 'shrfood_twitter:773023524683251766'
		path = '/channels/%s/messages/%s/reactions/%s/@me' % (channel, message_id, emoji)
		bot.post(path, None, method='PUT')
	else:
		log.write('skipping %s because no media' % message_id)

def queue_info(cmd):
	if config.bot.twitter_post is None or config.bot.twitter_post['channel'] != cmd.channel_id:
		return
	reply = 'queue length: %d' % len(config.state.twitter_queue)
	if len(config.state.twitter_queue) > 0:
		reply += '\nnext post: https://discord.com/channels/%s/%s/%s' % (
				cmd.d['guild_id'], config.bot.twitter_post['channel'], config.state.twitter_queue[0])
	if config.state.twitter_last_post_time:
		next_post_s = 12 * 60 * 60 - (time.time() - config.state.twitter_last_post_time)
		reply += '\nnext post in: ' + timer.readable_rel(datetime.timedelta(seconds=next_post_s))
	cmd.reply(reply)

def tweet_id_to_ts(tweet_id):
	# https://github.com/client9/snowflake2time#snowflake-layout
	return (tweet_id & 0x7fffffffffffffff) >> 22

def sign(method, url, signing_params, consumer_secret, token_secret):
	# https://developer.twitter.com/en/docs/authentication/oauth-1-0a/creating-a-signature
	# https://github.com/oauthlib/oauthlib/blob/d54965b86ce4ede956db70baff0b3d5e9182a007/oauthlib/oauth1/rfc5849/utils.py#L52
	parameter_string = urllib.parse.urlencode(sorted(signing_params.items()),
			quote_via=urllib.parse.quote, safe='~')
	# that's right! we re-quote the parameter string
	encoded_params = urllib.parse.quote_plus(parameter_string)
	base_string = '%s&%s&%s' % (method, urllib.parse.quote_plus(url), encoded_params)
	signing_key = '%s&%s' % (urllib.parse.quote(consumer_secret), urllib.parse.quote(token_secret))
	mac = hmac.HMAC(signing_key.encode('ascii'), base_string.encode('ascii'), 'sha1')
	return base64.b64encode(mac.digest()).decode('ascii')

def optimize_image(media: bytes) -> bytes:
	image = PIL.Image.open(io.BytesIO(media))
	if image.mode == 'RGBA':
		image = image.convert('RGB') # JPEG doesn't support alpha

	max_dim = max(image.width, image.height)
	if max_dim <= 8192 and len(media) <= MAX_SIZE: # no optimization needed
		return media

	if max_dim > 8192:
		divisor = math.ceil(max_dim / 8192)
		image = image.resize((image.width // divisor, image.height // divisor))

	output = io.BytesIO()
	image.save(output, 'JPEG', optimize=True)
	if len(output.getbuffer()) > MAX_SIZE:
		output = io.BytesIO()
		image.save(output, 'JPEG', optimize=True, quality='web_low')
	return output.getvalue()
