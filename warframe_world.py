from urllib.request import urlopen
import json

def world_state_pull(url):
	world_state_file = urlopen(url)
	world_state_json = world_state_file.read().decode("utf-8")
	return json.loads(world_state_json)

def alert_analysis():
	url = "http://content.warframe.com/dynamic/worldState.php"
	helmet_names = []
	orokin_available = False
	nitain_available = False
	warframe_state = world_state_pull(url)

	for mission in warframe_state["Alerts"]:
		reward = mission["MissionInfo"]["missionReward"]

		if "items" in reward:
			if orokin_search(reward["items"]):
				orokin_available = True
			helm = helm_search(reward['items'])
			if helm is not None:
				helmet_names.append(helm)
		elif "countedItems" in reward:
			if nitain_search(reward["countedItems"]):
				nitain_available = True

	post_parts = []
	if orokin_available:
		post_parts.append("Orokin catalysts or reactors are available.")

	if nitain_available:
		post_parts.append("REEEEEEE Nitain is available.")

	if len(helmet_names) > 0:
		post_parts.append(", ".join(helmet_names[:5]) + ' helmets are available.')

	post_parts.append("Credits are always available.")

	print("\n".join(post_parts))
	return "\n".join(post_parts)

def nitain_search(reward_check):

	return reward_check[0]["ItemType"] == "/Lotus/Types/Items/MiscItems/Alertium"

def orokin_search(reward_check):
	if reward_check == "/Lotus/StoreItems/Types/Recipes/Components/OrokinCatalystBlueprint":
		return True
	elif reward_check == "/Lotus/StoreItems/Types/Recipes/Components/OrokinReactorBlueprint":
		return True
	else:
		return False

def helm_search(reward_check):
	reward = reward_check[0]

	if 'Trapper' in reward:
		return None
	if 'Helmets' not in reward:
		return None
	item_string_table = reward.split('/')
	return item_string_table[-1]


alert_analysis()
