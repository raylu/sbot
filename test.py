#!/usr/bin/env python3

from pprint import pprint

import poe

class MockCmd:
	def __init__(self):
		self.args = 'precursor\'s emblem (po'
		self.sender = {'username': 'testname'}

	def reply(self, text, embed=None):
		print(text)
		pprint(embed)

poe.wiki(MockCmd())
