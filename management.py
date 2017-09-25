import config

def join(cmd):
	guild_id, role_id = _ids(cmd)
	if guild_id != config.bot.role_server:
		return
	roles = cmd.bot.guilds[guild_id].roles
	if role_id is None or cmd.args not in _allowed_role_names(roles):
		cmd.reply('no joinable role named %s' % cmd.args)
	else:
		cmd.bot.post('/guilds/%s/members/%s/roles/%s' % (guild_id, cmd.sender['id'], role_id), None,
				method='PUT')
		cmd.reply('put <@!%s> in %s' % (cmd.sender['id'], cmd.args))

def leave(cmd):
	guild_id, role_id = _ids(cmd)
	if guild_id != config.bot.role_server:
		return
	roles = cmd.bot.guilds[guild_id].roles
	if role_id is None or cmd.args not in _allowed_role_names(roles):
		cmd.reply('no joinable role named %s' % cmd.args)
	else:
		cmd.bot.post('/guilds/%s/members/%s/roles/%s' % (guild_id, cmd.sender['id'], role_id), None,
				method='DELETE')
		cmd.reply('removed <@!%s> from %s' % (cmd.sender['id'], cmd.args))

def list_roles(cmd):
	bot = cmd.bot
	guild_id = bot.channels[cmd.channel_id]
	if guild_id != config.bot.role_server:
		return
	roles = bot.guilds[guild_id].roles
	cmd.reply(', '.join(_allowed_role_names(roles)))

def _ids(cmd):
	bot = cmd.bot
	guild_id = bot.channels[cmd.channel_id]
	roles = bot.guilds[guild_id].roles
	try:
		role_id = roles[cmd.args]['id']
		return guild_id, role_id
	except KeyError:
		return guild_id, None

def _allowed_role_names(roles):
	sbot_position = roles['sbot']['position']
	arns = []
	for role in roles.values():
		# exclude roles higher than ours, @everyone (position 0), humans, and bots
		if 0 < role['position'] < sbot_position and role['name'] not in ('humans', 'bots'):
			arns.append(role['name'])
	return arns
