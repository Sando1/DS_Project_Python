# Save
import json
import os
import pprint
from functools import reduce
from collections import defaultdict, Counter
import random

dictionary = {}

host = 'localhost'
port = 30002
connections = {'127.0.0.1/30000' : {'ip':'127.0.0.1','port':30000}, '127.0.0.1/30001' : {'ip':'127.0.0.1','port':30001}}
file_servers = {'127.0.0.1/30000' : {'ip':'127.0.0.1','port':30000}, '127.0.0.1/30001' : {'ip':'127.0.0.1','port':30001}, '127.0.0.1/30002' : {'ip':'127.0.0.1','port':30002}}
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


#thing = BASE_PATH+'/config3.txt'
#dictionary = {'host' : host, 'port' : port, 'servers': file_servers, 'root': 'files/', 'connections':connections}

#with open(thing, 'w') as fp:
#   json.dump(dictionary, fp, indent=4)

#with open(BASE_PATH+'/files.txt', 'w') as f:
#   json.dump(filess, f, indent=4)

thing = { 'host': "127.0.0.1", 'port': 30000,'root': "temp/"}

with open(BASE_PATH+'/clientconfig.txt', 'w') as f:
    json.dump(thing, f, indent=4)

#print(data)
#figure out which node to save file on
#saving in whichever has the lowest data
#print(data)
'''
counts = Counter()
for items, des in data.items():
    if 'Node' in des[-1].keys():
        counts[des[-1]['Node']] += 1
    if 'Also' in des[-1].keys():
        if len(des[-1]['Also']) > 0:
            counts[des[-1]['Also'][-1]] += 1

print(counts)
#find how many nodes to replicate on
#int to get a whole number.
#wont add the plus 1 because already saved on one server which is
#the primary
number = int(len(counts)/2)
nodes = []
counts = counts.most_common()
if len(counts) == 1:
    for i in range(3):
        print(counts[0][0])

if len(counts) == 2:
    nodes.append(counts[-2])
    print(nodes)

if len(counts) > number:
    for i in range(2,number):
        nodes.append(counts[int('-'+2)])
    print(nodes)
'''
