import dataclasses
import os
import time
import typing

import yaml

@dataclasses.dataclass(eq=False, frozen=True, slots=True)
class BotConfig:
	app_id: str
	token: str
	err_channel: str | None
	roles: dict[str, str]
	autoreload: bool
	debug: bool
	eve_db: str | None
	acnh_db: str | None
	advent_of_code: list[dict] | None
	instagram: list[dict] | None
	prun_upkeep: dict[str, dict[str, typing.Any]] | None
	steam_news: dict | None
	twitch: dict | None

@dataclasses.dataclass(eq=False, slots=True)
class BotState:
	gateway_url: str | None = None
	timers: dict = dataclasses.field(default_factory=dict)
	flights: list = dataclasses.field(default_factory=list)

	def save(self):
		_save_yaml('bot_state.yaml', dataclasses.asdict(self))

@dataclasses.dataclass(eq=False, slots=True)
class CronState:
	advent_of_code_last_check: int = dataclasses.field(default_factory=lambda: int(time.time()))
	instagram: dict = dataclasses.field(default_factory=dict)
	prun_popi_next: dict[str, float] = dataclasses.field(default_factory=dict)
	steam_news_ids: dict = dataclasses.field(default_factory=dict)
	twitch_last_times: dict = dataclasses.field(default_factory=dict)

	def save(self):
		_save_yaml('cron_state.yaml', dataclasses.asdict(self))

def _save_yaml(filename: str, data: dict) -> None:
	temp_path = filename + '.tmp'
	with open(temp_path, 'w', encoding='utf-8') as f:
		yaml.dump(data, f)
	os.replace(temp_path, filename)

with open('config.yaml', 'r', encoding='utf-8') as f:
	bot = BotConfig(**yaml.safe_load(f))
try:
	with open('bot_state.yaml', 'r', encoding='utf-8') as f:
		state = BotState(**yaml.safe_load(f))
except FileNotFoundError:
	state = BotState()
try:
	with open('cron_state.yaml', 'r', encoding='utf-8') as f:
		cron_state = CronState(**yaml.safe_load(f))
except FileNotFoundError:
	cron_state = CronState()
