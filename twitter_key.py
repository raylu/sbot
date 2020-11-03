#!/usr/bin/env python3

import time
import urllib.parse

import requests

import twitter

consumer_key = input('consumer key: ')
consumer_secret = input('consumer secret: ')

mode = input('1. client credentials (get tweets)\n2. oauth (send tweets)\n')
rs = requests.Session()
if mode == '1':
	r = rs.post('https://api.twitter.com/oauth2/token',
		auth=(consumer_key, consumer_secret),
		data={'grant_type': 'client_credentials'})
	print(r.content)
elif mode == '2':
	# https://developer.twitter.com/en/docs/authentication/oauth-1-0a/pin-based-oauth
	params = {
		'oauth_callback': 'oob',
		'oauth_consumer_key': consumer_key,
		'oauth_nonce': 'hello',
		'oauth_signature_method': 'HMAC-SHA1',
		'oauth_timestamp': str(int(time.time())),
		'oauth_version': '1.0',
	}
	# https://developer.twitter.com/en/docs/authentication/api-reference/request_token
	url = 'https://api.twitter.com/oauth/request_token'
	params['oauth_signature'] = twitter.sign('POST', url, params, consumer_secret, '')
	# https://developer.twitter.com/en/docs/authentication/oauth-1-0a/authorizing-a-request
	auth = 'OAuth '
	auth += ', '.join('%s="%s"' % (k, urllib.parse.quote(v)) for k, v in params.items())
	r = rs.post(url, headers={'Authorization': auth})
	r.raise_for_status()
	oauth_response = urllib.parse.parse_qs(r.text)
	oauth_token = oauth_response['oauth_token'][0]

	# https://developer.twitter.com/en/docs/authentication/api-reference/authorize
	print('https://api.twitter.com/oauth/authorize?oauth_token=' + oauth_token)
	pin = input('pin: ')

	# https://developer.twitter.com/en/docs/authentication/api-reference/access_token
	r = rs.post('https://api.twitter.com/oauth/access_token',
			params={'oauth_token': oauth_token, 'oauth_verifier': pin})
	r.raise_for_status()
	oauth_response = urllib.parse.parse_qs(r.text)
	print(oauth_response)
