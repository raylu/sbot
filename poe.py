#!/usr/bin/env python3

import json
import time

import requests

rs = requests.Session()

league_name = None

def price(cmd):
	global league_name

	if league_name is None:
		league_name = _get_league_name()

	names, lines = _search(league_name, cmd.args)
	if len(names) == 0:
		cmd.reply("couldn't find " + cmd.args)
	elif len(names) > 1:
		cmd.reply(', '.join(names))
	else:
		responses = []
		for line in lines:
			name = line['name']
			if line['links'] > 0:
				name += ' (%d link)' % line['links']
			response = '%s: %.1f chaos' % (name, line['chaosValue'])
			if line['exaltedValue'] > 1.0:
				response += ', %.1f exalted' % line['exaltedValue']
			responses.append(response)
		cmd.reply('\n'.join(responses))

def _get_league_name():
	html = rs.get('https://poe.ninja/')
	prefix = 'window.leagues = '
	for line in html.text.split('\n'):
		if prefix in line:
			start = line.index(prefix) + len(prefix)
			end = line.find('];</script>') + 1
			doc = line[start:end]
			break
	else:
		raise Exception("Couldn't find leagues JSON")

	leagues = json.loads(doc)
	for league_info in leagues:
		if league_info['url'] == 'challenge':
			return league_info['name']

pages = [
	'UniqueArmour',
	'UniqueWeapon',
	'UniqueAccessory',
	'UniqueJewel',
	'UniqueFlask',
	'UniqueMap',
	'DivinationCard',
	'Prophecy',
	'HelmetEnchant',
]

def _search(league, q):
	q = q.casefold()
	names = set()
	matches = []
	for page in pages:
		data = _query(page, league)
		lines = data['lines']
		for line in lines:
			if q in line['name'].casefold():
				names.add(line['name'])
				matches.append(line)
		if len(names) > 0:
			# there may be other matches on other pages, but we won't bother finding them
			break
	return names, matches

cache = {}

def _query(page, league):
	cached = cache.get((page, league))
	now = time.time()
	if cached is not None:
		ts, data = cached
		if ts > now - 60 * 60: # cache for 1 hour
			return data

	data = rs.get('https://poe.ninja/api/data/itemoverview?league=%s&type=%s' % (league, page)).json()
	cache[(page, league)] = now, data
	return data
