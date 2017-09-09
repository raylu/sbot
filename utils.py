import datetime
import subprocess
import urllib.parse

import dateutil.parser
import dateutil.tz
import requests

import config

rs = requests.Session()
rs.headers['User-Agent'] = 'sbot (github.com/raylu/sbot)'

def help(cmd):
	commands = set(cmd.bot.commands.keys())
	guild_id = cmd.bot.channels[cmd.channel_id]
	if cmd.channel_id != config.bot.timer_channel:
		commands.remove('timer')
	if guild_id != config.bot.role_server:
		for name, func in cmd.bot.commands.items():
			if func.__module__ == 'management':
				commands.remove(name)
	reply = 'commands: `!%s`' % '`, `!'.join(commands)
	cmd.reply(reply)

def calc(cmd):
	response = rs.get('https://www.calcatraz.com/calculator/api', params={'c': cmd.args})
	cmd.reply(response.text.rstrip())

def units(cmd):
	command = ['units', '--compact', '--one-line', '--quiet'] + cmd.args.split(' in ', 1)
	proc = subprocess.Popen(command, universal_newlines=True, stdout=subprocess.PIPE)
	output, _ = proc.communicate()
	cmd.reply(output)

def roll(cmd):
	args = cmd.args or '1d6'
	response = rs.get('https://rolz.org/api/?' + urllib.parse.quote_plus(args))
	split = response.text.split('\n')
	details = split[2].split('=', 1)[1].strip()
	details = details.replace(' +', ' + ').replace(' +  ', ' + ')
	result = split[1].split('=', 1)[1]
	cmd.reply('%s %s' % (result, details))

pacific = dateutil.tz.gettz('America/Los_Angeles')
eastern = dateutil.tz.gettz('America/New_York')
utc = dateutil.tz.tzutc()
korean = dateutil.tz.gettz('Asia/Seoul')
australian = dateutil.tz.gettz('Australia/Sydney')
def timezones(cmd):
	if cmd.args:
		try:
			dt = dateutil.parser.parse(cmd.args)
		except (ValueError, AttributeError) as e:
			cmd.reply(str(e))
			return
	else:
		dt = datetime.datetime.utcnow()
	if not dt.tzinfo:
		dt = dt.replace(tzinfo=utc)
	response = '{:%a %-d %-I:%M %p %Z}\n{:%a %-d %-I:%M %p %Z}\n{:%a %-d %H:%M %Z}\n'
	response += '{:%a %-d %H:%M %Z}\n{:%a %-d %-I:%M %p %Z}'
	response = response.format(dt.astimezone(pacific), dt.astimezone(eastern), dt.astimezone(utc),
			dt.astimezone(korean), dt.astimezone(australian))
	cmd.reply(response)

timer_usage = 'usage: `!timer list`, `!timer add thing in 1d2h3m`, `!timer del thing`'
dt_format = '%Y-%m-%d %H:%M:%S'
def timer(cmd):
	if not cmd.args:
		cmd.reply(timer_usage)
		return
	split = cmd.args.split(' ', 1)
	subcmd = split[0]
	if subcmd == 'list':
		_timer_list(cmd, split)
	elif subcmd == 'add':
		_timer_add(cmd, split)
	elif subcmd == 'del':
		_timer_del(cmd, split)
	else:
		cmd.reply(timer_usage)

def _timer_list(cmd, split):
	now = datetime.datetime.utcnow()
	reply = []
	for name, time in config.state.timers.items():
		rel = readable_rel(time - now)
		reply.append('%s: %s (%s)' % (name, time.strftime(dt_format), rel))
	cmd.reply('\n'.join(reply))

def _timer_add(cmd, split):
	try:
		name, arg = split[1].rsplit(' in ', 1)
	except IndexError:
		cmd.reply('%s: missing args to `add`; %s' % (cmd.sender['username'], timer_usage))
		return
	except ValueError:
		cmd.reply('%s: must specify timer name and time delta' % cmd.sender['username'])
		return
	if name in config.state.timers:
		time_str = config.state.timers[name].strftime(dt_format)
		cmd.reply('%s: "%s" already set for %s' % (cmd.sender['username'], name, time_str))
		return
	td_args = {'days': 0, 'hours': 0, 'minutes': 0}
	for char, unit in zip('dhm', ['days', 'hours', 'minutes']):
		try:
			n_units, arg = arg.split(char, 1)
		except ValueError:
			continue
		try:
			td_args[unit] = int(n_units)
		except ValueError:
			cmd.reply('%s: "%s" not an int for unit %s' % (cmd.sender['username'], n_units, unit))
			return
	if arg:
		cmd.reply('%s: "%s" left over after parsing time' % (cmd.sender['username'], arg))
		return
	td = datetime.timedelta(**td_args)
	time = datetime.datetime.utcnow() + td
	config.state.timers[name] = time
	config.state.save()
	with cmd.bot.timer_condvar:
		cmd.bot.timer_condvar.notify()
	cmd.reply('"%s" set for %s (%s)' % (name, time.strftime(dt_format), readable_rel(td)))

def _timer_del(cmd, split):
	try:
		name = split[1]
	except IndexError:
		cmd.reply('%s: missing args to `del`; %s' % (cmd.sender['username'], timer_usage))
		return
	try:
		del config.state.timers[name]
		config.state.save()
		cmd.reply('deleted "%s"' % name)
	except KeyError:
		cmd.reply('%s: couldn\'t find "%s"' % (cmd.sender['username'], name))

def readable_rel(rel):
	seconds = rel.total_seconds()
	minutes, seconds = divmod(seconds, 60)
	hours, minutes = divmod(minutes, 60)
	days, hours = divmod(hours, 24)

	s = []
	for n, unit in zip([days, hours, minutes], ['day', 'hour', 'minute']):
		if n == 0:
			continue
		if n > 1:
			unit += 's'
		s.append('%d %s' % (n, unit))
	if not s:
		return '%d seconds' % seconds
	return ' '.join(s)
