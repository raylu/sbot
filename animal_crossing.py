import sqlite3

import config

if config.bot.acnh_db is not None:
	db = sqlite3.connect(config.bot.acnh_db)
	db.row_factory = sqlite3.Row

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
	sender = cmd.sender
	db.execute('''
	INSERT INTO user VALUES(?, ?, ?)
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
