from __future__ import annotations

import csv
import io
import time
import typing

import requests

if typing.TYPE_CHECKING:
	import bot

def price_mat(cmd: bot.CommandEvent) -> None:
	args = cmd.args.split()
	if len(args) != 2:
		cmd.reply('usage: !corp <amount> <mat>')
		return
	try:
		amount = int(args[0])
	except ValueError:
		cmd.reply('usage: !corp <amount> <mat>')
		return
	mat = args[1].upper()

	try:
		price = _get_prices()[mat]
		cmd.reply(f'{amount} {mat} = {amount * price} ICA ({price}/u)')
	except KeyError:
		cmd.reply(f"error: couldn't find {mat!r} in price schedule")

price_cache = {'last_update': 0, 'prices': None}
def _get_prices() -> dict:
	now = time.time()
	if price_cache['last_update'] < now - 60 * 60 * 24:
		r = requests.get('https://docs.google.com/spreadsheets/d/e/2PACX-1vSG_rqZ_TCSTe12_FzJRw0_mbDCYJ5HnGvnmgI3Sd-CFd0AxkSzc88e3glLeM-5ZpI2ILcFSzEX8Nvg/pub?output=csv')
		r.raise_for_status()
		reader = csv.reader(io.StringIO(r.text))
		prices = {}
		for row in reader:
			if row[1] and row[2]:
				try:
					prices[row[1]] = float(row[2])
				except ValueError:
					pass
		price_cache['prices'] = prices
		price_cache['last_update'] = now
	return price_cache['prices']
