from datetime import datetime, time, timezone
import re
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

friend_code_regex = re.compile(r'SW-\d{4}-\d{4}-\d{4}')
cached_row_id = 0

def stalk_market(cmd):
	if not cmd.args:
		# TODO: usage string? some other default behavior?
		return

	split = cmd.args.split(' ', 1)
	subcmd = split[0]
	if subcmd == 'tz':
		_stalk_set_timezone(cmd, split)
	elif subcmd == 'sell':
		_stalk_sales(cmd, split)

def _stalk_sales(cmd, split):
	if len(split) != 2:
		_stalk_list_sale_prices(cmd)
		return
	user_id = cmd.sender['id']
	current_time = datetime.now(timezone.utc)
	value = int(split[1])
	try:
		with db:
			db.execute('''
			INSERT INTO sale_price VALUES (?, ?, ?)
			''', (user_id, current_time, value))
		cmd.reply('Sale price recorded!')
	except sqlite3.IntegrityError:
		cmd.reply('Could not add sale price. Have you registered a friend code?')

def _stalk_list_sale_prices(cmd):
	# TODO: is there a better way to do this without a gross global?
	global cached_row_id
	cur = db.execute('''
	SELECT sale_price.rowid, *
	FROM sale_price
	INNER JOIN user ON sale_price.user_id = user.id
	WHERE sale_price.rowid > ?
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

def _stalk_set_timezone(cmd, split):
	if len(split) != 2:
		cmd.reply('''
		Specify a timezone from the tz database.
See https://en.wikipedia.org/wiki/List_of_tz_database_time_zones for a complete list.
		''')
		return

	tz = dateutil.tz.gettz(split[1])

	if tz is None:
		cmd.reply('Could not find your specified timzone. See https://en.wikipedia.org/wiki/List_of_tz_database_time_zones')
		return

	cur = None
	with db:
		cur = db.execute('''
		UPDATE user SET timezone=? WHERE id=?
		''', (split[1], cmd.sender['id']))

	if cur.rowcount:
		current_time = datetime.now().astimezone(tz)
		cmd.reply('''Timezone successfully updated.
Your current time should be %s.
		''' % (current_time))
	else:
		cmd.reply('Timezone could not be updated. Have you registered a friend code?')

def friend_code(cmd):
	if not cmd.args:
		_user_list_all(cmd)
		return

	split = cmd.args.split(' ', 1)
	subcmd = split[0]
	if subcmd == 'set':
		_user_upsert_friend_code(cmd, split)
	elif subcmd == 'remove':
		_user_remove(cmd)
	else:
		_user_find(cmd, split[0])

def _user_upsert_friend_code(cmd, split):
	if len(split) != 2:
		cmd.reply('usage: !fc set friend-code')
		return

	if friend_code_regex.match(split[1]) is None:
		cmd.reply('Invalid friend code submitted.')
		return

	sender = cmd.sender
	cur = None
	with db:
		cur = db.execute('''
		INSERT INTO user VALUES(?, ?, ?, null)
		ON CONFLICT(id)
		DO UPDATE SET code=excluded.code
		''', (sender['id'], sender['username'], split[1]))

	if cur.rowcount:
		cmd.reply('Friend code for %s has been set.' % (sender['username']))
	else:
		cmd.reply('Could not create user.')

def _user_list_all(cmd):
	cur = db.execute('SELECT username, code FROM user')

	users = cur.fetchall()
	if users:
		reply = []
		for user in users:
			reply.append('%s: %s' % (user['username'], user['code']))
		cmd.reply('\n'.join(reply))
	else:
		cmd.reply('There are no friend codes saved.')

def _user_find(cmd, user):
	cur = db.execute('''
	SELECT username, code FROM user WHERE username LIKE ?
	''', (user,))

	res = cur.fetchone()
	if res:
		cmd.reply('%s: %s' % (res['username'], res['code']))
	else:
		cmd.reply('Friend code for %s could not be found.' % (user))

def _user_remove(cmd):
	cur = None
	with db:
		cur = db.execute('''
		DELETE FROM user WHERE id=?
		''', (cmd.sender['id'],))

	if cur.rowcount:
		cmd.reply('Successfully removed friend code for %s.' % (cmd.sender['username']))
	else:
		cmd.reply('No friend code removed. Have you registered?')
