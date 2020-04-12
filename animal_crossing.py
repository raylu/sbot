from datetime import datetime, time, timezone
import sqlite3
import dateutil
import dateutil.tz

import config

if config.bot.acnh_db is not None:
	db = sqlite3.connect(config.bot.acnh_db)
	db.row_factory = sqlite3.Row

	# enable foreign key constraints
	with db:
		db.execute('PRAGMA foreign_keys = ON')

cached_row_id = 0

def stalk_market(cmd):
	if not cmd.args:
		# TODO: usage string? some other default behavior?
		return

	split = cmd.args.split(' ', 1)
	subcmd = split[0]
	subargs = len(split) == 2 and split[1] or ''
	if subcmd == 'tz':
		_stalk_set_timezone(cmd, subargs)
	elif subcmd == 'sell':
		_stalk_set_sell_price(cmd, subargs)
	elif subcmd == 'trigger':
		_stalks_set_sell_trigger(cmd, subargs)
	else:
		cmd.reply('Unrecognized stalks subcommand %s' % subcmd)

def _stalk_set_sell_price(cmd, price):
	if not price:
		_stalk_list_sale_prices(cmd)
		return
	user_id = cmd.sender['id']
	current_time = datetime.now(timezone.utc)
	try:
		value = int(price)
	except ValueError:
		cmd.reply('usage: !stalks sell 123')

	try:
		with db:
			db.execute('''
			INSERT INTO sale_price VALUES (?, ?, ?)
			''', (user_id, current_time, value))
		cmd.reply('Sale price recorded!')
		_stallk_check_sell_triggers(cmd, price)
	except sqlite3.IntegrityError:
		cmd.reply('Could not add sale price. Have you registered a friend code?')

def _stallk_check_sell_triggers(cmd, price):
	cur = db.execute('''
	SELECT user_id FROM sell_trigger WHERE sell_trigger.price <= ?
	''', (price,))

	triggers = [x['user_id'] for x in cur.fetchall() if x['user_id'] != cmd.sender['id']]
	if triggers:
		msg = ' '.join(['<@!%s>' % (x) for x in triggers])
		msg += (': %s has reported a sell price of %s, above your configured trigger.' %
			(cmd.sender['username'], price))
		cmd.reply(msg)

def _stalk_list_sale_prices(cmd):
	global cached_row_id
	cur = db.execute('''
	SELECT sale_price.rowid, *
	FROM sale_price
	INNER JOIN user ON sale_price.user_id = user.id
	WHERE sale_price.rowid > ?
	ORDER BY sale_price.rowid ASC
	''', (cached_row_id,))

	prices = cur.fetchall()
	current_time = datetime.now(timezone.utc)
	results = {}
	for price in prices:
		user_id = price['user_id']

		if dateutil.parser.parse(price['created_at']).date() != current_time.date():
			cached_row_id = price['rowid']
			continue

		tz_name = price['timezone']
		user_tz = dateutil.tz.gettz(tz_name)
		local_time = current_time.astimezone(user_tz)
		if (tz_name is None or time(8, 0) < local_time.time() < time(22, 0)):
			if user_id in results:
				if price['price'] > results[user_id]['price']:
					results[user_id] = price
			else:
				results[user_id] = price

	if not results:
		cmd.reply("No turnip prices have been reported for today.")
		return

	output = []
	tz_disclaimer = False
	for result in results.values():
		price_str = ('%s: %s (%s)' %
			(result['username'], str(result['price']), result['code']))
		if price['timezone'] is None:
			tz_disclaimer = True
			price_str += '*'
		output.append(price_str)
	if tz_disclaimer:
		output.append('\n*: user has no timezone record. Store may be closed.')
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
		Specify a timezone from the tz database.
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
		current_time = datetime.now().astimezone(tz)
		cmd.reply('Timezone successfully updated. Your current time should be %s.'
			% (current_time))
	else:
		cmd.reply('Timezone could not be updated. Have you registered a friend code?')
