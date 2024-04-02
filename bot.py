import _thread
import copy
import datetime
import importlib
import json
import mimetypes
import os
import re
import sys
import threading
import time
import traceback
import urllib.parse
import zlib
from collections import defaultdict

import requests
import websocket

import advent_of_code
import command
import config
import instagram
import log
import sbds
import steam_news
import twitch
import twitter
import warframe
from timer import readable_rel

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
		self.advent_of_code_thread = None
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
			'INTERACTION_CREATE': self.handle_interaction_create,
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

		url = config.state.gateway_url + '?v=9&encoding=json'
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
				except Exception:
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

	def get(self, path, params=None):
		response = self.rs.get('https://discord.com/api' + path, params=params)
		# https://discord.com/developers/docs/topics/rate-limits#header-format
		if response.headers.get('X-RateLimit-Remaining') == '0':
			wait_time = int(response.headers['X-RateLimit-Reset-After'])
			log.write('waiting %d for rate limit' % wait_time)
			time.sleep(wait_time)
		response.raise_for_status()
		return response.json()

	def post(self, path, data, files=None, method='POST'):
		if config.bot.debug:
			print('=>', path, data)
		response = self.rs.request(method, 'https://discord.com/api' + path, files=files, json=data)
		if response.headers.get('X-RateLimit-Remaining') == '0':
			wait_time = int(response.headers['X-RateLimit-Reset-After'])
			log.write('waiting %d for rate limit' % wait_time)
			time.sleep(wait_time)
		if response.status_code >= 400:
			log.write('response: %r' % response.content)
		response.raise_for_status()
		if response.status_code != 204: # No Content
			return response.json()
		return None

	def send(self, op, d):
		raw_data = json.dumps({'op': op, 'd': d})
		if config.bot.debug:
			print('->', raw_data)
		self.ws.send(raw_data)

	def send_message(self, channel_id, text: str, embed=None, files=None):
		if files is None:
			data = {'content': text}
			if embed is not None:
				if isinstance(embed, list):
					data['embeds'] = embed
				else:
					data['embed'] = embed
			self.post('/channels/%s/messages' % channel_id, data)
		else:
			assert text is None
			self.post('/channels/%s/messages' % channel_id, None, files)

	def get_message(self, channel_id, message_id):
		return self.get('/channels/%s/messages/%s' % (channel_id, message_id))

	def iter_messages(self, channel_id, after, last):
		path = '/channels/%s/messages' % (channel_id)
		params = {'after': after}
		while True:
			messages = self.get(path, params)
			messages.sort(key=lambda m: m['id'])
			for message in messages:
				yield message
				if message['id'] >= last:
					return
			params['after'] = message['id']
			time.sleep(2)

	def delete_messages(self, channel_id, message_ids):
		if len(message_ids) == 1:
			path = '/channels/%s/messages/%s' % (channel_id, message_ids[0])
			self.post(path, None, method='DELETE')
		else:
			path = '/channels/%s/messages/bulk-delete' % channel_id
			for i in range(0, len(message_ids), 100):
				self.post(path, {'messages': message_ids[i:i+100]})

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
			'intents': INTENT.GUILDS | INTENT.GUILD_MESSAGES | INTENT.GUILD_MESSAGE_REACTIONS | INTENT.DIRECT_MESSAGES,
			'properties': {
				'$browser': 'github.com/raylu/sbot',
				'$device': 'github.com/raylu/sbot',
			},
			'compress': True,
			'large_threshold': 50,
			'shard': [0, 1],
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
		if config.bot.advent_of_code is not None and datetime.date.today().month in (12, 1):
			self.advent_of_code_thread = _thread.start_new_thread(self.advent_of_code_loop, ())

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
		elif matches := re.findall(r'\[\[(.+?)\]\]', content): # respond to [[tennado]]
			embeds = list(filter(None, (sbds.get_embed(m) for m in matches)))[:4]
			if len(embeds) > 0:
				self.send_message(d['channel_id'], '', embeds)
		elif not content.startswith('!'):
			return

		lines = content[1:].split('\n', 1)
		split = lines[0].split(' ', 1)
		handler = self.commands.get(split[0])
		if handler:
			if config.bot.autoreload:
				handler = self._autoreload(split[0], handler)

			arg = ''
			if len(split) == 2:
				arg = split[1]
			if len(lines) == 2:
				arg += '\n' + lines[1]
			cmd = CommandEvent(d, arg, self)
			cmd.sender['pretty_name'] = cmd.d['member']['nick'] or \
										cmd.sender['global_name'] or \
										cmd.sender['username']
			handler(cmd)

	def handle_interaction_create(self, d):
		if d.get('member', {}).get('user', {}).get('bot'):
			return

		handler = self.commands.get(d['data']['name'])
		if handler:
			if config.bot.autoreload:
				handler = self._autoreload(d['data']['name'], handler)

			path = '/interactions/%s/%s/callback' % (d['id'], d['token'])
			self.post(path, {'type': INTERACTION.DEFERRED_CHANNEL_MESSAGE_WITH_SOURCE})

			cmd = InteractionEvent(d, self)
			try:
				handler(cmd)
			except Exception:
				cmd.reply('an error occurred')
				raise

	def _autoreload(self, command_name, handler):
		module_name = handler.__module__
		module = sys.modules[module_name]
		path = module.__file__
		new_mtime = os.stat(path).st_mtime
		if new_mtime > self.mtimes[module_name]:
			importlib.reload(module)
			self.mtimes[module_name] = new_mtime
			for trigger in self.modules[module_name]:
				handler_name = self.commands[trigger].__name__
				self.commands[trigger] = getattr(module, handler_name)
				if trigger == command_name:
					handler = self.commands[trigger]
					# continue replacing all the commands in the reloaded file; do not break/return
		return handler

	def handle_reaction_add(self, d):
		if config.bot.twitter_post is None:
			return

		if d['channel_id'] != config.bot.twitter_post['channel'] or \
				d['emoji']['name'] != 'shrfood_twitter' or d['user_id'] == self.user_id:
			return

		if d['message_id'] in config.state.twitter_queue:
			return

		message = self.get_message(d['channel_id'], d['message_id'])
		attachments = message.get('attachments')
		if not attachments:
			self.react(d['channel_id'], d['message_id'], '🙈')
			return

		for attachment in attachments[:4]:
			media_type, _ = mimetypes.guess_type(attachment['filename'])
			if media_type.startswith('video/'):
				if len(attachments) != 1:
					self.react(d['channel_id'], d['message_id'], '🧐')
					return
				if attachment['size'] > 5000000:
					self.react(d['channel_id'], d['message_id'], '😓')
					return

		config.state.twitter_queue.append(d['message_id'])
		config.state.save()

		self.react(d['channel_id'], d['message_id'], '✅')
		with self.twitter_post_condvar:
			self.twitter_post_condvar.notify()

	def handle_reaction_remove(self, d):
		if config.bot.twitter_post is None:
			return

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
			now = datetime.datetime.now(datetime.timezone.utc)
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
			except requests.exceptions.HTTPError as e:
				log.write('twitter: %s\n%s' % (e, e.response.text[:1000]))
			except requests.exceptions.RequestException as e:
				log.write('twitter: %s' % e)
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

	def advent_of_code_loop(self):
		while True:
			time.sleep(60 * 30)
			try:
				advent_of_code.check_leaderboards(self)
			except requests.exceptions.HTTPError as e:
				log.write('advent of code: %s\n%s' % (e, e.response.text[:1000]))
			except requests.exceptions.RequestException as e:
				log.write('advent of code: %s' % e)

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
	def __init__(self, d, args: str, bot: Bot):
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

class InteractionEvent:
	def __init__(self, d, bot):
		self.token = d['token']
		self.channel_id = d['channel_id']
		self.sender = d['member']['user']
		self.options = d['data'].get('options', [])
		self.args = ' '.join(InteractionEvent.iter_option_values(self.options))
		self.bot = bot

	def reply(self, message, embed=None):
		path = '/webhooks/%s/%s/messages/@original' % (config.bot.app_id, self.token)
		data = {'content': message}
		if embed:
			data['embeds'] = [embed]
		self.bot.post(path, data, method='PATCH')

	@classmethod
	def iter_option_values(cls, options):
		for option in options:
			if option['type'] in (command.OPTION_TYPE.SUB_COMMAND, command.OPTION_TYPE.SUB_COMMAND_GROUP):
				yield option['name']
				yield from cls.iter_option_values(option.get('options', []))
			else:
				yield str(option['value'])

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

# https://discord.com/developers/docs/topics/gateway#gateway-intents
class INTENT:
	GUILDS                    = 1 << 0
	GUILD_MEMBERS             = 1 << 1
	GUILD_BANS                = 1 << 2
	GUILD_EMOJIS_AND_STICKERS = 1 << 3
	GUILD_INTEGRATIONS        = 1 << 4
	GUILD_WEBHOOKS            = 1 << 5
	GUILD_INVITES             = 1 << 6
	GUILD_VOICE_STATES        = 1 << 7
	GUILD_PRESENCES           = 1 << 8
	GUILD_MESSAGES            = 1 << 9
	GUILD_MESSAGE_REACTIONS   = 1 << 10
	GUILD_MESSAGE_TYPING      = 1 << 11
	DIRECT_MESSAGES           = 1 << 12
	DIRECT_MESSAGE_REACTIONS  = 1 << 13
	DIRECT_MESSAGE_TYPING     = 1 << 14

# https://discord.com/developers/docs/interactions/slash-commands#interaction-response-object-interaction-callback-type
class INTERACTION:
	CHANNEL_MESSAGE_WITH_SOURCE          = 4
	DEFERRED_CHANNEL_MESSAGE_WITH_SOURCE = 5
