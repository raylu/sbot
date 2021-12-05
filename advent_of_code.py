import collections
import datetime
import time
from typing import Any

import requests

import config

def check_leaderboards(bot):
	last_check = getattr(config.state, 'advent_of_code_last_check', int(time.time()))
	today = datetime.date.today()
	year = today.year
	if today.month != 12:
		year -= 1
	rs = requests.Session()

	for leaderboard in config.bot.advent_of_code:
		url = 'https://adventofcode.com/%d/leaderboard/private/view/%d.json' % (
				year, leaderboard['leaderboard'])
		r = rs.get(url, headers={'Cookie': 'session=' + leaderboard['session']})
		r.raise_for_status()

		new_completions = collections.defaultdict(list)
		for member in r.json()['members'].values():
			if member['name'] is None: # anonymous user
				continue
			last_star_ts = member['last_star_ts']
			if last_star_ts == '0' or last_star_ts < last_check: # yes, it's a string sometimes
				continue

			for day, parts in sorted_dict(member['completion_day_level']):
				for part, part_info in sorted_dict(parts):
					if part_info['get_star_ts'] > last_check:
						new_completions[member['name']].append('day %s.%s' % (day, part))

		if new_completions:
			output = '\n'.join('%s got %s' % (name, ', '.join(completions))
					for name, completions in new_completions.items())
			bot.send_message(leaderboard['channel'], 'advent of code', {'description': output})

	config.state.advent_of_code_last_check = int(time.time())
	config.state.save()

def sorted_dict(d: dict[str, Any]):
	# the API returns a dict with string days/parts
	# {'10': {'2': {...}}}  represents day 10, part 2
	return sorted(d.items(), key=lambda pair: int(pair[0]))

def main():
	# pylint: disable=import-outside-toplevel
	import bot

	check_leaderboards(bot.Bot({}))

if __name__ == '__main__':
	main()
