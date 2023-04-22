import operator
import sqlite3
import time
from math import sqrt

import requests

import config

rs = requests.Session()
rs.headers.update({'User-Agent': 'sbot'})
if config.bot.eve_db is not None:
	db = sqlite3.connect(config.bot.eve_db)

esi_price_cache = {'last_update': 0, 'items': {}}


def price_check(cmd):
	def __item_info(query):
		curs = db.execute('''
			SELECT "typeID", "typeName" FROM "invTypes"
			WHERE LOWER("typeName") LIKE ? AND "marketGroupID" IS NOT NULL
			''', (query.lower(),))
		results = curs.fetchmany(3)
		if len(results) == 1:
			return results[0]
		if len(results) == 2 and \
                        results[0][1].endswith('Blueprint') ^ results[1][1].endswith('Blueprint'):
			# an item and its blueprint; show the item
			if results[0][1].endswith('Blueprint'):
				return results[1]
			else:
				return results[0]
		if len(results) >= 2:
			return results
		return None

	def item_info(item_name):
		# exact match
		curs = db.execute(
			'SELECT "typeID", "typeName" FROM "invTypes" WHERE LOWER("typeName") LIKE ?',
			(item_name.lower(),))
		result = curs.fetchone()
		if result:
			return result

		# start of string match
		results = __item_info(item_name + '%')
		if isinstance(results, tuple):
			return results
		if results:
			names = map(lambda r: r[1], results)
			cmd.reply('Found items: ' + ', '.join(names))
			return None

		# substring match
		results = __item_info('%' + item_name + '%')
		if isinstance(results, tuple):
			return results
		if results:
			names = map(lambda r: r[1], results)
			cmd.reply('Found items: ' + ', '.join(names))
			return None
		cmd.reply('Item not found')
		return None

	def get_esi_price(typeid):
		now = time.time()
		if esi_price_cache['last_update'] < now - 60 * 60 * 2:
			res = rs.get(
				'https://esi.evetech.net/latest/markets/prices/?datasource=tranquility')
			if res.status_code == 200:
				esi_price_cache['items'].clear()
				for item in res.json():
					esi_price_cache['items'][item['type_id']] = item
		prices = esi_price_cache['items'][typeid]
		if prices and 'average_price' in prices:
			if prices['average_price'] < 1000.0:
				return 'avg {average_price:g} adj {adjusted_price:g}'.format(**prices)
			for k, v in prices.items():
				prices[k] = int(v)
			return 'avg {average_price:,d} adj {adjusted_price:,d}'.format(**prices)
		else:
			return 'n/a'

	if not cmd.args:
		return
	result = item_info(cmd.args)
	if not result:
		return
	typeid, item_name = result
	try:
		esi = get_esi_price(typeid)
		cmd.reply('%s: %s' % (item_name, esi))
	except KeyError:
		cmd.reply('error: could not find %r in ESI market prices' % item_name)


def jumps(cmd):
	split = cmd.args.split()
	if not 2 <= len(split) <= 3:
		cmd.reply('usage: `!jumps [from] [to] (safe|shortest)`')
		return
	results = []
	for i in range(2):
		curs = db.execute('''
			SELECT "solarSystemID" FROM "mapSolarSystems"
			WHERE "solarSystemName" LIKE ? LIMIT 3
			''', (split[i],))
		matches = list(map(operator.itemgetter(0), curs.fetchall()))
		if len(matches) == 0:
			cmd.reply('no systems found for {}'.format(split[i]))
			return
		assert len(matches) == 1, f'more than 1 system found for {split[i]}'
		results.append(matches[0])

	if len(split) == 3 and split[2] in ['safe', 'secure']:
		flag = 'secure'
	else:
		flag = 'shortest'

	r = rs.get('https://esi.evetech.net/latest/route/{}/{}/?datasource=tranquility&flag={}'.format(
			results[0], results[1], flag))
	try:
		data = r.json()
	except ValueError:
		cmd.reply('error getting jumps')
		return
	jumps_split = []
	for j in data:
		curs.execute('''SELECT "solarSystemName", "security"
						FROM "mapSolarSystems"
						WHERE "solarSystemID" = ?''', (j,))
		system_name, security = curs.fetchone()
		if security >= 0.45:
			sec_emoji = 'green_apple'
		elif security > 0.0:
			sec_emoji = 'yellow_heart'
		else:
			sec_emoji = 'red_circle'
		jumps_split.append(':%s: %s' % (sec_emoji, system_name))
	cmd.reply('{} jumps:\n'.format(len(jumps_split)-1) + ' \u2192 '.join(jumps_split))


def lightyears(cmd):
	split = [n + '%' for n in cmd.args.lower().split()]
	if len(split) != 2:
		cmd.reply('usage: !ly [from] [to]')
		return

	curs = db.execute('''
		SELECT "solarSystemName", x, y, z FROM "mapSolarSystems"
		WHERE LOWER("solarSystemName") LIKE ? OR LOWER("solarSystemName") LIKE ?
		LIMIT 6
		''', (split[0], split[1]))
	result = curs.fetchall()
	if len(result) < 2:
		cmd.reply('error: one or both systems not found')
		return
	elif len(result) > 2:
		cmd.reply('error: found too many systems: ' + ' '.join(map(operator.itemgetter(0), result)))
		return

	dist = 0
	for d1, d2 in zip(result[0][1:], result[1][1:]):
		dist += (d1 - d2)**2
	dist = sqrt(dist) / 9.4605284e15 # meters to lightyears
	ship_ranges = [
		('other:\t ', 3.5),
		('blops:\t ', 4.0),
		('JF:\t\t', 5.0),
		('super:\t ', 3.0),
	]
	jdc = []
	for ship, jump_range in ship_ranges:
		for level in range(0, 6):
			if dist <= jump_range * (1 + level * 0.2):
				jdc.append('%s%d' % (ship, level))
				break
		else:
			jdc.append(ship + 'N/A')
	cmd.reply('```%s ⟷ %s: %.3f ly\n%s```' %
		(result[0][0], result[1][0], dist, '\n'.join(jdc)))


def who(cmd):
	if len(cmd.args) == 0:
		cmd.reply('usage: !who [name]')
		return

	char_info, corp_info, alliance_info = None, None, None
	entity_type_map = {
		0: 'characterID',
		1: 'corporationID',
		2: 'allianceID',
	}

	def get_char_info(char_id):
		r = rs.get('https://esi.evetech.net/latest/characters/{}/'.format(char_id), params={'datasource': 'tranquility'})
		r.raise_for_status()
		char_info = r.json()
		killed, lost = get_zkill_stats(char_id, 0)
		return char_info, killed, lost

	def get_corp_info(corp_id):
		r = rs.get('https://esi.evetech.net/latest/corporations/{}/'.format(corp_id), params={'datasource': 'tranquility'})
		r.raise_for_status()
		corp_info = r.json()
		active_members = get_group_actives(corp_id, 1)
		return corp_info, active_members

	def get_alliance_info(alliance_id):
		r = rs.get('https://esi.evetech.net/latest/alliances/{}/'.format(alliance_id), params={'datasource': 'tranquility'})
		r.raise_for_status()
		alliance_info = r.json()
		active_members = get_group_actives(alliance_id, 2)
		return alliance_info, active_members

	def get_zkill_stats(entity_id, entity_type):
		r = rs.get('https://zkillboard.com/api/stats/{entity_type}/{entity_id}/'.format(
				entity_id=entity_id, entity_type=entity_type_map[entity_type]))
		r.raise_for_status()
		stats = r.json()
		killed = stats.get('shipsDestroyed', 0)
		lost = stats.get('shipsLost', 0)
		return killed, lost

	def get_group_actives(entity_id, entity_type):
		r = rs.get('https://zkillboard.com/api/stats/{entity_type}/{entity_id}/'.format(
				entity_type=entity_type_map[entity_type], entity_id=entity_id))
		r.raise_for_status()
		data = r.json()
		try:
			return data['activepvp']['characters']['count']
		except KeyError:
			return 0

	try:
		r = rs.post('https://esi.evetech.net/latest/universe/ids/',
				params={'datasource': 'tranquility', 'language': 'en-us'},
				json=[cmd.args])
		r.raise_for_status()
	except requests.exceptions.HTTPError:
		cmd.reply('{}: esi error'.format(cmd.sender['username']))
		return

	initial_id = r.json()
	if len(initial_id) == 0:
		cmd.reply("%s: couldn't find your sleazebag" % cmd.sender['username'])
		return

	corp_id = alliance_id = None
	output = ''
	if 'characters' in initial_id:
		try:
			char_info, killed, lost = get_char_info(initial_id['characters'][0]['id'])
		except requests.exceptions.HTTPError:
			cmd.reply("%s: couldn't find your sleazebag" % cmd.sender['username'])

		corp_id = char_info['corporation_id']
		output += '{name} ({security:.2f}) [{killed}/{lost}]\n'.format(
				name=char_info['name'], security=char_info['security_status'], killed=killed, lost=lost)

	try:
		if 'corporations' in initial_id or char_info:
			if not char_info:
				corp_id = initial_id['corporations'][0]['id']
			corp_info, active_members = get_corp_info(corp_id)
			alliance_id = corp_info.get('alliance_id')
			output += '{name} [{ticker}] {active} active members\n'.format(
					name=corp_info['name'], ticker=corp_info['ticker'], active=active_members)

		if 'alliances' in initial_id or alliance_id is not None:
			if alliance_id is None:
				alliance_id = initial_id['alliances'][0]['id']
			alliance_info, active_members = get_alliance_info(alliance_id)
			output += '{name} <{ticker}> {active} active members'.format(
					name=alliance_info['name'], ticker=alliance_info['ticker'], active=active_members)
	except requests.exceptions.HTTPError:
		output += 'esi or zkb error looking up corporation/alliance'

	cmd.reply('```' +output + '```')
