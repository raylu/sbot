#!/usr/bin/env python3

import sys

import requests

import config

def main():
	rs = requests.Session()
	rs.headers['Authorization'] = 'Bot ' + config.bot.token
	rs.headers['User-Agent'] = 'DiscordBot (https://github.com/raylu/sbot 0.0)'

	if len(sys.argv) == 2:
		guild_id = sys.argv[1]
		r = rs.delete('https://discord.com/api/v8/users/@me/guilds/' + guild_id)
		print(r.content)
	else:
		r = rs.get('https://discord.com/api/v8/users/@me/guilds?with_counts=true')
		r.raise_for_status()
		for guild in r.json():
			print(guild['id'], guild['name'], guild['approximate_member_count'])

if __name__ == '__main__':
	main()
