import requests

import config

def new_tweets(bot):
	rs = requests.Session()
	for account, channel_id in config.bot.twitter['accounts'].items():
		last_tweet = config.state.tweet_ids.get(account)

		r = rs.get('https://api.twitter.com/1.1/statuses/user_timeline.json',
			params={'screen_name': account, 'count': 25, 'tweet_mode': 'extended'},
			headers={'Authorization': 'Bearer ' + config.bot.twitter['bearer_token']})
		r.raise_for_status()
		embeds = []
		tweets = r.json()
		for tweet in tweets:
			if tweet['id'] == last_tweet:
				break # tweets are newest first
			if len(tweet['entities']['user_mentions']) > 0:
				continue

			author_url = 'https://twitter.com/' + account
			embed = {
				'description': tweet['full_text'],
				'url': author_url + '/status/' + tweet['id_str'],
				'author': {'name': account, 'url': author_url, 'icon_url': tweet['user']['profile_image_url_https']},
			}
			media = tweet['entities'].get('media')
			if media:
				embed['image'] = {'url': media[0]['media_url_https'] + ':small'}
			embeds.append(embed)

		for embed in reversed(embeds):
			bot.send_message(channel_id, '<%s>' % embed['url'], embed)
		config.state.tweet_ids[account] = tweets[0]['id']
	config.state.save()
