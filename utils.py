import datetime
import random
import re
import subprocess
import traceback
import urllib.parse

import dateutil.parser
import dateutil.tz
import requests

import config

rs = requests.Session()
rs.headers['User-Agent'] = 'sbot (github.com/raylu/sbot)'

def help(cmd):
	if cmd.args: # only reply on "!help"
		return
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
	if not cmd.args:
		return
	response = rs.get('https://www.calcatraz.com/calculator/api', params={'c': cmd.args})
	if response.status_code == 200:
		cmd.reply(response.text.rstrip()[:1000])
	else:
		cmd.reply('<@!%s>: error calculating' % cmd.sender['id'])

def unicode(cmd):
	if not cmd.args:
		return
	command = ['unicode', '--max', '5', '--color', '0',
			'--format', '{pchar} U+{ordc:04X} {name} (UTF-8: {utf8})\\n', cmd.args]
	proc = subprocess.Popen(command, universal_newlines=True, stdout=subprocess.PIPE)
	output, _ = proc.communicate()
	cmd.reply(output)

temp_re = re.compile(r'\A(-?[0-9 ]*)(C|F)\Z')
def units(cmd):
	split = cmd.args.split(' in ', 1)
	for i, part in enumerate(split):
		match = temp_re.match(part)
		if match:
			# turn "20 C" into "tempC(20)"
			if match.group(1):
				split[i] = 'temp%s(%s)' % (match.group(2), match.group(1))
			else:
				split[i] = 'temp%s' % (match.group(2))
	command = ['units', '--compact', '--one-line', '--quiet'] + split
	proc = subprocess.Popen(command, universal_newlines=True, stdout=subprocess.PIPE)
	output, _ = proc.communicate()
	if proc.wait() == 0:
		cmd.reply(output)
	else:
		cmd.reply('<@!%s>: error running `units`' % cmd.sender['id'])

def roll(cmd):
	args = cmd.args or '1d6'
	response = rs.get('https://rolz.org/api/?' + args) # don't urlencode
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

def weather(cmd):
	if not cmd.args:
		return
	split = cmd.args.split()
	if split[0].startswith('-'):
		flags = split[0][1:]
		location = ' '.join(split[1:])
	elif split[-1].startswith('-'):
		flags = split[-1][1:]
		location = ' '.join(split[:-1])
	else:
		flags = '1Fp'
		location = cmd.args
	filename = '%s_%s.png' % (urllib.parse.quote_plus(location), flags)
	url = 'https://wttr.in/' + filename
	try:
		response = rs.get(url)
		response.raise_for_status()
	except Exception:
		cmd.reply('%s: error getting weather at %s' % (cmd.sender['username'], url),
				{'description': '```%s```' % traceback.format_exc()[-500:]})
		return
	cmd.reply(None, files={filename: response.content})

def ohno(cmd):
	url = 'https://www.raylu.net/f/ohno/ohno%03d.png' % random.randint(1, 294)
	cmd.reply('', {'image': {'url': url}})

def ohyes(cmd):
	url = 'https://www.raylu.net/f/ohyea/ohyea%02d.gif' % random.randint(1, 17)
	cmd.reply('', {'image': {'url': url}})
