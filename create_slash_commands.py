#!/usr/bin/env python3

import requests

from commands import commands
import config

def main():
	rs = requests.Session()
	rs.headers['Authorization'] = 'Bot ' + config.bot.token
	rs.headers['User-Agent'] = 'DiscordBot (https://github.com/raylu/sbot 0.0)'

	url = 'https://discord.com/api/v8/applications/%s/commands' % config.bot.app_id
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
