import time

import requests

import config

if config.bot.twitch is not None:
	rs = requests.Session()
	rs.headers['Client-ID'] = config.bot.twitch['client_id']

	users = {}
	ANNOUNCE_FREQ = 4 * 60 * 60 # announce once every 4h

def live_streams(bot):
	for announce in config.bot.twitch['announces']:
		url = 'https://api.twitch.tv/helix/streams?'
		if 'game_id' in announce:
			url += 'game_id=%d' % announce['game_id']
		else:
			url += 'user_id=%d' % announce['user_id']
		r = rs.get(url)
		r.raise_for_status()
		now = time.time()
		for stream in r.json()['data']:
			try:
				if now - users[stream['user_id']] < ANNOUNCE_FREQ:
					continue
			except KeyError:
				users[stream['user_id']] = now

			thumbnail_url = stream['thumbnail_url'].replace('{width}', '256').replace('{height}', '144')
			embed = {
				'url': 'https://www.twitch.tv/' + stream['user_name'],
				'title': stream['title'],
				'image': {'url': thumbnail_url},
				'author': {'name': stream['user_name']},
			}
			bot.send_message(announce['channel'], '<%s>' % embed['url'], embed)
			time.sleep(2)

	to_del = []
	for user_id, last_live in users.items():
		if now - last_live > ANNOUNCE_FREQ:
			to_del.append(user_id)
	for user_id in to_del:
		del users[user_id]
