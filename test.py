#!/usr/bin/env python3

import reddit

class MockCmd:
	def __init__(self):
		self.args = ''
		self.sender = {'username': 'testname'}

	def reply(self, text, embed=None):
		print(text, embed)

reddit.headpat(MockCmd())
