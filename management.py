def join(cmd):
	if cmd.args == '@everyone':
		return
	guild_id, role_id = _ids(cmd)
	if role_id is None:
		cmd.reply('no role named %s' % cmd.args)
	else:
		cmd.bot.post('/guilds/%s/members/%s/roles/%s' % (guild_id, cmd.sender['id'], role_id), None,
				method='PUT')
		cmd.reply('put <@!%s> in %s' % (cmd.sender['id'], cmd.args))

def leave(cmd):
	if cmd.args == '@everyone':
		return
	guild_id, role_id = _ids(cmd)
	if role_id is None:
		cmd.reply('no role named %s' % cmd.args)
	else:
		cmd.bot.post('/guilds/%s/members/%s/roles/%s' % (guild_id, cmd.sender['id'], role_id), None,
				method='DELETE')
		cmd.reply('removed <@!%s> from %s' % (cmd.sender['id'], cmd.args))

def _ids(cmd):
	bot = cmd.bot
	guild_id = bot.channels[cmd.channel_id]
	roles = bot.guilds[guild_id].roles
	try:
		role_id = roles[cmd.args]
		return guild_id, role_id
	except KeyError:
		return guild_id, None
