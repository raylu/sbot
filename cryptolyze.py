from __future__ import annotations

import typing

if typing.TYPE_CHECKING:
	from cryptolyzer.tls.versions import AnalyzerResultVersions
	from cryptolyzer.tls.vulnerabilities import AnalyzerResultVulnerabilities

	from bot import CommandEvent

def cryptolyze(cmd: CommandEvent) -> None:
	if not cmd.args:
		return
	try:
		versions_result, vulns_result = analyze(cmd.args)
	except Exception as e:
		cmd.reply(f'{cmd.sender['pretty_name']}: {e}')
	else:
		vulns = []
		for category in vulns_result.ciphers, vulns_result.dhparams, vulns_result.versions:
			for vuln in (getattr(category, a.name) for a in category.__attrs_attrs__): # pyright: ignore[reportAttributeAccessIssue]
				if vuln is not None and vuln.value:
					vulns.append(vuln.get_name())
		embed = {
			'title': versions_result.target.address,
			'description': versions_result.target.ip,
			'fields': [
				{'name': 'versions', 'value': ' '.join(map(str, versions_result.versions)), 'inline': True},
				{'name': 'vulnerabilities', 'value': '\n'.join(vulns) or 'none!', 'inline': True},
			],
		}
		cmd.reply('', embed=embed)

def analyze(host: str) -> tuple[AnalyzerResultVersions, AnalyzerResultVulnerabilities]:
	from cryptolyzer.common.utils import LogSingleton
	from cryptolyzer.tls.client import L7ClientTls
	from cryptolyzer.tls.versions import AnalyzerVersions
	from cryptolyzer.tls.vulnerabilities import AnalyzerVulnerabilities

	LogSingleton.log = lambda *args, **kwargs: None

	client = L7ClientTls(host, 443) # pyright: ignore[reportCallIssue]
	versions_result = AnalyzerVersions().analyze(client, None)
	vulns_result = AnalyzerVulnerabilities().analyze(client, None)
	return versions_result, vulns_result
