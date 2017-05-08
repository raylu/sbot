import urllib.parse
import subprocess

import dateutil.parser
import dateutil.tz
import requests

rs = requests.Session()
rs.headers['User-Agent'] = 'sbot (github.com/raylu/sbot)'

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
	if not cmd.args:
		return
	try:
		dt = dateutil.parser.parse(cmd.args)
	except (ValueError, AttributeError) as e:
		cmd.reply(str(e))
		return
	if not dt.tzinfo:
		dt = dt.replace(tzinfo=utc)
	response = '{:%a %-d %-I:%M %p %Z}\n{:%a %-d %-I:%M %p %Z}\n{:%a %-d %H:%M %Z}\n'
	response += '{:%a %-d %H:%M %Z}\n{:%a %-d %-I:%M %p %Z}'
	response = response.format(dt.astimezone(pacific), dt.astimezone(eastern), dt.astimezone(utc),
			dt.astimezone(korean), dt.astimezone(australian))
	cmd.reply(response)
