import animal_crossing
import canned
import code_eval
import eve
import friend_code
import management
import poe
import reddit
import timer
import twitter
import utils

commands = {
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

	'join': management.join,
	'leave': management.leave,
	'roles': management.list_roles,
	'groups': management.list_roles,
	'cleanup': management.cleanup,
	'massban': management.mass_ban,

	'headpat': reddit.headpat,

	'pc': poe.price,
	'poe': poe.wiki,

	'fc': friend_code.friend_code,
	'stalks': animal_crossing.stalk_market,

	'twitter_queue': twitter.queue_info,

	'can': canned.canned,
}
