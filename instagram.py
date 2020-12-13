import time

import requests

import config

def new_media(bot):
	rs = requests.Session()
	for insta_conf in config.bot.instagram:
		r = rs.get('https://graph.instagram.com/me/media', params={
			'fields': 'username,caption,timestamp,permalink,media_type,media_url,thumbnail_url',
			'access_token': insta_conf['token'],
		})
		r.raise_for_status()
		data = r.json()['data']
		if not data:
			continue

		# media comes most recent first
		last_timestamp = config.state.instagram.get(insta_conf['user_id'])
		if last_timestamp is None:
			# never seen this account before; post only the most recent image
			post_media(bot, insta_conf['channels'], data[0])
		else:
			for media in reversed(data):
				if media['timestamp'] <= last_timestamp:
					continue
				post_media(bot, insta_conf['channels'], media)
				time.sleep(2)
		config.state.instagram[insta_conf['user_id']] = data[0]['timestamp']
		config.state.save()

def post_media(bot, channel_ids, media):
	embed = {
		'description': media['caption'],
		'url': media['permalink'],
		'author': {
			'name': media['username'],
			'url': 'https://www.instagram.com/%s/' % media['username'],
		},
	}
	if media['media_type'] == 'IMAGE':
		embed['image'] = {'url': media['media_url']}
	elif media['media_type'] == 'VIDEO':
		embed['thumbnail'] = {'url': media['thumbnail_url']}
	for channel_id in channel_ids:
		bot.send_message(channel_id, '<%s>' % media['permalink'], embed)

def main():
	# pylint: disable=import-outside-toplevel
	import bot

	new_media(bot.Bot({}))

if __name__ == '__main__':
	main()
