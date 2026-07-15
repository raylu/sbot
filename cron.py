from __future__ import annotations

import dataclasses
import datetime
import math
import time
import traceback
import typing

import requests

import advent_of_code
import config
import instagram
import log
import prun
import steam_news
import twitch
from bot import Bot

def main() -> None:
	jobs: typing.Sequence[CronJob] = []
	if config.bot.advent_of_code is not None and datetime.date.today().month in (12, 1):
		jobs.append(CronJob(12 * 60 * 60, advent_of_code.check_leaderboards))
	if config.bot.instagram is not None:
		# https://developers.facebook.com/docs/graph-api/overview/rate-limiting#platform-rate-limits
		# 240 * users / hour is 4× what we'll need
		jobs.append(CronJob(60, instagram.new_media))
	if config.bot.prun_upkeep is not None:
		jobs.append(CronJob(60 * 60, prun.planetary_upkeep))
	if config.bot.steam_news is not None:
		jobs.append(CronJob(60, steam_news.news))
	if config.bot.twitch is not None:
		# https://dev.twitch.tv/docs/api/guide#rate-limits
		# 30 points per minute, streams endpoint costs 1 point
		jobs.append(CronJob(15, twitch.live_streams))

	now = time.time()
	for job in jobs:
		job.last_run = now

	period = math.gcd(*(job.interval for job in jobs))
	bot = Bot({})

	while True:
		sleep_duration = now - time.time() + period
		if sleep_duration > 0:
			time.sleep(sleep_duration)

		now = time.time()
		for job in jobs:
			if now - job.last_run < job.interval:
				continue
			job.last_run = now
			try:
				job.task(bot)
			except requests.exceptions.HTTPError as e:
				log.write(f'{job.task.__name__}: {e}\n{e.response.text[:1000]}') # ty: ignore[unresolved-attribute]
			except requests.exceptions.RequestException as e:
				log.write(f'{job.task.__name__}: {e}')
			except Exception:
				log.write(f'{job.task.__name__}:\n{traceback.format_exc()}')

@dataclasses.dataclass(eq=False, slots=True)
class CronJob:
	interval: int
	task: typing.Callable[[Bot], None]
	last_run: float = -1

if __name__ == '__main__':
	main()
