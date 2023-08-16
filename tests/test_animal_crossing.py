import datetime
import sys
import unittest
from unittest import mock

unittest.TestCase.assert_equal = unittest.TestCase.assertEqual

class TestAnimalCrossing(unittest.TestCase):
	user = {'id': '1', 'username': 'testuser'} # noqa: RUF012

	@classmethod
	def setUpClass(cls):
		mock_config = mock.Mock()
		mock_config.bot.acnh_db = ':memory:'
		sys.modules['config'] = mock_config

		try:
			import animal_crossing
			import friend_code

			cls.animal_crossing = animal_crossing
			cls.db = animal_crossing.db
			with open('acnh.sql', 'r') as f:
				for statement in f.read().split(';')[:-1]:
					cls.db.execute(statement)

			friend_code.friend_code(mock.Mock(args='set SW-0000-0000-0000', sender=cls.user))
			animal_crossing.stalk_market(mock.Mock(args='tz America/Indiana/Indianapolis', sender=cls.user))
		except Exception:
			del sys.modules['config']
			raise

	def tearDown(self):
		self.db.execute('DELETE FROM price')

	@classmethod
	def tearDownClass(cls):
		del sys.modules['config']

	def test_set_buy_price(self):
		mock_cmd = mock.Mock(sender=self.user)
		utc = datetime.timezone.utc
		dts = [
			datetime.datetime(2000, 1, 2, 10, tzinfo=utc), # 05:00 sunday
			datetime.datetime(2000, 1, 3, 10, tzinfo=utc), # 05:00 monday
		]
		for now in dts:
			with mock.patch('animal_crossing.datetime') as mock_dt:
				mock_dt.datetime.now.return_value = now
				mock_dt.datetime.combine = datetime.datetime.combine
				mock_dt.timezone.utc = utc
				mock_dt.timedelta = datetime.timedelta
				mock_dt.time = datetime.time
				self.animal_crossing._stalk_set_buy_price(mock_cmd, '100')
			reply = mock_cmd.reply.call_args[0][0]
			assert reply.startswith('Buy price recorded at 100 bells.'), reply

			[row] = self.db.execute('SELECT * FROM price').fetchall()
			self.assert_equal(row['week_local'], '2000-01-02')
			self.assert_equal(row['week_index'], 0)
			self.assert_equal(row['price'], 100)
			self.assert_equal(row['expiration'], '2000-01-02 17:00:00+00:00')
