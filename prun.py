from __future__ import annotations

import collections
import dataclasses
import datetime
import time
import typing

import requests

import config

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

def planetary_upkeep(bot: bot.Bot) -> None:
	assert config.bot.prun_upkeep is not None
	configs = {planet: UpkeepConfig(**cfg) for planet, cfg in config.bot.prun_upkeep.items()}

	planet_infra: dict[str, list[Infrastructure]] = collections.defaultdict(list)
	for infra in get_infra(configs.keys()):
		planet_infra[infra['PlanetName']].append(infra)

	now = datetime.datetime.now(tz=datetime.UTC)
	for planet_name, infras in planet_infra.items():
		planet_config = configs[planet_name]

		planet_last = None
		if planet_last_ts := config.cron_state.prun_popi_next.get(planet_name):
			planet_last = datetime.datetime.fromtimestamp(planet_last_ts, tz=datetime.UTC)
		planet_next = datetime.datetime.max.replace(tzinfo=datetime.UTC)
		planet_notifs = []
		for infra in infras:
			if (target := planet_config.popi.get(infra['Type'])) is None:
				continue
			fill_by = datetime.datetime.max.replace(tzinfo=datetime.UTC)
			if fill_by < planet_next:
				planet_next = fill_by
			if planet_last is not None and fill_by <= planet_last: # we've previously notified about this consumption
				continue

			filled = 0
			for upkeep in infra['Upkeeps']:
				next_consumption_amount = upkeep['StoreCapacity'] / 30 * upkeep['Duration'] # capacity is always 30 days
				filled += upkeep['Stored'] >= next_consumption_amount
				if (next_consumption := datetime.datetime.fromisoformat(upkeep['NextTick'])) < fill_by:
					fill_by = next_consumption
			if filled < target and fill_by - now < datetime.timedelta(hours=36):
				due_ts = int(fill_by.timestamp())
				planet_notifs.append(f"{infra['PlanetName']} {infra['Type']} {filled}/{target} filled; "
						f"due <t:{due_ts}:f> (<t:{due_ts}:R>)")
		if len(planet_notifs) > 0:
			bot.send_message(planet_config.channel, '\n'.join(planet_notifs))
			config.cron_state.prun_popi_next[planet_name] = planet_next.timestamp()
			config.cron_state.save()

def get_infra(planet_names: typing.Collection[str]) -> typing.Sequence[Infrastructure]:
	r = requests.get('https://api.fnar.net/infrastructure',
			params={'infrastructure': planet_names, 'include_upkeeps': 'true'})
	r.raise_for_status()
	return r.json()

@dataclasses.dataclass(frozen=True, eq=False, slots=True)
class UpkeepConfig:
	channel: str
	popi: dict[str, int]

class Infrastructure(typing.TypedDict):
	PlanetName: str
	Type: str
	Upkeeps: typing.Sequence[Upkeep]

class Upkeep(typing.TypedDict):
	Ticker: str
	Stored: int
	StoreCapacity: int
	Duration: int
	NextTick: str

if __name__ == '__main__':
	import sys

	import bot
	planet_names = sys.argv[1:]
	if not planet_names:
		planetary_upkeep(bot.Bot({}))
	else:
		for infra in get_infra(planet_names):
			for upkeep in infra['Upkeeps']:
				print(infra['PlanetName'], infra['Type'], upkeep['Ticker'],
						f"{upkeep['Stored']}/{upkeep['StoreCapacity']}", upkeep['NextTick'])
