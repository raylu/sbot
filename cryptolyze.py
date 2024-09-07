from __future__ import annotations

import subprocess
import typing

if typing.TYPE_CHECKING:
	from bot import CommandEvent


def cryptolyze(cmd: CommandEvent) -> None:
	if not cmd.args:
		return
	base_cmd = ['cryptolyze', '--output-format', 'markdown', 'tls']
	try:
		versions = subprocess.run([*base_cmd, 'versions', cmd.args], check=True, capture_output=True, text=True)
		output_lines = versions.stdout.splitlines()

		vulns = subprocess.run([*base_cmd, 'vulns', cmd.args], check=True, capture_output=True, text=True)
		vuln_lines = vulns.stdout.splitlines()
		assert vuln_lines[0] == '* Target:'
		for start, line in enumerate(vuln_lines[1:], 1):
			if line.startswith('* '):
				break
		else:
			raise AssertionError("couldn't find second heading in vulns output")
		for line in vuln_lines[start:]:
			if line.endswith('yes'):
				line = line.removesuffix('yes') + '**yes**'
			output_lines.append(line)

		output = '\n'.join(line[2:] if line.startswith('    ') else line for line in output_lines)
		cmd.reply('', embed={'description': output})
	except subprocess.CalledProcessError as e:
		cmd.reply(f'{cmd.sender['pretty_name']}: {e.stderr}')
