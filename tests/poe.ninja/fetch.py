#!/usr/bin/env python3

import sys

import requests

def main():
	league = sys.argv[1]

	rs = requests.Session()
	download(rs, '/api/data/getindexstate', {}, 'index_state.json')
	download(rs, '/api/data/economysearch', {
		'league': league,
		'language': 'fr',
	}, 'economysearch_kalandra_fr.json')
	download(rs, '/api/data/CurrencyOverview', {
		'league': league,
		'type': 'Currency',
		'language': 'fr',
	}, 'currencyoverview_kalandra_currency.json')
	for page in ['DivinationCard', 'SkillGem', 'UniqueWeapon']:
		params = {
			'league': league,
			'type': page,
			'language': 'fr',
		}
		filename = f'itemoverview_{league.lower()}_{page.lower()}.json'
		download(rs, '/api/data/ItemOverview', params, filename)

def download(rs, path, params, filename):
	print(path, '→', filename)
	r = rs.get('https://poe.ninja' + path, params=params)
	r.raise_for_status()
	with open(filename, 'wb') as f:
		f.write(r.content)

if __name__ == '__main__':
	main()
