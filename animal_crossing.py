from datetime import datetime, timezone
import re
import sqlite3
import dateutil
import dateutil.tz

import config

if config.bot.acnh_db is not None:
	db = sqlite3.connect(config.bot.acnh_db)
	db.row_factory = sqlite3.Row

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
	db.execute('''
	INSERT INTO sale_prices VALUES (?, ?, ?)
	''', (user_id, current_time, value))
	try:
		db.commit()
		cmd.reply("Sale price recorded!")
	except sqlite3.OperationalError:
		return

def _stalk_list_sale_prices(cmd):
	# TODO: is there a better way to do this without a gross global?
	global cached_row_id
	cur = db.execute('''
	SELECT sale_prices.rowid, *
	FROM sale_prices
	INNER JOIN user ON sale_prices.user_id = user.id
	WHERE sale_prices.rowid > ?
	''', (cached_row_id,))

	prices = cur.fetchall()
	current_time = datetime.now(timezone.utc)
	results = {}
	for price in prices:
		print("%s %s" % (price['rowid'], price['created_at']))
		user_id = price['user_id']

		# TODO: check noon bump / if store is still open in local TZ
		if dateutil.parser.parse(price['created_at']).date() != current_time.date():
			cached_row_id = price['rowid']
			continue
		if user_id in results:
			if price['price'] > results[user_id]['price']:
				results[user_id] = price
		else:
			results[user_id] = price

	if not results:
		cmd.reply("No turnip prices have been reported for today.")
		return

	output = []
	for result in results.values():
		output.append('%s: %s (%s)' %
			(result['username'], str(result['price']), result['code']))
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

	try:
		db.execute('''
		UPDATE user SET timezone=? WHERE id=?
		''', (split[1], cmd.sender['id']))
		db.commit()
		current_time = datetime.now().astimezone(tz)
		cmd.reply('''Timezone successfully updated.
Your current time should be %s''' % (current_time))
	except sqlite3.OperationalError:
		cmd.reply('Could not update timezone. Have you registered your friend code?')

def friend_code(cmd):
	if not cmd.args:
		_user_list_all(cmd)
		return

	split = cmd.args.split(' ', 1)
	subcmd = split[0]
	if subcmd == 'set':
		_user_upsert_friend_code(cmd, split[1])
	elif subcmd == 'remove':
		_user_remove(cmd)
	else:
		_user_find(cmd, split[0])

def _user_upsert_friend_code(cmd, code):
	if friend_code_regex.match(code) is None:
		cmd.reply('Invalid friend code submitted.')
		return

	sender = cmd.sender
	db.execute('''
	INSERT INTO user VALUES(?, ?, ?, null)
	ON CONFLICT(id)
	DO UPDATE SET code=excluded.code
	''', (sender['id'], sender['username'], code))
	db.commit()
	cmd.reply('Friend code for %s has been set.' % (sender['username']))

def _user_list_all(cmd):
	cur = db.execute('SELECT username, code FROM user')
	try:
		users = cur.fetchall()
		reply = []
		for user in users:
			reply.append('%s: %s' % (user['username'], user['code']))
		cmd.reply('\n'.join(reply))
	except sqlite3.OperationalError:
		cmd.reply('There are no friend codes saved :(')

def _user_find(cmd, user):
	cur = db.execute('''
	SELECT username, code FROM user WHERE username LIKE ?
	''', (user,))
	try:
		user = cur.fetchone()
		cmd.reply('%s: %s' % (user[0], user[1]))
	except sqlite3.OperationalError:
		cmd.reply('Friend code for %s could not be found.' % (user))

def _user_remove(cmd):
	db.execute('''
	DELETE FROM user WHERE id=?
	''', (cmd.sender['id'],))

	try:
		db.commit()
		cmd.reply('Successfully removed friend code for %s.' % (cmd.sender['username']))
	except sqlite3.OperationalError:
		cmd.reply('Could not remove friend code for %s. Are you sure it exists?' %
			(cmd.sender['username']))
