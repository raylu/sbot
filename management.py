import operator

import requests

import config
import log

def join(cmd):
	guild_id, role_id = _ids(cmd)
	if config.bot.roles is None or guild_id != config.bot.roles['server']:
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
	if config.bot.roles is None or guild_id != config.bot.roles['server']:
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
	if config.bot.roles is None or guild_id != config.bot.roles['server']:
		return

	roles = list(_allowed_roles(bot.guilds[guild_id].roles))
	roles.sort(key=operator.itemgetter('position'), reverse=True)

	desc = ' '.join('<@&%s>' % role['id'] for role in roles)
	embed = {'description': desc}
	cmd.reply('', embed)

def cleanup(cmd):
	if cmd.sender['id'] != '109405765848088576':
		return
	try:
		start, end = cmd.args.split()
		int(start)
		int(end)
	except ValueError:
		cmd.reply('usage: !cleanup 000 111')
		return
	messages = cmd.bot.iter_messages(cmd.channel_id, str(int(start) - 1), end)
	message_ids = [msg['id'] for msg in messages]
	if len(message_ids) > 0:
		cmd.bot.delete_messages(cmd.channel_id, message_ids)
	else:
		cmd.reply('no messages in range')

def mass_ban(cmd):
	if cmd.channel_id != '473980984874762242': # staff-chat
		return
	try:
		start, end = cmd.args.split()
	except ValueError:
		cmd.reply('usage: `!massban start_msg_id end_msg_id`')
		return
	programming_guild = '181866934353133570'
	join_channel = '209074609893408768'
	try:
		cmd.bot.get_message(join_channel, start)
		cmd.bot.get_message(join_channel, end)
	except requests.exceptions.HTTPError as e:
		if e.response.status_code != 404:
			raise
		cmd.reply('could not find %s or %s in #join' % (start, end))
		return
	cmd.reply('mass banning started')
	for msg in cmd.bot.iter_messages(join_channel, str(int(start) - 1), end):
		if 'welcome to Programming!' not in msg['content']:
			continue
		user_id = msg['mentions'][0]['id']
		user = cmd.bot.get('/users/%s' % user_id)
		log.write('banning %s %s#%s' % (user_id, user['username'], user['discriminator']))
		cmd.bot.ban(programming_guild, user_id)
	cmd.reply('mass banning complete!')

def _ids(cmd):
	bot = cmd.bot
	guild_id = bot.channels[cmd.channel_id]
	roles = bot.guilds[guild_id].roles
	try:
		role_id = roles[cmd.args]['id']
		return guild_id, role_id
	except KeyError:
		return guild_id, None

def _allowed_roles(roles):
	sbot_position = roles['sbot']['position']
	for role in roles.values():
		# exclude roles higher than ours, @everyone (position 0), bots, and Nitro Booster
		if 0 < role['position'] < sbot_position and role['name'] not in ['bots', 'Nitro Booster']:
			yield role

def _allowed_role_names(roles):
	for role in _allowed_roles(roles):
		yield role['name']
