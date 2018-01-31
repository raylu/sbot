from urllib.request import urlopen
import json
import sys
import re

helmet_name = "No"

def world_state_pull(url):
	world_state_file = urlopen(url)
	world_state_json = world_state_file.read().decode("utf-8")
	return json.loads(world_state_json)
	
def alert_analysis():
	url = "http://content.warframe.com/dynamic/worldState.php"
	global helmet_name
	orokin_available = False
	helmet_available = False
	nitain_available = False
	warframe_state = world_state_pull(url)
	
	for mission in warframe_state["Alerts"]:
		reward = mission["MissionInfo"]["missionReward"]
		
		if "items" in reward:
			if orokin_search(reward["items"]):
				orokin_available = True
			if helm_search(reward["items"]):
				helmet_available = True
		elif "countedItems" in reward:
			if nitain_search(reward["countedItems"]):
				nitain_available = True
	
	post_string = ""
	if orokin_available:
		post_string = post_string + "Orokin catalysts or reactors are available. "
	if helmet_available:
		post_string = post_string + helmet_name, "helmet is available. "
	if nitain_available:
		post_string = post_string + "REEEEEEE Nitain is available. "
		
	post_string = post_string + "Credits are always available."
	
	print(post_string)
	
	return post_string
		
def nitain_search(reward_check):

	if reward_check[0]["ItemType"] == "/Lotus/Types/Items/MiscItems/Alertium":
		return True
	else:
		return False

def orokin_search(reward_check):
	if reward_check == "/Lotus/StoreItems/Types/Recipes/Components/OrokinCatalystBlueprint":
		print("Catalyst")
		return true
	elif reward_check == "/Lotus/StoreItems/Types/Recipes/Components/OrokinReactorBlueprint":
		print("Reactor")
		return True
	else:
		return False

def helm_search(reward_check):
	global helmet_name 
	helmet_flag = reward_check[0].find("Helmets")
	vauban_flag = reward_check[0].find("Trapper")
	
	if helmet_flag > 0 and vauban_flag < 0:
		item_string_table = reward_check[0].split("/")
		if helmet_name != "No":
			print("test")
			helmet_name = "Multiple"
		else:
			helmet_name = item_string_table[-1]
			return True
	else:
		return False
		

alert_analysis()