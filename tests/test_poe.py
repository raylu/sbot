import json
import textwrap
import unittest
from os import path
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

	def assert_reply(self, q, value=None, matches=None):
		cmd = MockCmd(q)
		poe.price(cmd)
		if value is not None:
			self.assert_equal(cmd.reply_text, '')
			self.assert_equal(cmd.reply_embed['fields'][0]['value'], textwrap.dedent(value).strip())
		else:
			self.assert_equal(cmd.reply_embed, None)
			self.assert_equal(set(cmd.reply_text.split(', ')), set(matches))

	def test_price(self):
		self.assert_reply('the strat', 'The Strategist: 125.0 chaos')
		self.assert_reply('of mirror', 'House of Mirrors: 3570.6 chaos, 21.0 divine')

	def test_exact(self):
		self.assert_reply('enlighten support', '''
			Enlighten Support (level 4) (corrupted): 1539.4 chaos, 9.0 divine
			Enlighten Support (level 3) (20%): 513.1 chaos, 3.0 divine
			Enlighten Support (level 1): 427.6 chaos, 2.5 divine
			Enlighten Support (level 2) (20%): 409.7 chaos, 2.4 divine
			Enlighten Support (level 3) (corrupted): 342.1 chaos, 2.0 divine
			Enlighten Support (level 1) (corrupted): 256.6 chaos, 1.5 divine
			Enlighten Support (level 2) (20%) (corrupted): 256.6 chaos, 1.5 divine
		''')

	def test_multi_match(self):
		self.assert_reply('exalt', matches=[
			"Redeemer's Exalted Orb",
			"Warlord's Exalted Orb",
			"Crusader's Exalted Orb",
			"Hunter's Exalted Orb",
			'Eldritch Exalted Orb',
			'Tainted Exalted Orb',
			'Exalted Orb',
			'Exalted Shard',
		])
		self.assert_reply('promise', matches=["Gemcutter's Promise", 'Broken Promises'])

	def test_no_match(self):
		self.assert_reply('fishing', matches=["couldn't find fishing"])

	@unittest.expectedFailure
	def test_relic(self):
		self.assert_reply('cane of unravelling', '''
			Cane of Unravelling (6 link): 28.0 chaos
			Cane of Unravelling (relic) (5 link): 11.0 chaos
			Cane of Unravelling (relic): 4.0 chaos
			Cane of Unravelling: 1.0 chaos
			Cane of Unravelling (5 link): 1.0 chaos
		''')

def get(url, params=None):
	if url == 'https://poe.ninja/api/data/getindexstate':
		with open(path.join(fixtures_dir, 'index_state.json')) as f:
			data = json.load(f)
		return mock.Mock(json=mock.Mock(return_value=data))
	elif url == 'https://poe.ninja/api/data/economysearch' and params == {'league': 'Kalandra'}:
		with open(path.join(fixtures_dir, 'economysearch_kalandra_fr.json')) as f:
			data = json.load(f)
		return mock.Mock(json=mock.Mock(return_value=data))
	elif url == 'https://poe.ninja/api/data/itemoverview':
		if params['type'] == 'Currency':
			return mock.Mock(status_code=404)
		filename = 'itemoverview_%s_%s.json' % (params['league'].lower(), params['type'].lower())
		with open(path.join(fixtures_dir, filename)) as f:
			data = json.load(f)
		return mock.Mock(status_code=200, json=mock.Mock(return_value=data))
	elif url == 'https://poe.ninja/api/data/currencyoverview':
		filename = 'currencyoverview_%s_%s.json' % (params['league'].lower(), params['type'].lower())
		with open(path.join(fixtures_dir, filename)) as f:
			data = json.load(f)
		return mock.Mock(status_code=200, json=mock.Mock(return_value=data))
	else:
		raise AssertionError('unexpected get', url, params)

class MockCmd:
	def __init__(self, args):
		self.args = args
		self.reply_text = self.reply_embed = None

	def reply(self, text, embed=None):
		self.reply_text = text
		self.reply_embed = embed
