from __future__ import annotations

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

price_cache: dict = {'last_update': 0, 'prices': None}
def _get_prices() -> dict:
	now = time.time()
	if price_cache['last_update'] < now - 60 * 60 * 24:
		r = requests.get('https://api.punoted.net/v1/corporation/prices')
		r.raise_for_status()
		price_cache['prices'] = {p['ticker']: p['price'] for p in r.json()}
		price_cache['last_update'] = now
	return price_cache['prices']
