#!/usr/bin/env python3
from __future__ import annotations

import dataclasses
import datetime
import typing

import bs4
import dateutil
import requests

import bot
import command
import config

@command.command('track flight', {
	'type': command.OPTION_TYPE.SUB_COMMAND,
	'name': 'list',
	'description': 'list timestamps for a flight number',
	'options': [
		{
			'type': command.OPTION_TYPE.STRING,
			'name': 'flight-number',
			'description': 'e.g. UA123',
			'required': True,
		},
	],
}, {
	'type': command.OPTION_TYPE.SUB_COMMAND,
	'name': 'track',
	'description': 'receive notifications for a flight',
	'options': [
		{
			'type': command.OPTION_TYPE.STRING,
			'name': 'flight-number',
			'description': 'e.g. UA123',
			'required': True,
		},
		{
			'type': command.OPTION_TYPE.INTEGER,
			'name': 'timestamp',
			'description': 'scheduled departure timetamp (use /flight list)',
			'required': True,
		},
		{
			'type': command.OPTION_TYPE.STRING,
			'name': 'timezone',
			'description': 'e.g. America/Los_Angeles',
			'required': True,
		},
	],
})
def track_flight(cmd: bot.InteractionEvent) -> None:
	options = cmd.options
	subcmd = options[0]['name']
	match subcmd:
		case 'list':
			number = options[0]['options'][0]['value'].lower()
			rs = requests.Session()
			rs.headers['User-Agent'] = 'Mozilla/5.0'
			msg = '\n'.join(f"{row['data-timestamp']}: {row.find_all('td')[2].get_text()}"
					for row in _iter_flight_rows(rs, number))
			cmd.reply(msg)
		case 'track':
			number: str = options[0]['options'][0]['value'].lower()
			timestamp = options[0]['options'][1]['value']
			timezone = options[0]['options'][2]['value']
			if dateutil.tz.gettz(timezone) is None:
				cmd.reply(f'unknown timezone {timezone!r}')
				return
			flight_state = FlightState(channel_id=cmd.channel_id,
					number=number, timestamp=timestamp, timezone=timezone, last=None)
			config.state.flights.append(dataclasses.asdict(flight_state))
			config.state.save()
			cmd.reply('tracking flight ' + number.upper())

def check_flights(bot: bot.Bot) -> None:
	rs = requests.Session()
	rs.headers['User-Agent'] = 'Mozilla/5.0'
	new_state = []
	for flight_state_doc in config.state.flights:
		flight_state = FlightState.from_dict(flight_state_doc)
		aircraft_url, new_flights = _check_flight(rs, flight_state)
		if aircraft_url is None:
			bot.send_message(flight_state.channel_id, f'{flight_state.number.upper()} not found')
			# don't append to new_state
		elif flight_state.last != new_flights:
			msg = f'<{aircraft_url}>\n' + '\n\n'.join(f.format_tz(flight_state.timezone) for f in new_flights)
			bot.send_message(flight_state.channel_id, msg)

			if len(new_flights) == 1 and new_flights[0].status_prefix == 'Landed ':
				bot.send_message(flight_state.channel_id, f'{flight_state.number.upper()} has landed; tracking stopped')
			else:
				flight_state.last = new_flights
				new_state.append(dataclasses.asdict(flight_state))
		else:
			new_state.append(flight_state_doc)
	config.state.flights = new_state
	config.state.save()

def _check_flight(rs: requests.Session, flight_state: FlightState) -> tuple[str | None, typing.Sequence[Flight]]:
	for row in _iter_flight_rows(rs, flight_state.number):
		if int(row['data-timestamp']) == flight_state.timestamp:
			break
	else:
		print("couldn't find", flight_state.number, flight_state.timestamp)
		return None, []

	aircraft_url: str = row.find_all('td')[5].find('a')['href']
	aircraft_url = 'https://www.flightradar24.com' + aircraft_url
	response = rs.get(aircraft_url)
	response.raise_for_status()
	soup = bs4.BeautifulSoup(response.content, 'lxml')
	found_flight = False
	flights = []
	for row in soup.find('table', id='tbl-datatable').find('tbody').find_all('tr', class_='data-row'):
		flight = row.find('a', target='_self').get_text()
		cells: list[bs4.element.Tag] = row.find_all('td')
		timestamp = int(cells[7]['data-timestamp'])
		if not found_flight and flight.lower() == flight_state.number and timestamp == flight_state.timestamp:
			found_flight = True
		if found_flight:
			scheduled_departure = datetime.datetime.fromtimestamp(timestamp)
			scheduled_arrival = datetime.datetime.fromtimestamp(int(cells[9]['data-timestamp']))
			actual_departure = None
			if actual_ts := cells[8].get('data-timestamp'):
				actual_departure = datetime.datetime.fromtimestamp(int(actual_ts))
			status_prefix: str = cells[11]['data-prefix']
			status_dt = datetime.datetime.fromtimestamp(int(cells[11]['data-timestamp']))
			flights.append(Flight(
					number=flight, from_airport=cells[3].get_text().lstrip(), to_airport=cells[4].get_text().lstrip(),
					scheduled_departure=scheduled_departure, scheduled_arrival=scheduled_arrival,
					actual_departure=actual_departure, status_prefix=status_prefix, status_dt=status_dt))
			if len(flights) == 3 or status_prefix == 'Landed ':
				break
	return aircraft_url, flights

def _iter_flight_rows(rs: requests.Session, number: str) -> typing.Iterator[bs4.element.Tag]:
	response = rs.get('https://www.flightradar24.com/data/flights/' + number)
	response.raise_for_status()
	soup = bs4.BeautifulSoup(response.content, 'lxml')
	if (table := soup.find('table', id='tbl-datatable')) is None:
		return
	yield from table.find('tbody').find_all('tr', class_='data-row')

@dataclasses.dataclass(eq=False, slots=True)
class FlightState:
	channel_id: str
	number: str
	timestamp: int
	timezone: str
	last: typing.Sequence[Flight] | None

	@classmethod
	def from_dict(cls, d: typing.Mapping) -> FlightState:
		if d['last'] is not None:
			d = {**d, 'last': [Flight(**f) for f in d['last']]}
		return cls(**d)

@dataclasses.dataclass(eq=False, frozen=True, slots=True)
class Flight:
	number: str
	from_airport: str
	to_airport: str
	scheduled_departure: datetime.datetime
	scheduled_arrival: datetime.datetime
	actual_departure: datetime.datetime | None
	status_prefix: str
	status_dt: datetime.datetime

	def __eq__(self, o: object) -> bool:
		if not isinstance(o, Flight):
			return False
		for field in dataclasses.fields(Flight):
			if field.name != 'status_dt' and getattr(self, field.name) != getattr(o, field.name):
				return False
		return True

	def format_tz(self, tz_name: str) -> str:
		tz = dateutil.tz.gettz(tz_name)
		assert tz is not None
		scheduled_departure = self.scheduled_departure.astimezone(tz)
		scheduled_arrival = self.scheduled_arrival.astimezone(tz)
		actual_departure_s = '-'
		if self.actual_departure is not None:
			actual_departure_s = self.actual_departure.astimezone(tz).strftime('%H:%M')
		status_dt = self.status_dt.astimezone(tz)
		return f'{self.from_airport} → {self.to_airport}\t{scheduled_departure.strftime("%Y-%m-%d")}\n' + \
			f'schedule: {scheduled_departure.strftime("%H:%M")} → {scheduled_arrival.strftime("%H:%M")}\n' + \
			f'actual departure: {actual_departure_s}\n' + \
			f'{self.status_prefix}{status_dt.strftime("%H:%M")}'

if __name__ == '__main__':
	check_flights(bot.Bot({}))
