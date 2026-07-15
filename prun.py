from __future__ import annotations

import collections
import dataclasses
import datetime
import functools
import heapq
import time
import typing

import requests

import config

if typing.TYPE_CHECKING:
	import bot

def price_mat(cmd: bot.CommandEvent) -> None:
	prices = _get_prices()
	responses = []
	for pair in cmd.args.split(','):
		try:
			amount, mat = pair.strip().split()
			amount = int(amount)
			mat = mat.upper()
			price = prices[mat]
			responses.append(f'{amount} {mat} = {amount * price} ICA ({price}/u)')
		except ValueError:
			responses.append('usage: !corp <amount> <mat>')
		except KeyError:
			responses.append(f"error: couldn't find {mat!r} in price schedule")
	cmd.reply('\n'.join(responses))

price_cache: dict = {'last_update': 0, 'prices': None}
def _get_prices() -> dict:
	now = time.time()
	if price_cache['last_update'] < now - 60 * 60 * 24:
		r = requests.get('https://api.punoted.net/v1/corporation/prices')
		r.raise_for_status()
		price_cache['prices'] = {p['ticker']: p['price'] for p in r.json()}
		price_cache['last_update'] = now
	return price_cache['prices']

def travel(cmd: bot.CommandEvent) -> None:
	args = cmd.args.split(' ', 1)
	if len(args) != 2:
		cmd.reply('usage: !travel <cx> <planet>')
		return
	cx_name, planet_name = args

	cx_name = cx_name.upper()
	cx = {'ANT': 'AI1', 'BEN': 'CI1', 'ARC': 'CI2', 'HRT': 'IC1', 'MOR': 'NC1', 'HUB': 'NC2'}.get(cx_name, cx_name)

	response = requests.get('https://api.fnar.net/planet/' + planet_name)
	response.raise_for_status()
	planet: FIOPlanet = response.json()
	system_name = planet['NaturalId'][:-1]
	planet_display = planet['Name']
	if planet['Name'] != planet['NaturalId']:
		planet_display += f' ({planet["NaturalId"]})'

	response = requests.get('https://api.fnar.net/map/systems', params={'system': system_name})
	response.raise_for_status()
	(system,) = response.json()

	ftl_travel = ftl_distance(cx, system['SystemId'])
	if ftl_travel.jumps == 0:
		km = int(planet['SemiMajorAxis'] / 1000)
		# ENG at 750 SF usage (50% of an SSL) TRAs at ~300,000,000 km/h
		hours = km / 300_000_000
		cmd.reply(f'{planet_display} is {km:,} km from star\n'
				f'SCB: {hours:.1f} hours')
	else:
		# SCB JMPs at 4pc/hr. RCT CHRGs in 7m30s. 30m DEP, 1.5hr APP+(TO/LAND)
		hours = ftl_travel.parsecs / 4 + (ftl_travel.jumps - 1) * 0.125 + 2
		cmd.reply(f'{system_name} is {ftl_travel.jumps} jumps, {ftl_travel.parsecs:.2f} pc away\n'
				f'SCB: {hours:.1f} hours')

def ftl_distance(cx: str, system: str) -> FTLTravel:
	adjacency = get_system_map()
	cx_systems: dict[str, str] = {
		'AI1': '8ecf9670ba070d78cfb5537e8d9f1b6c',
		'CI1': '92029ff27c1abe932bd2c61ee4c492c7',
		'CI2': 'a4ba8b12739da65efc2b518703652ee1',
		'IC1': 'f2f57766ebaca9d69efae41ccf4d8853',
		'NC1': '49b6615d39ccba05752b3be77b2ebf36',
		'NC2': 'afda9bea7f948f4a066a8882cdfa9055',
	}
	destination = cx_systems[cx]
	if destination == system:
		return FTLTravel(0, 0)

	best: dict[str, float] = {system: 0}
	frontier: list[DijkstraNode] = [DijkstraNode(system, 0, 0)]

	while frontier:
		current = heapq.heappop(frontier)
		if current.system == destination:
			return FTLTravel(current.parsecs, current.jumps)
		if current.parsecs != best.get(current.system):
			continue

		for neighbor in adjacency.get(current.system, []):
			total_distance = current.parsecs + neighbor.parsecs
			if total_distance >= best.get(neighbor.to, float('inf')):
				continue
			best[neighbor.to] = total_distance
			heapq.heappush(frontier, DijkstraNode(neighbor.to, total_distance, current.jumps + 1))

	raise Exception(f'no route from {system} to {cx}')

@functools.cache
def get_system_map() -> dict[str, typing.Any]:
	response = requests.get('https://universemap.taiyibureau.de/graph_data.json')
	response.raise_for_status()
	edges =  response.json()['edges']

	adjacency: dict[str, list[SystemNode]] = collections.defaultdict(list)
	for edge in edges:
		adjacency[edge['start']].append(SystemNode(edge['end'], edge['distance']))
		adjacency[edge['end']].append(SystemNode(edge['start'], edge['distance']))
	return adjacency

@dataclasses.dataclass(eq=False, frozen=True, slots=True)
class FTLTravel:
	parsecs: float
	jumps: int

@dataclasses.dataclass(eq=False, frozen=True, slots=True)
class SystemNode:
	to: str
	parsecs: float

@dataclasses.dataclass(eq=False, frozen=True, slots=True)
class DijkstraNode:
	system: str
	parsecs: float
	jumps: int

	def __lt__(self, other: DijkstraNode) -> bool:
		return (self.parsecs, self.jumps) < (other.parsecs, other.jumps)

class SystemEdge(typing.TypedDict):
	start: str
	end: str
	distance: float

class FIOPlanet(typing.TypedDict):
	NaturalId: str
	Name: str
	SemiMajorAxis: float

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

			filled = 0
			fill_by = datetime.datetime.max.replace(tzinfo=datetime.UTC)
			for upkeep in infra['Upkeeps']:
				next_consumption_amount = upkeep['StoreCapacity'] / 30 * upkeep['Duration'] # capacity is always 30 days
				filled += upkeep['Stored'] >= next_consumption_amount
				if (next_consumption := datetime.datetime.fromisoformat(upkeep['NextTick'])) < fill_by:
					fill_by = next_consumption

			if fill_by < planet_next:
				planet_next = fill_by
			if planet_last is not None and fill_by <= planet_last: # we've previously notified about this consumption
				continue

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
