import dataclasses
import itertools
import typing

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
			if query in key.casefold():
				return 'en'
		else:
			for lang, translation in translated.items():
				if query in translation.casefold():
					return lang

	def translate(self, key: str, lang: str):
		try:
			translated: dict[str, str] = self.translations['translations'][key]
		except KeyError:
			return key
		else:
			return translated[lang]

def sbds(cmd: 'bot.CommandEvent'):
	if not cmd.args:
		return
	query = cmd.args.casefold()

	data = _get_data()
	for spell_id, spell in itertools.chain(data.spells['SPELL'].items(), data.spells['EVOLVED'].items()):
		if spell['spellName'] is None:
			continue
		if lang := data.matches_key(query, spell['spellName']):
			cmd.reply('', {
				'title': data.translate(spell['spellName'], lang),
				'description': data.translate(spell['levelUpDescriptions'][0], lang),
				'thumbnail': {'url': f'https://sbds.fly.dev/static/data/spells/{spell_id}.png'}
			})
			return

	cmd.reply(f'couldn\'t find "{query}"')

_cache = None
def _get_data():
	global _cache
	if _cache is not None:
		return _cache

	data = SBDS()
	rs = requests.Session()
	for filename in SBDS.__dataclass_fields__:
		r = rs.get(f'https://sbds.fly.dev/static/data/{filename}.json', timeout=5)
		r.raise_for_status()
		setattr(data, filename, r.json())
	_cache = data
	return data
