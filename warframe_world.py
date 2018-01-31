from urllib.request import urlopen
import json
import sys
import re

helmetName = "No"

def worldStatePull(url):
	worldStateFile = urlopen(url)
	worldStateJson = worldStateFile.read().decode("utf-8")
	return json.loads(worldStateJson)
	
def alertAnalysis():
	url = "http://content.warframe.com/dynamic/worldState.php"
	global helmetName
	orokinAvailable = False
	helmetAvailable = False
	nitainAvailable = False
	warframeState = worldStatePull(url)
	
	for mission in warframeState["Alerts"]:
		reward = mission["MissionInfo"]["missionReward"]
		
		if "items" in reward:
			if orokinSearch(reward["items"]):
				orokinAvailable = True
			if helmSearch(reward["items"]):
				helmetAvailable = True
		elif "countedItems" in reward:
			if nitainSearch(reward["countedItems"]):
				nitainAvailable = True
	
	postString = ""
	if orokinAvailable:
		postString = postString + "Orokin catalysts or reactors are available. "
	if helmetAvailable:
		postString = postString + helmetName, "helmet is available. "
	if nitainAvailable:
		postString = postString + "REEEEEEE Nitain is available. "
		
	postString = postString + "Credits are always available."
	
	print(postString)
	
	return postString
		
def nitainSearch(rewardToCheck):

	if rewardToCheck[0]["ItemType"] == "/Lotus/Types/Items/MiscItems/Alertium":
		return True
	else:
		return False

def orokinSearch(rewardToCheck):
	if rewardToCheck == "/Lotus/StoreItems/Types/Recipes/Components/OrokinCatalystBlueprint":
		print("Catalyst")
		return true
	elif rewardToCheck == "/Lotus/StoreItems/Types/Recipes/Components/OrokinReactorBlueprint":
		print("Reactor")
		return True
	else:
		return False

def helmSearch(rewardToCheck):
	global helmetName 
	helmetFlag = rewardToCheck[0].find("Helmets")
	vaubanFlag = rewardToCheck[0].find("Trapper")
	
	if helmetFlag > 0 and vaubanFlag < 0:
		itemStringTable = rewardToCheck[0].split("/")
		if helmetName != "No":
			print("test")
			helmetName = "Multiple"
		else:
			helmetName = itemStringTable[-1]
			return True
	else:
		return False
		

alertAnalysis()