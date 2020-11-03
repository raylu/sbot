import base64
import copy
import hashlib
import mimetypes
import hmac
import os
import time
import urllib.parse

import requests

import config

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

def post(bot):
	rs = requests.Session()
	message_id = '316960031314804737'
	channel = config.bot.twitter_post['channel']
	message = bot.get('/channels/%s/messages/%s' % (channel, message_id))
	media_ids = []
	upload_url = 'https://upload.twitter.com/1.1/media/upload.json'
	for attachment in message['attachments'][:4]:
		media = rs.get(attachment['url']).content

		media_type, _ = mimetypes.guess_type(attachment['filename'])
		rs = requests.Session()
		response = signed_request(rs, 'POST', upload_url, params={
			'command': 'INIT',
			'media_type': media_type,
			'total_bytes': str(attachment['size']),
		})
		media_id = response.json()['media_id_string']

		response = signed_request(rs, 'POST', upload_url, params={
			'command': 'APPEND',
			'media_id': media_id,
			'segment_index': '0',
		}, files={'media': media})

		response = signed_request(rs, 'POST', upload_url, params={
			'command': 'FINALIZE',
			'media_id': media_id,
		})

		media_ids.append(media_id)

	discord_link = 'https://discord.com/channels/%s/%s/%s' % (
			config.bot.twitter_post['server'], config.bot.twitter_post['channel'], message_id)
	tweet = '%s on %s\n%s' % (message['author']['username'], message['timestamp'][:10], discord_link)
	response = signed_request(rs, 'POST', 'https://api.twitter.com/1.1/statuses/update.json', {
		'status': tweet,
		'media_ids': ','.join(media_ids),
		'trim_user': '1',
	}, {})

def tweet_id_to_ts(tweet_id):
	# https://github.com/client9/snowflake2time#snowflake-layout
	return (tweet_id & 0x7fffffffffffffff) >> 22

def signed_request(rs, method, url, params=None, data=None, files=None):
	signing_params = {
		'oauth_consumer_key': config.bot.twitter_post['consumer_key'],
		'oauth_nonce': base64.b64encode(os.getrandom(16)),
		'oauth_signature_method': 'HMAC-SHA1',
		'oauth_timestamp': str(int(time.time())),
		'oauth_version': '1.0',
		'oauth_token': config.bot.twitter_post['token'],
	}
	final_data = None
	headers = {}
	if files:
		# https://github.com/oauthlib/oauthlib/blob/bda81b3cb6306dec19a6e60113e21b2933d0950c/oauthlib/oauth1/rfc5849/__init__.py#L212
		request = requests.Request(method, url, data=data, files=files).prepare()
		signing_params['oauth_body_hash'] = base64.b64encode(hashlib.sha1(request.body).digest())
		final_data = request.body
		headers['Content-Type'] = request.headers['Content-Type']
	auth_params = copy.copy(signing_params)
	if params:
		signing_params.update(params)
	if data:
		signing_params.update(data)
		if not files:
			final_data = data

	consumer_secret = config.bot.twitter_post['consumer_secret']
	token_secret = config.bot.twitter_post['token_secret']
	auth_params['oauth_signature'] = sign(method, url,
			signing_params, consumer_secret, token_secret)
	# https://developer.twitter.com/en/docs/authentication/oauth-1-0a/authorizing-a-request
	auth = 'OAuth '
	auth += ', '.join('%s="%s"' % (k, urllib.parse.quote(v)) for k, v in auth_params.items())
	headers['Authorization'] = auth
	response = rs.request(method, url, params=params, data=final_data, headers=headers)
	response.raise_for_status()
	return response

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
