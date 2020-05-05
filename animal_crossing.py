import collections
import datetime
import sqlite3

import dateutil
import dateutil.parser
import dateutil.tz

import config
from timer import readable_rel

if config.bot.acnh_db is not None:
	db = sqlite3.connect(config.bot.acnh_db)
	db.row_factory = sqlite3.Row

	# enable foreign key constraints
	with db:
		db.execute('PRAGMA foreign_keys = ON')

time_format = '%Y-%m-%d %H:%M'

def stalk_market(cmd):
	if not cmd.args:
		cmd.reply('''Please register your friend code with '!fc set <friend-code>' before using the following commands:
- !stalks tz <tz>: will set your local timezone. See https://en.wikipedia.org/wiki/List_of_tz_database_time_zones. **This is required for the following commands.**
- !stalks buy: will list all currently available buy offers.
- !stalks buy <value>: will add a new offer listed at <value> bells.
- !stalks sell: will list all currently available sell offers.
- !stalks sell <value>: will add a new offer listed at <value> bells.
- !stalks trigger <value>: will ping you if a new offer is listed above <value> bells. 
		''')
		return

	split = cmd.args.split(' ', 1)
	subcmd = split[0]
	subargs = len(split) == 2 and split[1] or ''
	if subcmd == 'tz':
		_stalk_set_timezone(cmd, subargs)
	elif subcmd == 'sell':
		_stalk_set_sell_price(cmd, subargs)
	elif subcmd == 'buy':
		_stalk_set_buy_price(cmd, subargs)
	elif subcmd == 'trigger':
		_stalks_set_sell_trigger(cmd, subargs)
	else:
		cmd.reply('Unrecognized stalks subcommand %s' % subcmd)

def _stalk_set_buy_price(cmd, price):
	if not price:
		_stalk_list_buy_prices(cmd)
		return

	user_id = cmd.sender['id']
	current_time = datetime.datetime.now(datetime.timezone.utc)
	cur = db.execute('SELECT timezone FROM user WHERE id = ?', (user_id,))
	res = cur.fetchone()
	if not res:
		cmd.reply('Could not add buy price. Have you registered a friend code?')
		return
	elif res['timezone'] is None:
		cmd.reply('Could not add buy price. Please register a time zone with !stalks tz')
		return

	user_time = current_time.astimezone(dateutil.tz.gettz(res['timezone']))
	if user_time.weekday() != 6:
		cmd.reply('It is not currently Sunday in your selected time zone, %s. Turnip offers cannot be submitted.' %
			res['timezone'])
		return
	elif user_time.hour >= 12:
		cmd.reply('Turnips are not available on your island. Your current time zone is %s, where it is currently %s.' %
			(res['timezone'], user_time.strftime(time_format)))
		return
	try:
		value = int(price)
	except ValueError:
		cmd.reply('Could not parse buy value. Usage: !stalks buy 123')
		return

	# discard the calculated index and hardcode 0 for sunday/buy price
	week_local, _, expiration = _user_time_info(user_time)
	with db:
		db.execute('''
		INSERT INTO price (user_id, week_local, week_index, expiration, price) VALUES (?, ?, ?, ?, ?)
		ON CONFLICT(user_id, expiration) DO UPDATE SET price = excluded.price
		''', (user_id, week_local, 0, expiration.astimezone(datetime.timezone.utc), value))

	expires_in = readable_rel(expiration - user_time)
	cmd.reply('Buy price recorded at %d bells. Offer expires in %s.\n<%s>' %
		(value, expires_in, _turnip_prophet([value] + [None] * 12)))

def _stalk_list_buy_prices(cmd):
	current_time = datetime.datetime.now(datetime.timezone.utc)
	sunday = _date_to_sunday(current_time)
	cur = db.execute('''
	SELECT username, expiration, price FROM price 
	JOIN user ON user_id = user.id
	WHERE week_local = ? AND week_index = 0
	''', (str(sunday),))

	prices = cur.fetchall()
	if not prices:
		cmd.reply('No turnip offers were recorded this week.')
		return

	current_time_str = str(current_time)
	current_prices = {}
	week_prices = collections.defaultdict(lambda: [None] * 13)
	for row in prices:
		user = row['username']
		price = row['price']
		if row['expiration'] > current_time_str:
			current_prices[user] = (price, row['expiration'])
		week_prices[user][0] = row['price']

	output = []
	for user, prices in week_prices.items():
		line = '%s:' % user
		if user in current_prices:
			price, expiration = current_prices[user]
			expires_in = readable_rel(dateutil.parser.parse(expiration) - current_time)
			line += ' **%d** (expires in %s)' % (price, expires_in)
		line += ' <%s>' % _turnip_prophet(week_prices[user])
		output.append(line)
	cmd.reply('\n'.join(output))


def _stalk_set_sell_price(cmd, price):
	if not price:
		_stalk_list_sale_prices(cmd)
		return

	user_id = cmd.sender['id']
	current_time = datetime.datetime.now(datetime.timezone.utc)
	cur = db.execute('SELECT timezone FROM user WHERE id = ?', (user_id,))
	res = cur.fetchone()
	if not res:
		cmd.reply('Could not add sale price. Have you registered a friend code?')
		return
	elif res['timezone'] is None:
		cmd.reply('Could not add sale price. Please register a time zone with !stalks tz')
		return

	user_time = current_time.astimezone(dateutil.tz.gettz(res['timezone']))
	if (user_time.hour < 8 or user_time.hour >= 22):
		cmd.reply('Your shops are closed. Your current time zone is %s, where it is currently %s.' %
			(res['timezone'], user_time.strftime(time_format)))
		return
	elif user_time.weekday() == 6:
		cmd.reply('It is currently Sunday in your selected time zone, %s. Turnip offers cannot be submitted.' %
			res['timezone'])
		return
	try:
		value = int(price)
	except ValueError:
		cmd.reply('Could not parse sell value. Usage: !stalks sell 123')
		return

	week_local, week_index, expiration = _user_time_info(user_time)
	with db:
		db.execute('''
		INSERT INTO price (user_id, week_local, week_index, expiration, price) VALUES (?, ?, ?, ?, ?)
		ON CONFLICT(user_id, expiration) DO UPDATE SET price = excluded.price
		''', (user_id, week_local, week_index, expiration.astimezone(datetime.timezone.utc), value))

	sunday = _date_to_sunday(current_time)
	with db:
		cur = db.execute('SELECT week_index, price FROM price WHERE user_id = ? AND week_local = ?',
				(user_id, str(sunday),))
		week_price_rows = cur.fetchall()
	week_prices = [None] * 13
	for row in week_price_rows:
		week_prices[row['week_index']] = row['price']

	expires_in = readable_rel(expiration - user_time)
	cmd.reply('Sale price recorded at %d bells. Offer expires in %s.\n<%s>' %
		(value, expires_in, _turnip_prophet(week_prices)))

	_stalk_check_sell_triggers(cmd, price, expires_in)

def _stalk_check_sell_triggers(cmd, price, expires_in):
	cur = db.execute('''
	SELECT user_id FROM sell_trigger WHERE sell_trigger.price <= ?
	''', (price,))

	triggers = [x['user_id'] for x in cur.fetchall() if x['user_id'] != cmd.sender['id']]
	if triggers:
		msg = ' '.join(['<@!%s>' % (x) for x in triggers])
		msg += (': %s has reported a sell price of %s, above your configured trigger. Their offer will expire in %s.' %
			(cmd.sender['username'], price, expires_in))
		cmd.reply(msg)

def _stalk_list_sale_prices(cmd):
	current_time = datetime.datetime.now(datetime.timezone.utc)
	sunday = _date_to_sunday(current_time)
	cur = db.execute('''
	SELECT username, week_index, expiration, price
	FROM price
	JOIN user ON user_id = user.id
	WHERE week_local == ?
	''', (str(sunday),))

	prices = cur.fetchall()
	if not prices:
		cmd.reply('No turnip offers were recorded this week.')
		return

	current_time_str = str(current_time)
	current_prices = {}
	week_prices = collections.defaultdict(lambda: [None] * 13)
	for row in prices:
		user = row['username']
		price = row['price']
		if row['expiration'] > current_time_str:
			current_prices[user] = (price, row['expiration'])
		week_prices[user][row['week_index']] = price

	output = []
	for user, prices in week_prices.items():
		line = '%s:' % user
		if user in current_prices:
			price, expiration = current_prices[user]
			expires_in = readable_rel(dateutil.parser.parse(expiration) - current_time)
			line += ' **%d** (expires in %s)' % (price, expires_in)
		line += ' <%s>' % _turnip_prophet(week_prices[user])
		output.append(line)
	cmd.reply('\n'.join(output))

def _stalks_set_sell_trigger(cmd, price):
	if not price:
		cmd.reply('usage: !stalks trigger 123\nWill ping you if someone reports a sale price higher than 123.')

	try:
		with db:
			db.execute('''
			INSERT INTO sell_trigger VALUES (?, ?)
			ON CONFLICT(user_id)
			DO UPDATE SET price=excluded.price
			''', (cmd.sender['id'], price))
		cmd.reply('Trigger has been set for %s. You will be pinged if someone reports a price above this.' %
			(price))
	except sqlite3.IntegrityError:
		cmd.reply('Could not insert trigger. Have you registered a friend code?')

def _stalk_set_timezone(cmd, tz_name):
	if not tz_name:
		cmd.reply('''
		Specify a time zone from the tz database.
See https://en.wikipedia.org/wiki/List_of_tz_database_time_zones for a complete list.
		''')
		return

	tz = dateutil.tz.gettz(tz_name)

	if tz is None:
		cmd.reply('Could not find your specified timzone. See https://en.wikipedia.org/wiki/List_of_tz_database_time_zones')
		return

	cur = None
	with db:
		cur = db.execute('''
		UPDATE user SET timezone=? WHERE id=?
		''', (tz_name, cmd.sender['id']))

	if cur.rowcount:
		current_time = datetime.datetime.now().astimezone(tz)
		cmd.reply('Time zone successfully updated. Your current time should be %s.'
			% (current_time.strftime(time_format)))
	else:
		cmd.reply('Time zone could not be updated. Have you registered a friend code?')

def _user_time_info(user_time):
	sunday = _date_to_sunday(user_time)
	week_index = (user_time.weekday() * 2) + 1

	if user_time.hour >= 12:
		expiration = user_time.replace(hour=22, minute=0, second=0, microsecond=0)
		week_index += 1
	else:
		expiration = user_time.replace(hour=12, minute=0, second=0, microsecond=0)

	return sunday, week_index, expiration

def _date_to_sunday(dt):
	weekday = dt.isoweekday()
	if weekday == 7:
		return dt.date()
	return (dt - datetime.timedelta(days=weekday)).date()

def _turnip_prophet(week_prices):
	week_prices_str = '.'.join(i and str(i) or '' for i in week_prices)
	return 'https://turnipprophet.io/?prices=%s' % week_prices_str

def migrate(dry_run):
	with db:
		cur = db.execute('''SELECT user_id, expiration, price, timezone FROM price
		JOIN user ON price.user_id = user.id''')
		rows = cur.fetchall()
		print('migrating', len(rows), 'rows; dry-run:', dry_run)
		if not dry_run:
			db.execute('DROP TABLE sell_price')
			db.execute('''CREATE TABLE sell_price (
				user_id TEXT,
				week_local TEXT,
				week_index INTEGER,
				expiration TEXT,
				price INTEGER,
				FOREIGN KEY(user_id) REFERENCES user(id)
			)''')
			db.execute('''CREATE UNIQUE INDEX idx_sell_price_user_expiration
			ON sell_price (user_id, expiration)''')

		for row in rows:
			expiration_dt = datetime.datetime.fromisoformat(row['expiration'])
			expiration_local = expiration_dt.astimezone(dateutil.tz.gettz(row['timezone']))
			sunday, week_index, _ = _user_time_info(expiration_local - datetime.timedelta(seconds=1))
			if not dry_run:
				db.execute('''INSERT INTO sell_price (user_id, week_local, week_index, expiration, price)
				VALUES(?, ?, ?, ?, ?)''',
						(row['user_id'], str(sunday), week_index, row['expiration'], row['price']))
			print('%s %s\t%s %d' % (row['expiration'], row['timezone'], sunday, week_index))

if __name__ == '__main__':
	import sys

	if sys.argv[1] == 'migrate':
		migrate(False)
	elif sys.argv[1] == 'dry_run':
		migrate(True)
	else:
		sys.exit(1)
