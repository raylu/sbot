import typing

import animal_crossing
import canned
import code_eval
import cryptolyze
import eve
import flights
import friend_code
import management
import poe
import prun
import sbds
import timer
import utils

commands: typing.Mapping[str, typing.Callable[..., None]] = {
	'help': utils.help,
	'botinfo': utils.botinfo,
	'ping': utils.ping,
	'calc': utils.calc,
	'unicode': utils.unicode,
	'units': utils.units,
	'roll': utils.roll,
	'time': utils.time,
	'weather': utils.weather,
	'ohno': utils.ohno,
	'ohyes': utils.ohyes,
	'ddd': utils.ddd,

	'timer': timer.timer,

	'price': eve.price_check,
	'jumps': eve.jumps,
	'ly': eve.lightyears,
	'evewho': eve.who,

	'js': code_eval.nodejs,
	'ruby': code_eval.ruby,
	'py2': code_eval.python2,
	'py3': code_eval.python3,

	'cryptolyze': cryptolyze.cryptolyze,

	'join': management.join,
	'leave': management.leave,
	'roles': management.list_roles,
	'groups': management.list_roles,
	'cleanup': management.cleanup,
	'massban': management.mass_ban,

	'corp': prun.price_mat,
	'travel': prun.travel,

	'pc': poe.price,
	'poe': poe.poedb,

	'flight': flights.track_flight,

	'sbds': sbds.sbds,

	'fc': friend_code.friend_code,
	'stalks': animal_crossing.stalk_market,

	'can': canned.canned,
}
