import sqlite3

import config

if config.bot.acnh_db is not None:
	db = sqlite3.connect(config.bot.acnh_db)

def friend_code(cmd):
	if not cmd.args:
		_fc_list_all(cmd)
		return

	split = cmd.args.split(' ', 1)
	subcmd = split[0]
	if subcmd == 'add':
		_fc_add_or_update(cmd, split)
	elif subcmd == 'remove':
		_fc_remove(cmd)
	else:
		_fc_find(cmd, split)

def _fc_add_or_update(cmd, split):
	fc = split[1]
	sender = cmd.sender
	cur = db.execute('''
	SELECT id FROM friend_code WHERE id=?
	''', (sender['id'],))

	try:
		cur.fetchone()
		db.execute('''
		UPDATE friend_code SET code=? WHERE id=?
		''', (fc, sender['id']))
		db.commit()
		cmd.reply('Updated friend code!')
	except:
		db.execute('''
		INSERT INTO friend_code VALUES(?, ?, ?)
		''', (sender['id'], sender['username'], fc))
		db.commit()
		cmd.reply('New friend code added!')

def _fc_list_all(cmd):
	cur = db.execute('SELECT username, code FROM friend_code')
	try:
		codes = cur.fetchall()
		reply = []
		for code in codes:
			reply.append('%s: %s' % (code[0], code[1]))
		cmd.reply('\n'.join(reply))
	except:
		cmd.reply('There are no friend codes saved :(')

def _fc_find(cmd, split):
	cur = db.execute('''
	SELECT username, code FROM friend_code WHERE username LIKE ?
	''', (split[0],))
	try:
		code = cur.fetchone()
		cmd.reply('%s: %s' % (code[0], code[1]))
	except:
		cmd.reply('Friend code for %s could not be found.' % (split[0]))

def _fc_remove(cmd):
	db.execute('''
	DELETE FROM friend_code WHERE id=?
	''', (cmd.sender['id'],))

	try:
		db.commit()
		cmd.reply('Successfully removed your friend code.')
	except:
		cmd.reply('Could not remove friend code. Are you sure it exists?')
