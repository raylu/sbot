import unittest
from unittest import mock

from tests import mock_config

unittest.TestCase.assert_equal = unittest.TestCase.assertEqual

class TestUtils(unittest.TestCase):
	@classmethod
	def setUpClass(cls):
		mock_config.set_up_class(cls, 'utils')

	@classmethod
	def tearDownClass(cls):
		mock_config.tear_down_class(cls)

	def test_time(self):
		self.assert_equal(self.parse_time('2000-01-02 03:04 PST'), 946811040)
		self.assert_equal(self.parse_time('2000-01-02 03:04 PDT'), 946811040)
		self.assert_equal(self.parse_time('2000-01-02 03:04 EST'), 946800240)

	def parse_time(self, s):
		mock_cmd = mock.Mock(args=s)
		self.utils.time(mock_cmd)
		return int(mock_cmd.reply.call_args[0][0].split(' ', 1)[0][3:-1])
