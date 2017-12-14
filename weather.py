import requests

import config

rs = requests.Session()
rs.headers['User-Agent'] = 'sbot (github.com/raylu/sbot)'

def weather(cmd):
	if not cmd.args:
		return
	if not config.bot.weather_key:
		return
	response = rs.get('https://api.wunderground.com/api/%s/conditions/q/%s.json' %
			  (config.bot.weather_key, cmd.args))
	report = response.json()
	if response.status_code == 200 and 'current_observation' in report:
		report = report['current_observation']
		cmd.reply('%s: %s, feels like %s. %s. (%s)'
			  % (report['display_location']['city'],
			     report['temperature_string'],
			     report['feelslike_string'],
			     report['weather'],
			     report['forecast_url']))
	elif response.status_code == 200 and 'results' in report['response']:
		cmd.reply('Got %s results. Try narrowing your search'
			  % len(report['response']['results']))
	else:
		cmd.reply('Error fetching results')
