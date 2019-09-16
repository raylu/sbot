#!/usr/bin/env python3

from pprint import pprint

import utils

class MockCmd:
	def __init__(self):
		self.args = '94103'
		self.sender = {'username': 'testname'}

	def reply(self, text, embed=None, files=None):
		print(text)
		pprint(embed)

utils.weather(MockCmd())
