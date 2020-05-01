#!/usr/bin/env python3

from pprint import pprint

import animal_crossing

class MockCmd:
	def __init__(self):
		self.args = 'sell'
		self.sender = {'username': 'testname', 'id': '1'}
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

animal_crossing.stalk_market(MockCmd())
