import json
from os import path
import textwrap
import unittest
from unittest import mock

import poe

unittest.TestCase.assert_equal = unittest.TestCase.assertEqual
fixtures_dir = path.join(path.dirname(path.abspath(__file__)), 'poe.ninja')

class TestPoe(unittest.TestCase):
	@classmethod
	def setUpClass(cls):
		cls.original_rs = poe.rs
		poe.rs = mock.Mock()
		poe.rs.get = get

		cls.maxDiff = 1000

	@classmethod
	def tearDownClass(cls):
		poe.rs = cls.original_rs

	def assert_reply(self, q, value):
		cmd = MockCmd(q)
		poe.price(cmd)
		self.assert_equal(cmd.reply_text, '')
		self.assert_equal(cmd.reply_embed['fields'][0]['value'], textwrap.dedent(value).strip())

	def test_price(self):
		self.assert_reply('the strat', 'The Strategist: 45.0 chaos')
		self.assert_reply('le stratège', 'The Strategist: 45.0 chaos')

	def test_exact(self):
		self.assert_reply('enlighten support', '''
		Enlighten Support (level 4) (20%) (corrupted): 390.9 chaos, 3.9 exalted
		Enlighten Support (level 3): 59.0 chaos
		Enlighten Support (level 2): 27.6 chaos
		Enlighten Support (level 1): 22.0 chaos
		Enlighten Support (level 3) (corrupted): 15.0 chaos
		Enlighten Support (level 1) (corrupted): 15.0 chaos
		Enlighten Support (level 2) (corrupted): 14.0 chaos
		''')

def get(url, params=None):
	if url == 'https://poe.ninja/':
		with open(path.join(fixtures_dir, 'index.html')) as f:
			return mock.Mock(text=f.read())
	elif url == 'https://poe.ninja/api/data/economysearch' and params == {'league': 'Ritual', 'language': 'fr'}:
		with open(path.join(fixtures_dir, 'economysearch_ritual_fr.json')) as f:
			data = json.load(f)
		return mock.Mock(json=mock.Mock(return_value=data))
	elif url == 'https://poe.ninja/api/data/itemoverview':
		filename = 'itemoverview_%s_%s.json' % (params['league'].lower(), params['type'].lower())
		with open(path.join(fixtures_dir, filename)) as f:
			data = json.load(f)
		return mock.Mock(status_code=200, json=mock.Mock(return_value=data))
	else:
		raise AssertionError('unexpected get', url, params)

class MockCmd:
	def __init__(self, args):
		self.args = args

	def reply(self, text, embed=None):
		self.reply_text = text
		self.reply_embed = embed
