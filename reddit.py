import requests

import config

rs = requests.Session()
rs.headers['User-Agent'] = 'python:sbot:v0 (by /u/raylu)'

def headpat(cmd):
	try:
		items = _reddit_request('/r/headpats/random')
		item = items[0]['data']['children'][0]['data']

		resolutions = item['preview']['images'][0]['resolutions']
		image = resolutions[1]
		image_url = image['url'].replace('&amp;', '&')

		embed = {
			'title': item['title'],
			'url': 'https://www.reddit.com/' + item['permalink'],
			'image': {'url': image_url, 'width': image['width'], 'height': image['height']},
		}
	except Exception:
		cmd.reply('%s: error getting an /r/headpat image' % cmd.sender['username'])
	else:
		cmd.reply('', embed)

def _reddit_request(path):
	url = 'https://oauth.reddit.com' + path
	access_token = config.state.reddit_access_token
	if access_token is not None:
		r = rs.get(url, headers={'Authorization': 'bearer ' + access_token})
	if access_token is None or r.status_code == 401:
		_refresh_access_token()
		r = rs.get(url, headers={'Authorization': 'bearer ' + config.state.reddit_access_token})
	r.raise_for_status()
	return r.json()

def _refresh_access_token():
	r = rs.post('https://www.reddit.com/api/v1/access_token',
			auth=(config.bot.reddit['api_id'], config.bot.reddit['api_secret']),
			data={'grant_type': 'client_credentials'})
	r.raise_for_status()
	access_token = r.json()['access_token']
	config.state.reddit_access_token = access_token
	config.state.save()
