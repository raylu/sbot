import datetime

import command
import config

timer_usage = 'usage: `!timer list`, `!timer add thing in 1d2h3m`, `!timer del thing`'

@command.command('per-channel reminders', {
	'type': command.OPTION_TYPE.SUB_COMMAND,
	'name': 'list',
	'description': 'list timers for this channel',
}, {
	'type': command.OPTION_TYPE.SUB_COMMAND,
	'name': 'add',
	'description': 'add a timer',
	'options': [
		{
			'type': command.OPTION_TYPE.STRING,
			'name': 'thing',
			'description': 'what message to send when the timer expires',
			'required': True,
		},
		{
			'type': command.OPTION_TYPE.STRING,
			'name': 'duration',
			'description': 'when to send the message (format: 1d2h3m)',
			'required': True,
		},
	],
}, {
	'type': command.OPTION_TYPE.SUB_COMMAND,
	'name': 'del',
	'description': 'delete a timer',
	'options': [
		{
			'type': command.OPTION_TYPE.STRING,
			'name': 'thing',
			'description': 'the message that would have been sent',
			'required': True,
		},
	],
})
def timer(cmd):
	options = getattr(cmd, 'options', None)
	if options is not None:
		# this is an InteractionEvent (slash-command)
		subcmd = options[0]['name']
		if subcmd == 'list':
			_timer_list(cmd)
		elif subcmd == 'add':
			name = options[0]['options'][0]['value']
			arg = options[0]['options'][1]['value']
			_timer_add(cmd, name, arg)
		elif subcmd == 'del':
			name = options[0]['options'][0]['value']
			_timer_del(cmd, name)
		else:
			raise AssertionError('unexpeced timer sub-command: %r' % subcmd)
	else:
		if not cmd.args:
			cmd.reply(timer_usage)
			return
		split = cmd.args.split(' ', 1)
		subcmd = split[0]
		if subcmd == 'list':
			_timer_list(cmd)
		elif subcmd == 'add':
			try:
				name, arg = split[1].rsplit(' in ', 1)
			except IndexError:
				cmd.reply('%s: missing args to `add`; %s' % (cmd.sender['username'], timer_usage))
				return
			except ValueError:
				cmd.reply('%s: must specify timer name and time delta' % cmd.sender['username'])
				return
			_timer_add(cmd, name, arg)
		elif subcmd == 'del':
			try:
				name = split[1]
			except IndexError:
				cmd.reply('%s: missing args to `del`; %s' % (cmd.sender['username'], timer_usage))
				return
			_timer_del(cmd, name)
		else:
			cmd.reply(timer_usage)

def _timer_list(cmd):
	reply = []
	for name, dt in config.state.timers.get(cmd.channel_id, {}).items():
		dt = dt.replace(tzinfo=datetime.timezone.utc)
		reply.append('%s: %s' % (name, format_dt(dt)))
	if reply:
		cmd.reply('\n'.join(reply))
	else:
		cmd.reply('no timers in this channel')

def _timer_add(cmd, name, arg):
	timers = config.state.timers.get(cmd.channel_id, {})
	if name in timers:
		time_str = format_dt(timers[name].replace(tzinfo=datetime.timezone.utc))
		cmd.reply('%s: "%s" already set for %s' % (cmd.sender['username'], name, time_str))
		return

	try: # parse as timestamp (981173106)
		dt = datetime.datetime.utcfromtimestamp(int(arg))
	except ValueError:
		# parse as relative time (1d2h3m)
		try:
			dt = parse_rel(arg)
		except RelativeTimeParsingException as e:
			cmd.reply('%s: %s' % (cmd.sender['username'], e.message))
			return
	dt = dt.replace(tzinfo=datetime.timezone.utc)

	timers[name] = dt
	config.state.timers[cmd.channel_id] = timers
	config.state.save()
	with cmd.bot.timer_condvar:
		cmd.bot.timer_condvar.notify()
	cmd.reply('"%s" set for %s' % (name, format_dt(dt)))

def _timer_del(cmd, name):
	try:
		del config.state.timers[cmd.channel_id][name]
		config.state.save()
		cmd.reply('deleted "%s"' % name)
	except KeyError:
		cmd.reply('%s: couldn\'t find "%s" in this channel' % (cmd.sender['username'], name))

def format_dt(dt):
	ts = dt.timestamp()
	return '<t:%d> (<t:%d:R>)' % (ts, ts)

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

def parse_rel(arg):
	td_args = {'days': 0, 'hours': 0, 'minutes': 0}
	for char, unit in zip('dhm', ['days', 'hours', 'minutes']):
		try:
			n_units, arg = arg.split(char, 1)
		except ValueError:
			continue
		try:
			td_args[unit] = int(n_units)
		except ValueError as e:
			raise RelativeTimeParsingException('"%s" not an int for unit %s' % (n_units, unit)) from e
	if arg:
		raise RelativeTimeParsingException('"%s" left over after parsing time' % arg)
	try:
		td = datetime.timedelta(**td_args)
		return datetime.datetime.utcnow() + td
	except OverflowError as e:
		raise RelativeTimeParsingException('time not in range') from e

class RelativeTimeParsingException(Exception):
	def __init__(self, message):
		super().__init__(message)
		self.message = message
