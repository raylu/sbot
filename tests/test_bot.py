import unittest

from tests import mock_config

unittest.TestCase.assert_equal = unittest.TestCase.assertEqual

class TestInteractionEvent(unittest.TestCase):
	@classmethod
	def setUpClass(cls):
		mock_config.set_up_class(cls, 'bot')

	@classmethod
	def tearDownClass(cls):
		mock_config.tear_down_class(cls)

	def test_init(self):
		d = {
			'version': 1,
			'type': 2,
			'token': 'faketoken',
			'member': {
				'user': {
					'username': 'raylu',
					'public_flags': 0,
					'id': '109405765848088576',
					'discriminator': '4444',
					'avatar': 'c9e5c7c95dabd8f8bbb16c93156f12ed',
				},
				'roles': ['212431241587326977'],
				'premium_since': '2021-06-11T16:31:36.106000+00:00',
				'permissions': '274877906943',
				'pending': False,
				'nick': None,
				'mute': False,
				'joined_at': '2015-10-30T01:53:30.907000+00:00',
				'is_pending': False,
				'deaf': False,
				'avatar': None
			},
			'id': '869800892336066580',
			'guild_id': '109469702010478592',
			'data': {
				'options': [
					{
						'type': 1,
						'options': [
							{
								'value': 'hi there',
								'type': 3,
								'name': 'thing',
							},
							{
								'value': '1m',
								'type': 3,
								'name': 'duration',
							},
						],
						'name': 'add',
					},
				],
				'name': 'timer',
				'id': '869795468882894888'
			},
			'channel_id': '282441291327864834',
			'application_id': '713159744516259880',
		}
		interaction_event = self.bot.InteractionEvent(d, None)
		self.assert_equal(interaction_event.args, 'add hi there 1m')

		d =  {
			'version': 1,
			'type': 2,
			'token': 'faketoken',
			'member': {
				'user': {
					'username': 'raylu',
					'public_flags': 0,
					'id': '109405765848088576',
					'discriminator': '4444',
					'avatar': 'c9e5c7c95dabd8f8bbb16c93156f12ed',
				},
				'roles': ['212431241587326977'],
				'premium_since': '2021-06-11T16:31:36.106000+00:00',
				'permissions': '274877906943',
				'pending': False,
				'nick': None,
				'mute': False,
				'joined_at': '2015-10-30T01:53:30.907000+00:00',
				'is_pending': False,
				'deaf': False,
				'avatar': None,
			},
			'id': '869810272448155678',
			'guild_id': '109469702010478592',
			'data': {
				'options': [
					{
						'type': 1,
						'name': 'list',
					},
				],
				'name': 'timer',
				'id': '869795468882894888',
			},
			'channel_id': '282441291327864834',
			'application_id': '713159744516259880',
		}
		interaction_event = self.bot.InteractionEvent(d, None)
		self.assert_equal(interaction_event.args, 'list')
