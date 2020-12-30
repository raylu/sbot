from collections import defaultdict
import copy
import datetime
import imp
import json
import os
import sys
import threading
import time
import traceback
import urllib.parse
import zlib
import _thread  # pylint: disable=wrong-import-order

import requests
import websocket

import config
import instagram
import log
import steam_news
from timer import readable_rel
import twitch
import twitter
import warframe

class Bot:
	def __init__(self, commands):
		self.ws = None
		self.rs = requests.Session()
		self.rs.headers['Authorization'] = 'Bot ' + config.bot.token
		self.rs.headers['User-Agent'] = 'DiscordBot (https://github.com/raylu/sbot 0.0)'
		self.heartbeat_thread = None
		self.timer_thread = None
		self.timer_condvar = threading.Condition()
		self.zkill_thread = None
		self.warframe_thread = None
		self.twitch_thread = None
		self.twitter_thread = None
		self.twitter_post_thread = None
		self.twitter_post_condvar = threading.Condition()
		self.instagram_thread = None
		self.steam_news_thread = None
		self.user_id = None
		self.seq = None
		self.guilds = {} # guild id -> Guild
		self.channels = {} # channel id -> guild id


		self.handlers = {
			OP.HELLO: self.handle_hello,
			OP.DISPATCH: self.handle_dispatch,
		}
		self.events = {
			'READY': self.handle_ready,
			'MESSAGE_CREATE': self.handle_message_create,
			'MESSAGE_REACTION_ADD': self.handle_reaction_add,
			'MESSAGE_REACTION_REMOVE': self.handle_reaction_remove,
			'GUILD_CREATE': self.handle_guild_create,
			'GUILD_ROLE_CREATE': self.handle_guild_role_create,
			'GUILD_ROLE_UPDATE': self.handle_guild_role_update,
			'GUILD_ROLE_DELETE': self.handle_guild_role_delete,
		}
		self.commands = commands

		if config.bot.autoreload:
			self.mtimes = {}
			self.modules = defaultdict(list)
			for trigger, handler in commands.items():
				module_name = handler.__module__
				module = sys.modules[module_name]
				path = module.__file__
				if module_name not in self.mtimes:
					self.mtimes[module_name] = os.stat(path).st_mtime
				self.modules[module_name].append(trigger)

	def connect(self):
		if config.state.gateway_url is None:
			data = self.get('/gateway/bot')
			config.state.gateway_url = data['url']
			config.state.save()

		url = config.state.gateway_url + '?v=6&encoding=json'
		self.ws = websocket.create_connection(url)

	def run_forever(self):
		while True:
			raw_data = self.ws.recv()
			# one might think that after sending "compress": true, we can expect to only receive
			# compressed data. one would be underestimating discord's incompetence
			if isinstance(raw_data, bytes):
				raw_data = zlib.decompress(raw_data).decode('utf-8')
			if not raw_data:
				break
			if config.bot.debug:
				print('<-', raw_data)
			data = json.loads(raw_data)
			self.seq = data['s']
			handler = self.handlers.get(data['op'])
			if handler:
				try:
					handler(data['t'], data['d'])
				except:
					tb = traceback.format_exc()
					log.write(data)
					log.write(tb)
					if config.bot.err_channel:
						try:
							# messages can be up to 2000 characters
							self.send_message(config.bot.err_channel,
									'```\n%s\n```\n```\n%s\n```' % (raw_data[:800], tb[:1000]))
						except Exception:
							log.write('error sending to err_channel:\n' + traceback.format_exc())
			log.flush()

	def get(self, path):
		response = self.rs.get('https://discord.com/api' + path)
		response.raise_for_status()
		return response.json()

	def post(self, path, data, files=None, method='POST'):
		if config.bot.debug:
			print('=>', path, data)
		response = self.rs.request(method, 'https://discord.com/api' + path, files=files, json=data)
		response.raise_for_status()
		if response.status_code != 204: # No Content
			return response.json()
		return None

	def send(self, op, d):
		raw_data = json.dumps({'op': op, 'd': d})
		if config.bot.debug:
			print('->', raw_data)
		self.ws.send(raw_data)

	def send_message(self, channel_id, text, embed=None, files=None):
		if files is None:
			data = {'content': text}
			if embed is not None:
				data['embed'] = embed
			self.post('/channels/%s/messages' % channel_id, data)
		else:
			assert text is None
			self.post('/channels/%s/messages' % channel_id, None, files)

	def react(self, channel_id, message_id, emoji):
		path = '/channels/%s/messages/%s/reactions/%s/@me' % (
				channel_id, message_id, urllib.parse.quote(emoji))
		self.post(path, None, method='PUT')

	def remove_reaction(self, channel_id, message_id, emoji):
		path = '/channels/%s/messages/%s/reactions/%s/@me' % (
				channel_id, message_id, urllib.parse.quote(emoji))
		self.post(path, None, method='DELETE')

	def get_reactions(self, channel_id, message_id, emoji):
		return self.get('/channels/%s/messages/%s/reactions/%s' % (channel_id, message_id, emoji))

	def ban(self, guild_id, user_id):
		self.post('/guilds/%s/bans/%s' % (guild_id, user_id), {}, method='PUT')

	def handle_hello(self, _, d):
		log.write('connected to %s' % d['_trace'])
		self.heartbeat_thread = _thread.start_new_thread(self.heartbeat_loop, (d['heartbeat_interval'],))
		self.send(OP.IDENTIFY, {
			'token': config.bot.token,
			'properties': {
				'$browser': 'github.com/raylu/sbot',
				'$device': 'github.com/raylu/sbot',
			},
			'compress': True,
			'large_threshold': 50,
			'shard': [0, 1]
		})

	def handle_dispatch(self, event, d):
		handler = self.events.get(event)
		if handler:
			handler(d)

	def handle_ready(self, d):
		log.write('connected as ' + d['user']['username'])
		self.user_id = d['user']['id']
		self.timer_thread = _thread.start_new_thread(self.timer_loop, ())
		if config.bot.zkillboard is not None:
			self.zkill_thread = _thread.start_new_thread(self.zkill_loop, ())
		if config.bot.warframe is not None:
			self.warframe_thread = _thread.start_new_thread(self.warframe_loop, ())
		if config.bot.twitch is not None:
			self.twitch_thread = _thread.start_new_thread(self.twitch_loop, ())
		if config.bot.twitter is not None:
			self.twitter_thread = _thread.start_new_thread(self.twitter_loop, ())
		if config.bot.twitter_post is not None:
			self.twitter_post_thread = _thread.start_new_thread(self.twitter_post_loop, ())
		if config.bot.instagram is not None:
			self.instagram_thread = _thread.start_new_thread(self.instagram_loop, ())
		if config.bot.steam_news is not None:
			self.steam_news_thread = _thread.start_new_thread(self.steam_news_loop, ())

	def handle_message_create(self, d):
		if d['author'].get('bot'):
			return

		content = d['content']
		if content.casefold() == 'oh no.':
			cmd = CommandEvent(d, None, self)
			self.commands['ohno'](cmd)
			return
		elif content.casefold() == 'oh yes.':
			cmd = CommandEvent(d, None, self)
			self.commands['ohyes'](cmd)
			return
		if not content.startswith('!'):
			return

		lines = content[1:].split('\n', 1)
		split = lines[0].split(' ', 1)
		handler = self.commands.get(split[0])
		if handler:
			if config.bot.autoreload:
				module_name = handler.__module__
				module = sys.modules[module_name]
				path = module.__file__
				new_mtime = os.stat(path).st_mtime
				if new_mtime > self.mtimes[module_name]:
					imp.reload(module)
					self.mtimes[module_name] = new_mtime
					for trigger in self.modules[module_name]:
						handler_name = self.commands[trigger].__name__
						self.commands[trigger] = getattr(module, handler_name)
						if trigger == split[0]:
							handler = self.commands[trigger]

			arg = ''
			if len(split) == 2:
				arg = split[1]
			if len(lines) == 2:
				arg += '\n' + lines[1]
			cmd = CommandEvent(d, arg, self)
			handler(cmd)

	def handle_reaction_add(self, d):
		if d['channel_id'] != config.bot.twitter_post['channel'] or \
				d['emoji']['name'] != 'shrfood_twitter' or d['user_id'] == self.user_id:
			return

		if d['message_id'] in config.state.twitter_queue:
			return
		config.state.twitter_queue.append(d['message_id'])
		config.state.save()

		self.react(d['channel_id'], d['message_id'], '✅')
		with self.twitter_post_condvar:
			self.twitter_post_condvar.notify()

	def handle_reaction_remove(self, d):
		if d['channel_id'] != config.bot.twitter_post['channel'] or \
				d['emoji']['name'] != 'shrfood_twitter':
			return

		emoji = '%s:%s' % (d['emoji']['name'], d['emoji']['id'])
		reactions = self.get_reactions(d['channel_id'], d['message_id'], emoji)
		if len(reactions) == 0: # no more shrfood_twitter emoji
			try:
				config.state.twitter_queue.remove(d['message_id'])
			except ValueError:
				return
			config.state.save()

			self.remove_reaction(d['channel_id'], d['message_id'], '✅')

	def handle_guild_create(self, d):
		log.write('in guild %s (%d members)' % (d['name'], d['member_count']))
		self.guilds[d['id']] = Guild(d)
		for channel in d['channels']:
			self.channels[channel['id']] = d['id']

	def handle_guild_role_create(self, d):
		role = d['role']
		self.guilds[d['guild_id']].roles[role['name']] = role

	def handle_guild_role_update(self, d):
		role = d['role']
		if self._del_role(d['guild_id'], role['id']):
			self.guilds[d['guild_id']].roles[role['name']] = role
		else:
			log.write("couldn't find role for deletion: %r" % d)

	def handle_guild_role_delete(self, d):
		if not self._del_role(d['guild_id'], d['role_id']):
			log.write("couldn't find role for deletion: %r" % d)

	def _del_role(self, guild_id, role_id):
		roles = self.guilds[guild_id].roles
		for role in roles.values():
			if role['id'] == role_id:
				del roles[role['name']]
				return True
		return False

	def heartbeat_loop(self, interval_ms):
		interval_s = interval_ms / 1000
		while True:
			time.sleep(interval_s)
			self.send(OP.HEARTBEAT, self.seq)

	def timer_loop(self):
		while True:
			wakeups = []
			now = datetime.datetime.utcnow()
			hour_from_now = now + datetime.timedelta(hours=1)
			for channel_id, timers in config.state.timers.items():
				for name, dt in copy.copy(timers).items():
					if dt <= now:
						self.send_message(channel_id, 'removing expired timer "%s" for %s' %
								(name, dt.strftime('%Y-%m-%d %H:%M:%S')))
						del timers[name]
						config.state.save()
					elif dt <= hour_from_now:
						self.send_message(channel_id, '%s until %s' % (readable_rel(dt - now), name))
						wakeups.append(dt)
					else:
						wakeups.append(dt - datetime.timedelta(hours=1))
			wakeup = None
			if wakeups:
				wakeups.sort()
				wakeup = (wakeups[0] - now).total_seconds()
			with self.timer_condvar:
				self.timer_condvar.wait(wakeup)

	def zkill_loop(self):
		while True:
			r = self.rs.get('https://redisq.zkillboard.com/listen.php', params={'ttw': 30})
			if r.ok:
				data = r.json()
				if not data or not data['package']:
					time.sleep(10)
					continue
				killmail = data['package']['killmail']
				victim = killmail['victim']

				characters = killmail['attackers']
				characters.append(victim)
				for char in characters:
					if 'alliance' in char and char['alliance']['id'] == config.bot.zkillboard['alliance']:
						break
				else: # alliance not involved in kill
					continue

				if 'character' not in victim:
					continue
				victim_name = victim['character']['name']
				ship = victim['shipType']['name']
				cost = data['package']['zkb']['totalValue'] / 1000000
				url = 'https://zkillboard.com/kill/%d/' % killmail['killID']
				self.send_message(config.bot.zkillboard['channel'],
						"%s's **%s** (%d mil) %s" % (victim_name, ship, cost, url))
			else:
				log.write('zkill: %s %s\n%s' % (r.status_code, r.reason, r.text[:1000]))
				time.sleep(30)

	def warframe_loop(self):
		last_alerts = []
		while True:
			time.sleep(5 * 60)
			try:
				alerts = warframe.alert_analysis()
				broadcast_alerts = set(alerts) - set(last_alerts)
				if len(broadcast_alerts) > 0:
					self.send_message(config.bot.warframe['channel'], '\n'.join(broadcast_alerts))
				last_alerts = alerts
			except requests.exceptions.HTTPError as e:
				log.write('warframe: %s\n%s' % (e, e.response.text[:1000]))
			except requests.exceptions.RequestException as e:
				log.write('warframe: %s' % e)

	def twitch_loop(self):
		while True:
			# https://dev.twitch.tv/docs/api/guide#rate-limits
			# 30 points per minute, streams endpoint costs 1 point
			time.sleep(15)
			try:
				twitch.live_streams(self)
			except requests.exceptions.HTTPError as e:
				log.write('twitch: %s\n%s' % (e, e.response.text[:1000]))
			except requests.exceptions.RequestException as e:
				log.write('twitch: %s' % e)

	def twitter_loop(self):
		while True:
			# https://developer.twitter.com/en/docs/tweets/timelines/api-reference/get-statuses-user_timeline.html
			# 100,000 in 24 hours is 69.4 a minute, so wait 1 minute per account (1 request per account)
			time.sleep(60 * len(config.bot.twitter['accounts']))
			try:
				twitter.new_tweets(self)
			except requests.exceptions.HTTPError as e:
				log.write('twitter: %s\n%s' % (e, e.response.text[:1000]))
			except requests.exceptions.RequestException as e:
				log.write('twitter: %s' % e)

	def twitter_post_loop(self):
		while True:
			if len(config.state.twitter_queue) == 0:
				with self.twitter_post_condvar:
					self.twitter_post_condvar.wait()
				continue

			sleep = 12 * 60 * 60 # 12 hours
			if config.state.twitter_last_post_time:
				sleep = config.state.twitter_last_post_time + sleep - time.time()
			with self.twitter_post_condvar:
				self.twitter_post_condvar.wait(sleep)
			if config.state.twitter_last_post_time and \
					time.time() < config.state.twitter_last_post_time + 12 * 60 * 60:
				# we were woken up by a reaction add but it's too early
				continue

			try:
				twitter.post(self, config.state.twitter_queue[0])
				config.state.twitter_queue.pop(0)
			except Exception:
				log.write('twitter post:\n' + traceback.format_exc())
			# always update the last post time, even if we failed to tweet
			config.state.twitter_last_post_time = int(time.time())
			config.state.save()

	def instagram_loop(self):
		while True:
			# https://developers.facebook.com/docs/graph-api/overview/rate-limiting#platform-rate-limits
			# 240 * users / hour is 4✕ what we'll need
			time.sleep(60)
			try:
				instagram.new_media(self)
			except requests.exceptions.HTTPError as e:
				log.write('instagram: %s\n%s' % (e, e.response.text[:1000]))
			except requests.exceptions.RequestException as e:
				log.write('instagram: %s' % e)

	def steam_news_loop(self):
		while True:
			time.sleep(60)
			try:
				steam_news.news(self)
			except requests.exceptions.HTTPError as e:
				log.write('steam news: %s\n%s' % (e, e.response.text[:1000]))
			except requests.exceptions.RequestException as e:
				log.write('steam news: %s' % e)

class Guild:
	def __init__(self, d):
		self.roles = {} # name -> {
		#	'color': 0,
		#	'hoist': False,
		#	'id': '282441120896516096',
		#	'managed': True,
		#	'mentionable': False,
		#	'name': 'sbot',
		#	'permissions': 805637184,
		#	'position': 5,
		# }
		for role in d['roles']:
			self.roles[role['name']] = role

class CommandEvent:
	def __init__(self, d, args, bot):
		self.d = d
		self.channel_id = d['channel_id']
		# sender = {
		#     'username': 'raylu',
		#     'id': '109405765848088576',
		#     'discriminator': '8396',
		#     'avatar': '464d73d2ca17733636282ab58b8cc3f5',
		# }
		self.sender = d['author']
		self.args = args
		self.bot = bot

	def reply(self, message, embed=None, files=None):
		self.bot.send_message(self.channel_id, message, embed, files)

	def react(self, emoji):
		self.bot.react(self.channel_id, self.d['id'], emoji)

class OP:
	DISPATCH              = 0
	HEARTBEAT             = 1
	IDENTIFY              = 2
	STATUS_UPDATE         = 3
	VOICE_STATE_UPDATE    = 4
	VOICE_SERVER_PING     = 5
	RESUME                = 6
	RECONNECT             = 7
	REQUEST_GUILD_MEMBERS = 8
	INVALID_SESSION       = 9
	HELLO                 = 10
	HEARTBEAT_ACK         = 11
