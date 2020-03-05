import time

import requests

import config

if config.bot.twitch is not None:
	rs = requests.Session()
	rs.headers['Client-ID'] = config.bot.twitch['client_id']

	ANNOUNCE_FREQ = 4 * 60 * 60 # announce once every 4h

def live_streams(bot):
	now = time.time()
	user_to_announce = {}
	for announce in config.bot.twitch['announces']:
		url = 'https://api.twitch.tv/helix/streams?'
		if 'game_id' in announce:
			url += 'game_id=%d' % announce['game_id']
		else:
			url += 'user_id=%d' % announce['user_id']
		r = rs.get(url)
		r.raise_for_status()
		for stream in r.json()['data']:
			user_id = stream['user_id']
			# don't announce if we've announced in the last ANNOUNCE_FREQ
			last_announce = config.state.twitch_last_times.get(user_id)
			if last_announce is not None and now - last_announce < ANNOUNCE_FREQ:
				continue
			config.state.twitch_last_times[user_id] = now

			thumbnail_url = stream['thumbnail_url'].replace('{width}', '256').replace('{height}', '144')
			embed = {
				'title': stream['title'],
				'image': {'url': thumbnail_url},
			}
			# store user_id because the stream URL cannot be derived from the stream['user_name']
			user_to_announce[user_id] = (announce['channel'], embed)

	if user_to_announce:
		# get stream URLs for all user_ids
		params = (('id', user_id) for user_id in user_to_announce.keys())
		r = rs.get('https://api.twitch.tv/helix/users', params=params)
		r.raise_for_status()
		for user in r.json()['data']:
			channel, embed = user_to_announce[user['id']]
			embed['url'] = 'https://www.twitch.tv/' + user['login']
			embed['author'] = {
				'name': user['display_name'],
				'icon_url': user['profile_image_url'],
			}
			bot.send_message(channel, '<%s>' % embed['url'], embed)
			time.sleep(2)

	# clean up last announce times older than ANNOUNCE_FREQ
	to_del = []
	for user_id, last_live in config.state.twitch_last_times.items():
		if now - last_live > ANNOUNCE_FREQ:
			to_del.append(user_id)
	for user_id in to_del:
		del config.state.twitch_last_times[user_id]
	config.state.save()
