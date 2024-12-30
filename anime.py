import json
import re
import sys
import os
from threading import Thread, Timer

# Gloabl variables
list = None
configEdit = True

def loadConfig():
    global list
    print("Reloading config")
    list = json.load(open('configs/anime.json'))
    print("Reloadinf config succesfully")

def saveJsonFile(dict):
    global configEdit
    if configEdit:
        print("config saved")
        configEdit = False
        with open("configs/anime.json", 'w') as json_file:
            json.dump(dict, json_file, 
                            indent=4,  
                            separators=(',',': '))
        configEdit = True
    else:
        print("coudn´t save config")

def builDirs():
    print("Building directories")
    for z in list:
        for key, value in z.items():
            if key == "charakters-subfolder":
                continue
            if not os.path.isdir(key):
                os.mkdir(key)
        for a in z['anime']:
            aa = a['path']
            if not os.path.isdir(key + "/" + aa):
                os.mkdir(key + "/" + aa)
            for b in a['charakters']:
                bb = b['path']
                if not os.path.isdir(key + "/" + aa + "/" + bb):
                    os.mkdir(key + "/" + aa + "/" + bb)
                for c in z['charakters-subfolder']:
                    if not os.path.isdir(key + "/" + aa + "/" + bb + "/" + c):
                        os.mkdir(key + "/" + aa + "/" + bb + "/" + c)
    print("Succesfully builded directories")
    
def addAnime(name, path):
    for a in list:
        for key, value in a.items():
            if key == "anime":
                value.append({"name": name, "path": path, "charakters": []})
                
def isalias(list, alias):
    for a in list:
        if a.lower() == alias.lower():
            return True
    return False
                
def addCharakter(anime, name, path):
    for a in list:
        for key, value in a.items():
            if key == "anime":
                for b in value:
                    if b['name'].lower() == anime.lower() or b['path'].lower() == anime.lower() or isalias(b['alias'], anime):
                        b['charakters'].append({"name": name, "path": path})
                        
def addFile():
    pass
    
loadConfig()
configTimer = Timer(300.0, saveJsonFile(list))
configTimer.start()
            
while True:
    inputI = input()
    reloadpattern = re.compile("reload*")
    if inputI == "stop" or inputI == "exit":
        configTimer.cancel()
        sys.exit(1)
    elif reloadpattern.match(inputI):
        if len(inputI.split(" ")) >= 1:
            inputII = inputI.split(" ")[1]
        else:
            print("What do you want to reload?")
            print("-> [dirs | config]")
            inputII = input("I wanr to reload: ")
        if inputII == "dirs":
            Thread(target=builDirs()).start()
        elif inputII == "config":
            Thread(target=loadConfig()).start()
        else: 
            print("exited reload context")
    elif inputI == "help":
        print("stop | exit - stop the program")
        print("reload - open the reload context")
    elif inputI == "add anime":
        name = input("Name: ")
        path = input("Path: ")
        Thread(target=addAnime(name=name, path=path)).start()
    elif inputI == "add char":
        anime = input("Anime: ")
        name = input("Name: ")
        path = input("Path: ")
        if input("save char?[y/n]: ") == "y":
            Thread(target=addCharakter(anime=anime, name=name, path=path)).start()
        else:
            print("Creating char canceled")
    elif inputI == "save config":
        Thread(target=saveJsonFile(list)).start()
    else:
        print("unknown command, use \"help\"")
