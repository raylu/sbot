from collections import defaultdict
import copy
import datetime
import imp
import json
import os
import sys
import _thread
import threading
import time
import traceback
import zlib

import requests
import websocket

import config
from utils import readable_rel

class Bot:
	def __init__(self, commands):
		self.ws = None
		self.rs = requests.Session()
		self.rs.headers['Authorization'] = 'Bot ' + config.bot.token
		self.rs.headers['User-Agent'] = 'DiscordBot (https://github.com/raylu/sbot 0.0'
		self.heartbeat_thread = None
		self.timer_thread = None
		self.timer_condvar = threading.Condition()
		self.zkill_thread = None
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
			'GUILD_CREATE': self.handle_guild_create,
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

		url = config.state.gateway_url + '?v=5&encoding=json'
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
					if config.bot.err_channel:
						try:
							self.send_message(config.bot.err_channel, '```\n%s\n```' % tb[:2000])
						except Exception as e:
							print('error sending to err_channel: %r' % e, file=sys.stderr)
					print(tb, file=sys.stderr)

	def get(self, path):
		response = self.rs.get('https://discordapp.com/api' + path)
		response.raise_for_status()
		return response.json()

	def post(self, path, data, method='POST'):
		if config.bot.debug:
			print('=>', path, data)
		response = self.rs.request(method, 'https://discordapp.com/api' + path, json=data)
		response.raise_for_status()
		if response.status_code != 204: # No Content
			return response.json()

	def send(self, op, d):
		raw_data = json.dumps({'op': op, 'd': d})
		if config.bot.debug:
			print('->', raw_data)
		self.ws.send(raw_data)

	def send_message(self, channel_id, text, embed=None):
		data = {'content': text}
		if embed is not None:
			data['embed'] = embed
		self.post('/channels/%s/messages' % channel_id, data)

	def handle_hello(self, _, d):
		print('connected to', d['_trace'])
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
		print('connected as', d['user']['username'])
		self.user_id = d['user']['id']
		self.timer_thread = _thread.start_new_thread(self.timer_loop, ())
		if config.bot.zkillboard is not None:
			self.zkill_thread = _thread.start_new_thread(self.zkill_loop, ())

	def handle_message_create(self, d):
		content = d['content']
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
			cmd = CommandEvent(d['channel_id'], d['author'], arg, self)
			handler(cmd)

	def handle_guild_create(self, d):
		self.guilds[d['id']] = Guild(d)
		for channel in d['channels']:
			self.channels[channel['id']] = d['id']

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
			for name, time in copy.copy(config.state.timers).items():
				if time <= now:
					self.send_message(config.bot.timer_channel, 'removing expired timer "%s" for %s' %
							(name, time.strftime('%Y-%m-%d %H:%M:%S')))
					del config.state.timers[name]
					config.state.save()
				elif time <= hour_from_now:
					self.send_message(config.bot.timer_channel, '%s until %s' % (readable_rel(time - now), name))
					wakeups.append(time)
				else:
					wakeups.append(time - datetime.timedelta(hours=1))
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

				victim_name = victim['character']['name']
				ship = victim['shipType']['name']
				cost = data['package']['zkb']['totalValue'] / 1000000
				url = 'https://zkillboard.com/kill/%d/' % killmail['killID']
				self.send_message(config.bot.zkillboard['channel'],
						"%s's **%s** (%d mil) %s" % (victim_name, ship, cost, url))
				break
			else:
				print('zkill: %s %s\n%s' % (r.status_code, r.reason, r.text[:1000]), file=sys.stderr)
				time.sleep(30)

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
	def __init__(self, channel_id, sender, args, bot):
		self.channel_id = channel_id
		# sender = {
		#     'username': 'raylu',
		#     'id': '109405765848088576',
		#     'discriminator': '8396',
		#     'avatar': '464d73d2ca17733636282ab58b8cc3f5',
		# }
		self.sender = sender
		self.args = args
		self.bot = bot

	def reply(self, message, embed=None):
		self.bot.send_message(self.channel_id, message, embed)

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
