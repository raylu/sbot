import time

import yaml

import log

class YamlAttrs:
	def __init__(self, filename, defaults=None):
		self.filename = filename

		try:
			with open(filename, 'r', encoding='utf-8') as f:
				doc = yaml.safe_load(f)
		except FileNotFoundError:
			doc = defaults
			log.write('creating ' + self.filename)
			self.save()

		for k, v in doc.items():
			setattr(self, k, v)

	def save(self):
		with open(self.filename, 'w', encoding='utf-8') as f:
			data = dict(self.__dict__)
			del data['filename']
			yaml.dump(data, f)

	def __str__(self):
		return '%s %s' % (self.__class__, self.__dict__)

bot = YamlAttrs('config.yaml')
state = YamlAttrs('state.yaml',
	defaults={
		'advent_of_code_last_check': int(time.time()),
		'gateway_url': None,
		'instagram': {},
		'reddit_access_token': None,
		'steam_news_ids': {},
		'timers': {},
		'tweet_ids': {},
		'twitch_last_times': {},
		'twitter_last_post_time': None,
		'twitter_queue': [],
	})
