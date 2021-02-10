#!/usr/bin/env python3

from pprint import pprint

import requests

import config
import poe

class MockCmd:
	def __init__(self):
		self.args = 'le stratège'
		self.sender = {'username': 'testname', 'id': '1'}
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
		})
		response.raise_for_status()
		return response.json()

class MockGuild:
	def __init__(self):
		self.roles = {
			'sbot': {'position': 3},
			'dogs': {'position': 1, 'name': 'dogs', 'color': 123456, 'id': '1111'},
			'cats': {'position': 2, 'name': 'cats', 'color': 13369480, 'id': '2222'},
		}

poe.price(MockCmd())
