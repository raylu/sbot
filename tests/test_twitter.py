import unittest

import twitter

unittest.TestCase.assert_equal = unittest.TestCase.assertEqual

class TestTwitter(unittest.TestCase):
	def test_sign(self):
		params = {
			'status': 'Hello Ladies + Gentlemen, a signed OAuth request!',
			'include_entities': 'true',
			'oauth_consumer_key': 'xvz1evFS4wEEPTGEFPHBog',
			'oauth_nonce': 'kYjzVBB8Y0ZFabxSWbWovY3uYSQ2pTgmZeNu2VS4cg',
			'oauth_signature_method': 'HMAC-SHA1',
			'oauth_timestamp': '1318622958',
			'oauth_token': '370773112-GmHxMAgYyLbNEtIKZeRNFsMKPR9EyMZeS9weJAEb',
			'oauth_version': '1.0',
		}
		url = 'https://api.twitter.com/1.1/statuses/update.json'
		consumer_secret = 'kAcSOqF21Fu85e7zjz7ZN2U4ZRhfV3WpwPAoE3Z7kBw'
		token_secret = 'LswwdoUaIvS8ltyTt5jkRh4J50vUPVVHtR2YPi5kE'
		self.assert_equal(twitter.sign('POST', url, params, consumer_secret, token_secret),
				'hCtSmYh+iHYCEqBWrE7C7hYmtUk=')
