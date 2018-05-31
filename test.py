#!/usr/bin/env python3

import poe

class MockCmd:
	def __init__(self):
		self.args = 'starforge'
		self.sender = {'username': 'testname'}

	def reply(self, text, embed=None):
		print(text, embed)

poe.price(MockCmd())
