#!/usr/bin/env python3

import requests

consumer_key = input('consumer key: ')
consumer_secret = input('consumer secret: ')

rs = requests.Session()
r = rs.post('https://api.twitter.com/oauth2/token',
	auth=(consumer_key, consumer_secret),
	data={'grant_type': 'client_credentials'})
print(r.content)
