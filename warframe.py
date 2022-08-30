import requests

def alert_analysis():
	r = requests.get('http://content.warframe.com/dynamic/worldState.php', timeout=5.0)
	r.raise_for_status()
	warframe_state = r.json()

	orokin_available = False
	for mission in warframe_state['Alerts']:
		reward = mission['MissionInfo']['missionReward']
		if 'items' in reward:
			if orokin_search(reward['items']):
				orokin_available = True

	post_parts = []
	if orokin_available:
		post_parts.append('orokin catalysts or reactors are available')
	return post_parts

def orokin_search(reward_check):
	orokin = [
		'/Lotus/StoreItems/Types/Recipes/Components/OrokinCatalystBlueprint',
		'/Lotus/StoreItems/Types/Recipes/Components/OrokinReactorBlueprint',
	]
	return reward_check[0] in orokin
