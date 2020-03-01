#!/usr/bin/env python3

from pprint import pprint

import management

class MockCmd:
	def __init__(self):
		self.args = ''
		self.sender = {'username': 'testname'}
		self.channel_id = '1'
		self.bot = MockBot()

	def reply(self, text, embed=None, files=None):
		print(text)
		pprint(embed)

class MockBot:
	def __init__(self):
		self.channels = {'1': '109469702010478592'}
		self.guilds = {'109469702010478592': MockGuild()}

class MockGuild:
	def __init__(self):
		self.roles = {
			'sbot': {'position': 3},
			'dogs': {'position': 1, 'name': 'dogs', 'color': 123456},
			'cats': {'position': 2, 'name': 'cats', 'color': 13369480},
		}

management.list_roles(MockCmd())
