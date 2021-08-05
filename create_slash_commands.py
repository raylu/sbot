#!/usr/bin/env python3

import argparse

import requests

from commands import commands
import config

def main():
	parser = argparse.ArgumentParser()
	parser.add_argument('--guild_id')
	parser.add_argument('--unregister', action='store_const', const=True, default=False)
	args = parser.parse_args()

	rs = requests.Session()
	rs.headers['Authorization'] = 'Bot ' + config.bot.token
	rs.headers['User-Agent'] = 'DiscordBot (https://github.com/raylu/sbot 0.0)'

	if args.guild_id is None:
		url = 'https://discord.com/api/v8/applications/%s/commands' % config.bot.app_id
	else:
		url = 'https://discord.com/api/v8/applications/%s/guilds/%s/commands' % (config.bot.app_id, args.guild_id)
	if args.unregister:
		for command in rs.get(url).json():
			print('deleting', command['name'])
			r = rs.delete('%s/%s' % (url, command['id']))
			r.raise_for_status()
	else:
		for name, handler in commands.items():
			description = getattr(handler, 'description', None)
			if description is None:
				continue
			r = rs.post(url, json={
				'name': name,
				'description': description,
				'options': handler.options,
			})
			print(r.content)
			r.raise_for_status()

if __name__ == '__main__':
	main()
