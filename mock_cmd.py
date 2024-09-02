#!/usr/bin/env python3

import sys
from pprint import pprint

import requests

import config
import code_eval

class MockCmd:
	def __init__(self):
		if len(sys.argv) == 2:
			self.args = sys.argv[1]
		else:
			self.args = ''
		self.sender = {'username': 'testname', 'pretty_name': 'testname', 'id': '1'}
		self.channel_id = '1'
		self.bot = MockBot()

	def reply(self, text, embed=None, files=None):
		print(text)
		if embed:
			pprint(embed)
		if files:
			pprint(files.keys())

class MockBot:
	def __init__(self):
		self.channels = {'1': '109469702010478592'}
		self.guilds = {'109469702010478592': MockGuild()}

	def send_message(self, channel_id, text, embed=None, files=None):
		print(channel_id, text, embed, files)

	def get(self, path):
		response = requests.get('https://discord.com/api' + path, headers={
			'Authorization': 'Bot ' + config.bot.token,
			'User-Agent': 'DiscordBot (https://github.com/raylu/sbot 0.0)',
		}, timeout=5.0)
		response.raise_for_status()
		return response.json()

	def get_message(self, channel_id, message_id):
		return self.get('/channels/%s/messages/%s' % (channel_id, message_id))

class MockGuild:
	def __init__(self):
		self.roles = {
			'sbot': {'position': 3},
			'dogs': {'position': 1, 'name': 'dogs', 'color': 123456, 'id': '1111'},
			'cats': {'position': 2, 'name': 'cats', 'color': 13369480, 'id': '2222'},
		}

code_eval.nodejs(MockCmd())
