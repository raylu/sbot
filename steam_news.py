import html
import re
import time
import xml.etree.ElementTree

import requests

import config

def news(bot):
	rs = requests.Session()

	for game_id, channel_id in config.bot.steam_news.items():
		last_ann_id = config.state.steam_news_ids.get(game_id, 0)
		first_ann_id = None
		embeds = []
		r = rs.get('https://steamcommunity.com/games/%s/rss' % game_id)
		r.raise_for_status()
		tree = xml.etree.ElementTree.fromstring(r.text)
		for item in tree.iter('item'):
			ann_id = int(item.findtext('guid').rsplit('/', 1)[1])
			if first_ann_id is None:
				first_ann_id = ann_id
			if ann_id <= last_ann_id:
				break # items are newest first

			title = item.findtext('title')
			description = item.findtext('description')
			link = item.findtext('link')
			author = item.findtext('author')

			description_text = re.sub(r'<[^>]+>', ' ', html.unescape(description))
			embeds.append({
				'title': title, 'description': description_text[:1000], 'url': link, 'author': {'name': author},
			})

		for embed in reversed(embeds):
			bot.send_message(channel_id, '<%s>' % embed['url'], embed)
			time.sleep(2)
		config.state.steam_news_ids[game_id] = first_ann_id
	config.state.save()
