import datetime
import html
import re
import time
import xml.etree.ElementTree

import requests

import config

def news(bot):
	rs = requests.Session()

	for game_id, channel_id in config.bot.steam_news.items():
		last_dt = config.state.steam_news_dts.get(game_id, datetime.datetime.min)
		embeds = []
		r = rs.get('https://steamcommunity.com/games/427520/rss')
		r.raise_for_status()
		tree = xml.etree.ElementTree.fromstring(r.text)
		first_item_dt = None
		for item in tree.iter('item'):
			pub_date = item.findtext('pubDate')
			dt = datetime.datetime.strptime(pub_date, '%a, %d %b %Y %H:%M:%S %z').replace(tzinfo=None)
			if first_item_dt is None:
				first_item_dt = dt
			if dt <= last_dt:
				break # items are newest first

			title = item.findtext('title')
			description = item.findtext('description')
			link = item.findtext('link')
			author = item.findtext('author')

			description_text = re.sub(r'<[^>]+>', '', html.unescape(description))
			embeds.append({
				'title': title, 'description': description_text[:2500], 'url': link, 'author': {'name': author},
			})

		for embed in reversed(embeds):
			bot.send_message(channel_id, '<%s>' % embed['url'], embed)
			time.sleep(2)
		config.state.steam_news_dts[game_id] = first_item_dt
	config.state.save()
