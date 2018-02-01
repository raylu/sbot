import requests

def alert_analysis():
	r = requests.get('http://content.warframe.com/dynamic/worldState.php')
	r.raise_for_status()
	warframe_state = r.json()

	helmet_names = []
	orokin_available = nitain_available = False
	for mission in warframe_state['Alerts']:
		reward = mission['MissionInfo']['missionReward']
		if 'items' in reward:
			if orokin_search(reward['items']):
				orokin_available = True
			helm = helm_search(reward['items'])
			if helm is not None:
				helmet_names.append(helm)
		elif 'countedItems' in reward:
			if nitain_search(reward['countedItems']):
				nitain_available = True

	post_parts = []
	if orokin_available:
		post_parts.append('orokin catalysts or reactors are available')
	if nitain_available:
		post_parts.append('nitain is available')
	if len(helmet_names) > 0:
		post_parts.append(', '.join(helmet_names[:5]) + ' helmets are available')
	return post_parts

def nitain_search(reward_check):
	return reward_check[0]['ItemType'] == '/Lotus/Types/Items/MiscItems/Alertium'

def orokin_search(reward_check):
	orokin = [
		'/Lotus/StoreItems/Types/Recipes/Components/OrokinCatalystBlueprint',
		'/Lotus/StoreItems/Types/Recipes/Components/OrokinReactorBlueprint',
	]
	return reward_check in orokin

def helm_search(reward_check):
	reward = reward_check[0]
	if 'Trapper' in reward:
		return None
	if 'Helmets' not in reward:
		return None
	item_string_table = reward.split('/')
	return item_string_table[-1]
