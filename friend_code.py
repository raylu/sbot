import re
import sqlite3

import config

if config.bot.acnh_db is not None:
	db = sqlite3.connect(config.bot.acnh_db)
	db.row_factory = sqlite3.Row

	# enable foreign key constraints
	with db:
		db.execute('PRAGMA foreign_keys = ON')

friend_code_regex = re.compile(r'SW-\d{4}-\d{4}-\d{4}')

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
		_user_find(cmd, cmd.args)

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
		cmd.reply('Successfully removed friend code for %s.' % (cmd.sender['pretty_name']))
	else:
		cmd.reply('No friend code removed. Have you registered?')
