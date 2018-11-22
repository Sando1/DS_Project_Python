# Save
import json
import os
import pprint
from functools import reduce
from collections import defaultdict, Counter
import random

dictionary = {}

host = 'localhost'
port = 30000
connections = {'127.0.0.1/30001' : {'ip':'127.0.0.1','port':30001}, '127.0.0.1/30002' : {'ip':'127.0.0.1','port':30002}}
filess = {}

BASE_PATH = os.path.dirname(os.getcwd())

import os

nodes = ['127.0.0.0/30001','127.0.0.0/30000','127.0.0.0/30002']

def get_directory_structure(rootdir):
    """
    Creates a nested dictionary that represents the folder structure of rootdir
    """
    dir = {}
    for root, dirs, files in os.walk(rootdir):
        dirs[:] = [d for d in dirs if d not in ['__pycache__','.git','temp']]
        parent = root.split(os.sep)[-1]
        #print(parent)
        if not parent in dir:
            dir[parent] = [{'Type':'Root'}]

        for dire in dirs:
            print(dire + ': '+ parent)
            dir[dire] = [{'Type':'D', 'Parent':parent}]

        for file in files:
            print(file + ': '+ parent)
            dir[file] = [{'Type':'F', 'Parent':parent, 'Node': random.choice(nodes), 'Version':0, 'Also': [], 'Path': root}]

        #print(dir)
    return dir

#filess = get_directory_structure(BASE_PATH+'/files')

#pp = pprint.PrettyPrinter(indent=2)
#pp.pprint(filess)


thing = BASE_PATH+'/config.txt'
dictionary = {'host' : host, 'port' : port, 'connections':connections}

with open(thing, 'w') as fp:
   json.dump(dictionary, fp, indent=4)

#with open(BASE_PATH+'/files.txt', 'w') as f:
#    json.dump(filess, f, indent=4)

#with open(BASE_PATH+'/files.txt', 'r') as f:
#    data = json.load(f)

#figure out which node to save file on
#saving in whichever has the lowest data
#counts = Counter()
#for items, des in data.items():
#    if 'Node' in des[-1].keys():
#        counts[des[-1]['Node']] += 1
        #counts[des[-1]['Also'][-1]] += 1
#print(counts)
