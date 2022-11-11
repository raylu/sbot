import dataclasses
import itertools
import re
import typing
import urllib.parse

import requests

if typing.TYPE_CHECKING:
	import bot

@dataclasses.dataclass
class SBDS:
	translations: dict = None
	spells: dict = None
	buffs: dict = None

	def matches_key(self, query: str, key: str):
		translations: dict[str, dict[str, str]] = self.translations['translations']
		try:
			translated = translations[key]
		except KeyError:
			if query == key.casefold():
				return 'en'
		else:
			for lang, translation in translated.items():
				if query == translation.casefold():
					return lang

	def translate(self, key: str, lang: str):
		try:
			translated: dict[str, str] = self.translations['translations'][key]
		except KeyError:
			return key
		else:
			return translated[lang]

	def translate_all(self, s: str, lang: str):
		def ttl(m: re.Match):
			return str(self.translate(m.group(0), lang))
		return re.sub(r'\b[A-Z_]+\b', ttl, s)

def sbds(cmd: 'bot.CommandEvent'):
	if not cmd.args:
		return
	name = cmd.args
	embed = get_embed(cmd.args)
	if embed is None:
		cmd.reply(f'couldn\'t find "{name}"')
	else:
		cmd.reply('', embed)

def get_embed(name: str) -> dict:
	data = _get_data()
	name = name.casefold()
	for spell_id, spell in itertools.chain(data.spells['SPELL'].items(), data.spells['EVOLVED'].items()):
		if spell['spellName'] is None:
			continue
		if lang := data.matches_key(name, spell['spellName']):
			translatedName = data.translate(spell['spellName'], lang)
			return {
				'title': translatedName,
				'description': data.translate(spell['levelUpDescriptions'][0], lang),
				'thumbnail': {'url': f'https://sbds.fly.dev/static/data/spells/{spell_id}.png'},
				'url': 'https://sbds.fly.dev/spells?' + urllib.parse.urlencode(
					{'q': translatedName, 'lang': lang}),
			}
	for aura_pair in data.spells['AURA']:
		for aura in aura_pair:
			if lang := data.matches_key(name, aura['titleText']):
				translatedName = data.translate(aura['titleText'], lang)
				return {
					'title': translatedName,
					'description': data.translate_all(aura['description'], lang),
					'thumbnail': {'url': f'https://sbds.fly.dev/static/data/spells/{aura["titleText"]}.png'},
					'url': 'https://sbds.fly.dev/spells?' + urllib.parse.urlencode(
						{'q': translatedName, 'lang': lang}),
				}
	for player_buff, enemy_buff in data.buffs:
		for buff in (player_buff, enemy_buff):
			if not buff:
				continue
			if lang := data.matches_key(name, buff['shrineText']):
				translated = data.translate(buff['shrineText'], lang)
				embed = {
					'title': translated,
					'thumbnail': {'url': f'https://sbds.fly.dev/static/data/buffs/{player_buff["shrineText"]}.png'},
					'url': 'https://sbds.fly.dev/buffs?' + urllib.parse.urlencode(
						{'q': translated, 'lang': lang}),
				}
				if 'notificationText' in buff:
					embed['description'] = data.translate(buff['notificationText'], lang)
				return embed

_cache = None
def _get_data():
	global _cache
	if _cache is not None:
		return _cache

	data = SBDS()
	rs = requests.Session()
	for filename in SBDS.__dataclass_fields__: # pylint: disable=no-member
		r = rs.get(f'https://sbds.fly.dev/static/data/{filename}.json', timeout=5)
		r.raise_for_status()
		setattr(data, filename, r.json())
	_cache = data
	return data
