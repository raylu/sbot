import datetime

import config

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
	for name, time in config.state.timers.get(cmd.channel_id, {}).items():
		rel = readable_rel(time - now)
		reply.append('%s: %s (%s)' % (name, time.strftime(dt_format), rel))
	if reply:
		cmd.reply('\n'.join(reply))
	else:
		cmd.reply('no timers in this channel')

def _timer_add(cmd, split):
	try:
		name, arg = split[1].rsplit(' in ', 1)
	except IndexError:
		cmd.reply('%s: missing args to `add`; %s' % (cmd.sender['username'], timer_usage))
		return
	except ValueError:
		cmd.reply('%s: must specify timer name and time delta' % cmd.sender['username'])
		return

	timers = config.state.timers.get(cmd.channel_id, {})
	if name in timers:
		time_str = timers[name].strftime(dt_format)
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
	try:
		td = datetime.timedelta(**td_args)
		time = datetime.datetime.utcnow() + td
	except OverflowError:
		cmd.reply('%s: time not in range' % cmd.sender['username'])
		return

	timers[name] = time
	config.state.timers[cmd.channel_id] = timers
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
		del config.state.timers[cmd.channel_id][name]
		config.state.save()
		cmd.reply('deleted "%s"' % name)
	except KeyError:
		cmd.reply('%s: couldn\'t find "%s" in this channel' % (cmd.sender['username'], name))

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
