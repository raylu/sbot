#!/usr/bin/env python3

from pprint import pprint

import poe

class MockCmd:
	def __init__(self):
		self.args = 'piscator\'s'
		self.sender = {'username': 'testname'}

	def reply(self, text, embed=None):
		print(text)
		pprint(embed)

poe.wiki(MockCmd())
