import json
import os
import pprint
from functools import reduce
from collections import defaultdict, Counter
import random


dictionary = {}

host = '127.0.0.1'
port = 30002
#connections = {'127.0.0.1/30000' : {'ip':'127.0.0.1','port':30000}, '127.0.0.1/30002' : {'ip':'127.0.0.1','port':30002}}
file_servers = {
'127.0.0.1/30000' : {'ip':'127.0.0.1','port':30000, 'connected':False},
'127.0.0.1/30001' : {'ip':'127.0.0.1','port':30001,'connected':False},
'127.0.0.1/30002' : {'ip':'127.0.0.1','port':30002,'connected' : False}
}
filess = {}

thing = 'config3.txt'
print(thing)
dictionary = {'host' : host, 'port' : port, 'servers': file_servers, 'root': 'files'}

with open(thing, 'w') as fp:
   json.dump(dictionary, fp, indent=4)
