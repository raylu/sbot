import operator
import urllib

import psycopg2
import requests

import config

rs = requests.Session()
rs.headers.update({'User-Agent': 'sbot'})
db = psycopg2.connect(config.eve_dsn)

def calc(client, message, args):
    response = rs.get('https://www.calcatraz.com/calculator/api', params={'c': args})
    client.send_message(message.channel, response.text.rstrip())

def roll(client, message, args):
    if not args:
        args = '1d6'
    response = rs.get('https://rolz.org/api/?' + urllib.parse.quote_plus(args))
    split = response.text.split('\n')
    details = split[2].split('=', 1)[1].strip()
    details = details.replace(' +', ' + ').replace(' +  ', ' + ')
    result = split[1].split('=', 1)[1]
    client.send_message(message.channel, '%s %s' % (result, details))

def price_check(client, message, args):
	def get_prices(typeid, system=None, region=None):
		from xml.dom import minidom
		import xml.parsers.expat

		url = 'http://api.eve-central.com/api/marketstat'
		params = {'typeid': typeid}
		if system: params['usesystem'] = system
		if region: params['regionlimit'] = region
		try:
			xml = minidom.parseString(rs.get(url, params=params).text)
		except xml.parsers.expat.ExpatError:
			return None

		buy = xml.getElementsByTagName('buy')[0]
		buy_max = buy.getElementsByTagName('max')[0]
		bid = float(buy_max.childNodes[0].data)

		sell = xml.getElementsByTagName('sell')[0]
		sell_min = sell.getElementsByTagName('min')[0]
		ask = float(sell_min.childNodes[0].data)

		all_orders = xml.getElementsByTagName('all')[0]
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
				client.send_message(message.channel, 'Found items: ' + ', '.join(names))
				return

			# substring match
			results = __item_info(curs, '%' + item_name + '%')
			if isinstance(results, tuple):
				return results
			if results:
				names = map(lambda r: r[1], results)
				client.send_message(message.channel, 'Found items: ' + ', '.join(names))
				return
			client.send_message(message.channel, 'Item not found')
	def format_prices(prices):
		if prices is None:
			return 'n/a'
		if prices[1] < 1000.0:
			return 'bid {0:g} ask {1:g} vol {2:,d}'.format(*prices)
		prices = map(int, prices)
		return 'bid {0:,d} ask {1:,d} vol {2:,d}'.format(*prices)

	if args.lower() == 'plex':
		args = "30 Day Pilot's License Extension (PLEX)"
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
	client.send_message(message.channel, '%s - Jita: %s ; Amarr: %s' % (item_name, jita, amarr))

def jumps(client, message, args):
	split = args.split()
	if len(split) != 2:
		client.send_message(message.channel, 'usage: `!jumps [from] [to]`')
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
			client.send_message(message.channel, 'could not find system starting with ' + s)
			break
	if None in query:
		return
	r = rs.get('http://api.eve-central.com/api/route/from/%s/to/%s' % (query[0], query[1]))
	try:
		jumps = r.json()
	except ValueError:
		client.send_message(message.channel, 'error getting jumps')
		return
	jumps_split = []
	for j in jumps:
		j_str = j['to']['name']
		from_sec = j['from']['security']
		to_sec = j['to']['security']
		if from_sec != to_sec:
			j_str += ' (%0.1g)' % to_sec
		jumps_split.append(j_str)
	client.send_message(message.channel, '%d jumps: %s' % (len(jumps), ', '.join(jumps_split)))

handlers = {
    'calc': calc,
    'pc': price_check,
    'price': price_check,
    'roll': roll,
    'jumps': jumps,
}
