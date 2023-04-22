#!/usr/bin/env python3

import html.parser
import time

import requests

rs = requests.Session()

league_names = None

def price(cmd):
	global league_names

	if league_names is None:
		league_names = _get_league_names()

	if not cmd.args:
		return
	names, lines = _search(league_names[0], cmd.args)
	if len(names) == 0:
		cmd.reply("couldn't find " + cmd.args)
	elif len(names) > 1:
		cmd.reply(', '.join(names)[:250])
	else:
		icon = None
		for line in lines:
			icon = line.get('icon')
			if icon is not None:
				break

		fields = [
			{'name': league_names[0], 'value': '\n'.join(_build_responses(lines))},
		]
		for league_name in league_names[1:]:
			_, lines = _search(league_name, cmd.args)
			fields.append({'name': league_names[0], 'value': '\n'.join(_build_responses(lines))})

		embed = {'thumbnail': {'url': icon}, 'fields': fields}
		cmd.reply('', embed=embed)

def _get_league_names():
	r = rs.get('https://poe.ninja/api/data/getindexstate')
	r.raise_for_status()
	leagues = r.json()['economyLeagues']

	ret = []
	standard_league = None
	for league_info in leagues:
		if league_info['url'] in ('challenge', 'event'):
			ret.append(league_info['name'])
		elif league_info['url'] == 'standard':
			standard_league = league_info['name']
	if len(ret) > 0:
		return ret
	else:
		return [standard_league]

def _build_responses(lines):
	responses = []
	for line in lines:
		name = line.get('name')
		if name is None: # currency
			name = line['currencyTypeName']
			bid = line['receive']['value']
			ask = 1 / line['pay']['value']
			if bid > 1.0:
				response = 'bid 1 : %.2f chaos' % bid
			else:
				response = 'bid %.2f : 1 chaos' % (1 / bid)
			if ask > 1.0:
				response += '\nask 1 : %.2f chaos' % ask
			else:
				response += '\nask %.2g : 1 chaos' % (1 / ask)
		else: # item
			if line.get('icon', '').endswith('&relic=1'):
				name += ' (relic)'
			if line.get('links', 0) > 0:
				name += ' (%d link)' % line['links']
			if line.get('gemLevel'):
				name += ' (level %d)' % line['gemLevel']
			if line.get('gemQuality'):
				name += ' (%d%%)' % line['gemQuality']
			if line.get('mapTier'):
				name += ' (T%d)' % line['mapTier']
			if line.get('corrupted'):
				name += ' (corrupted)'
			response = '%s: %.1f chaos' % (name, line['chaosValue'])
			if line['divineValue'] > 1.0:
				response += ', %.1f divine' % line['divineValue']
		responses.append(response)
	return responses

def _search(league, q) -> tuple[set[str], list[dict]]:
	q = q.casefold().replace('’', "'") # replace U+2019 with apostrophe # noqa: RUF001
	matches = []
	q, names, page = _page(league, q)
	if not page:
		return names, matches

	data = _query(page, league)
	exact = False
	for line in data['lines']:
		name = line.get('name')
		if name is None:
			name = line['currencyTypeName']
			(detail,) = (d for d in data['currencyDetails'] if d['name'] == name)
			line['icon'] = detail['icon']
		if q in name.casefold():
			names.add(name)
			matches.append(line)
			if q == name.casefold():
				exact = True
				# there may be other exact matches (5L/6L), so we cannot break

	if exact:
		# there may be multiple lines that are exact matches (5L/6L)
		matches = [match for match in matches
				if match.get('name', match.get('currencyTypeName')).casefold() == q]
		names = {matches[0].get('name', matches[0].get('currencyTypeName'))}
	return names, matches

pages = {}

def _page(league, q):
	if len(pages) == 0:
		r = rs.get('https://poe.ninja/api/data/economysearch', params={'league': league, 'language': 'fr'})
		r.raise_for_status()
		pages.update(r.json())

	names = set()
	for page, items in pages['items'].items():
		for item in items:
			if q in item['name'].casefold():
				# there may be other matches on other pages, but we won't bother finding them
				return q, names, page

	# couldn't find it in english; try french
	fr_q = []
	for en, fr in pages['language']['translations'].items():
		fr = fr.casefold()
		if q == fr:
			fr_q = [(en.casefold(), fr)]
			break
		elif q in fr:
			fr_q.append((en.casefold(), fr))
	if len(fr_q) == 1:
		q = fr_q[0][0]
		for page, items in pages['items'].items():
			for item in items:
				if q in item['name'].casefold():
					return q, names, page
	elif len(fr_q) > 1:
		names = {fr for en, fr in fr_q}
		return None, names, None
	else:
		return None, names, None

cache = {}

def _query(page, league):
	cached = cache.get((page, league))
	now = time.time()
	if cached is not None:
		ts, data = cached
		if ts > now - 60 * 60: # cache for 1 hour
			return data

	params = {'league': league, 'type': page}
	if page == 'Currency':
		r = rs.get('https://poe.ninja/api/data/currencyoverview', params=params)
	else:
		r = rs.get('https://poe.ninja/api/data/itemoverview', params=params)
	r.raise_for_status()
	data = r.json()
	cache[(page, league)] = now, data
	return data

def poedb(cmd):
	if not cmd.args:
		return

	query = cmd.args.casefold()
	results: list[dict[str, str]] = []
	for item in _poedb_autocomplete():
		label = item['label'].casefold()
		if query == label:
			result = item
			break
		elif query in label:
			results.append(item)
	else:
		if len(results) == 0:
			cmd.reply('no results found for %r' % cmd.args)
			return
		elif len(results) > 1:
			cmd.reply(', '.join(i['label'] for i in results))
			return
		[result] = results

	url = 'https://poedb.tw/us/' + result['value']
	r = rs.get(url)
	r.raise_for_status()

	parser = OpenGraphParser()
	parser.feed(r.text)
	try:
		image = {'url': parser.og['image']}
	except KeyError:
		image = None
	embed = {
		'title': parser.og['title'],
		'description': parser.og.get('description'),
		'image': image,
		'url': url,
	}
	cmd.reply('', embed=embed)

poedb_autocomplete = None

def _poedb_autocomplete():
	global poedb_autocomplete

	if poedb_autocomplete is None:
		r = rs.get('https://poedb.tw/json/autocomplete_us.json')
		r.raise_for_status()
		poedb_autocomplete = r.json()
	return poedb_autocomplete

class OpenGraphParser(html.parser.HTMLParser):
	def __init__(self):
		super().__init__()
		self.og = {}

	def handle_starttag(self, tag, attrs):
		if tag != 'meta':
			return
		attr_dict = dict(attrs)
		prop = attr_dict.get('property')
		if prop is not None and prop.startswith('og:'):
			self.og[prop[3:]] = attr_dict['content']
