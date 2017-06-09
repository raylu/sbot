import datetime
from math import sqrt
import operator
import time
from xml.dom import minidom
import xml.parsers.expat

import psycopg2
import requests

import config

rs = requests.Session()
rs.headers.update({'User-Agent': 'sbot'})
if config.bot.eve_dsn is not None:
	db = psycopg2.connect(config.bot.eve_dsn)

crest_price_cache = {'last_update': 0, 'items': {}}
def price_check(cmd):
	def get_prices(typeid, system=None, region=None):
		url = 'http://api.eve-central.com/api/marketstat'
		params = {'typeid': typeid}
		if system: params['usesystem'] = system
		if region: params['regionlimit'] = region
		try:
			dom = minidom.parseString(rs.get(url, params=params).text)
		except xml.parsers.expat.ExpatError:
			return None

		buy = dom.getElementsByTagName('buy')[0]
		buy_max = buy.getElementsByTagName('max')[0]
		bid = float(buy_max.childNodes[0].data)

		sell = dom.getElementsByTagName('sell')[0]
		sell_min = sell.getElementsByTagName('min')[0]
		ask = float(sell_min.childNodes[0].data)

		all_orders = dom.getElementsByTagName('all')[0]
		all_volume = all_orders.getElementsByTagName('volume')[0]
		volume = int(all_volume.childNodes[0].data)

		return bid, ask, volume
	def __item_info(curs, query):
		curs.execute('''
			SELECT "typeID", "typeName" FROM "invTypes"
			WHERE LOWER("typeName") LIKE %s AND "marketGroupID" IS NOT NULL
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
	def item_info(item_name):
		with db.cursor() as curs:
			# exact match
			curs.execute(
					'SELECT "typeID", "typeName" FROM "invTypes" WHERE LOWER("typeName") LIKE %s',
					(item_name.lower(),))
			result = curs.fetchone()
			if result:
				return result

			# start of string match
			results = __item_info(curs, item_name + '%')
			if isinstance(results, tuple):
				return results
			if results:
				names = map(lambda r: r[1], results)
				cmd.reply('Found items: ' + ', '.join(names))
				return

			# substring match
			results = __item_info(curs, '%' + item_name + '%')
			if isinstance(results, tuple):
				return results
			if results:
				names = map(lambda r: r[1], results)
				cmd.reply('Found items: ' + ', '.join(names))
				return
			cmd.reply('Item not found')
	def format_prices(prices):
		if prices is None:
			return 'n/a'
		if prices[1] < 1000.0:
			return 'bid {0:g} ask {1:g} vol {2:,d}'.format(*prices)
		prices = map(int, prices)
		return 'bid {0:,d} ask {1:,d} vol {2:,d}'.format(*prices)
	def get_crest_price(typeid):
		now = time.time()
		if crest_price_cache['last_update'] < now - 60 * 60 * 2:
			res = rs.get('https://crest-tq.eveonline.com/market/prices/')
			if res.status_code == 200:
				crest_price_cache['items'].clear()
				for item in res.json()['items']:
					crest_price_cache['items'][item['type']['id']] = item
					del item['type']
				crest_price_cache['last_update'] = now
		prices = crest_price_cache['items'].get(typeid)
		if prices and 'averagePrice' in prices:
			if prices['averagePrice'] < 1000.0:
				return 'avg {averagePrice:g} adj {adjustedPrice:g}'.format(**prices)
			for k, v in prices.items():
				prices[k] = int(v)
			return 'avg {averagePrice:,d} adj {adjustedPrice:,d}'.format(**prices)
		else:
			return 'n/a'

	args = cmd.args
	result = item_info(args)
	if not result:
		return
	typeid, item_name = result
	jita_system = 30000142
	amarr_system = 30002187
	jita_prices = get_prices(typeid, system=jita_system)
	amarr_prices = get_prices(typeid, system=amarr_system)
	jita = format_prices(jita_prices)
	amarr = format_prices(amarr_prices)
	crest = get_crest_price(typeid)
	cmd.reply('%s\nJita: %s\nAmarr: %s\nCREST: %s' % (item_name, jita, amarr, crest))

def jumps(cmd):
	split = cmd.args.split()
	if len(split) != 2:
		cmd.reply('usage: `!jumps [from] [to]`')
		return
	with db.cursor() as curs:
		curs.execute('''
				SELECT "solarSystemName" FROM "mapSolarSystems"
				WHERE LOWER("solarSystemName") LIKE %s OR LOWER("solarSystemName") LIKE %s
				''', (split[0].lower() + '%', split[1].lower() + '%')
		)
		results = list(map(operator.itemgetter(0), curs.fetchmany(2)))
	query = [None, None]
	for i, s in enumerate(split):
		s = s.lower()
		for r in results:
			if r.lower().startswith(s):
				query[i] = r
				break
		else:
			cmd.reply('could not find system starting with ' + s)
			break
	if None in query:
		return
	r = rs.get('http://api.eve-central.com/api/route/from/%s/to/%s' % (query[0], query[1]))
	try:
		data = r.json()
	except ValueError:
		cmd.reply('error getting jumps')
		return
	jumps_split = []
	for j in data:
		j_str = j['to']['name']
		from_sec = j['from']['security']
		to_sec = j['to']['security']
		if from_sec != to_sec:
			j_str += ' (%0.1g)' % to_sec
		jumps_split.append(j_str)
	cmd.reply('%d jumps: %s' % (len(data), ', '.join(jumps_split)))

def lightyears(cmd):
	split = [n + '%' for n in cmd.args.lower().split()]
	if len(split) != 2:
		cmd.reply('usage: !ly [from] [to]')
		return

	with db.cursor() as curs:
		curs.execute('''
				SELECT "solarSystemName", x, y, z FROM "mapSolarSystems"
				WHERE LOWER("solarSystemName") LIKE %s OR LOWER("solarSystemName") LIKE %s
				''', split)
		result = curs.fetchmany(6)
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
		('other:', 3.5),
		('blackops:', 4.0),
		('jump freighter:', 5.0),
		('super:', 3.0),
	]
	jdc = []
	for ship, jump_range in ship_ranges:
		for level in range(0, 6):
			if dist <= jump_range * (1 + level * 0.2):
				jdc.append('%s %d' % (ship, level))
				break
		else:
			jdc.append(ship + ' N/A')
	cmd.reply('%s ⟷ %s: %.3f ly\n%s' % (result[0][0], result[1][0], dist, '\n'.join(jdc)))

def who(cmd):
	dt_format = '%Y-%m-%dT%H:%M:%SZ'
	try:
		r = rs.get('https://api.eveonline.com/eve/CharacterId.xml.aspx', params={'names': cmd.args})
		r.raise_for_status()
		dom = minidom.parseString(r.text)
		row = dom.getElementsByTagName('row')[0]
		char_id = int(row.attributes['characterID'].nodeValue)

		r = rs.get('https://esi.tech.ccp.is/v4/characters/%d/' % char_id)
		r.raise_for_status()
		data = r.json()
		char_name = data['name']
		corp_id = int(data['corporation_id'])
		birthday = data['birthday']
		birthday = datetime.datetime.strptime(birthday, dt_format).date()
		security_status = data['security_status']
		output = '%s: born %s, security status %.2f  ' % (char_name, birthday, security_status)
		output += 'https://zkillboard.com/character/%d/' % char_id

		r = rs.get('https://esi.tech.ccp.is/v3/corporations/%d/' % corp_id)
		r.raise_for_status()
		data = r.json()
		corp_name = data['corporation_name']
		creation_date = data.get('creation_date') # NPC corps have no creation_date
		if creation_date:
			creation_date = datetime.datetime.strptime(creation_date, dt_format).date()
		else:
			creation_date = '?'
		members = data['member_count']
		alliance_id = data.get('alliance_id')
		output += '\n%s: created %s, %s members  ' % (corp_name, creation_date, members)
		output += 'https://zkillboard.com/corporation/%d/' % (corp_id)

		if alliance_id:
			alliance_id = int(alliance_id)
			r = rs.get('https://esi.tech.ccp.is/v2/alliances/%d/' % alliance_id)
			r.raise_for_status()
			data = r.json()
			alliance_name = data['alliance_name']
			founding_date = data['date_founded']
			founding_date = datetime.datetime.strptime(founding_date, dt_format).date()
			output += '\n%s: founded %s' % (alliance_name, founding_date)

		cmd.reply(output)
	except requests.exceptions.HTTPError:
		cmd.reply("%s: couldn't find your sleazebag" % cmd.sender['username'])
