import settings as s
from collections import Counter
import random

def rename(old, new):
    '''
    Description: Updates the file structure with the
    new file name and returns true is succcessful
    '''
    if old in s.FILES.keys():
        data = s.FILES[old]
        del s.FILES[old]
        s.FILES[new] = data
        return True

    return False

def findFile(name):
    '''
    Description: Find file information.
    Returns None if File Not Found
    '''
    nodes = []
    #file is present and we are not doing this to a directory
    if name in s.FILES.keys() and s.FILES[name][-1]['Type'] != 'D':
        nodes.append(s.FILES[name][-1]['Node'])
        for also in s.FILES[name][-1]['Also']:
            nodes.append(also)
        return nodes
    else:
        return False

def updateFs(remoteFs):
    '''
    Description: Function to simply update the fs with the remoteFs
    if file already exists, a value is added in the version list.
    '''
    for file, des in remoteFs.items():
        #if file found in currFs and that value has different length than the remote Fs
        if file in s.FILES.keys() and len(s.FILES[file]) != len(remoteFs[file]):
            #for the difference
            for l in range(len(remoteFs[file]) - len(s.FILES[file]), 0, -1):
                try:
                    #pick that entry in the remoteFs
                    entryNo = '-{}'.format(l)
                    #update the fs
                    s.FILES[file].append(remoteFs[file][int(entryNo)])
                except Exception as e:
                    print('Error in updating FS: {}'.format(e))
                    return False
    return True

def NodeToSaveOn():
    '''
    Description: Finds the node to save a new file on creation.
    Assumes the one with the lesser number of files is the free one
    and hence that will be the node selected.
    '''
    #get file structure
    files = s.FILES
    #figure out which node to save file on
    #saving in whichever has the lowest data
    counts = Counter()
    for items, des in s.FILES.items():
        if 'Node' in des[-1].keys():
            counts[des[-1]['Node']] += 1
        if 'Also' in des[-1].keys():
            if len(des[-1]['Also']) > 0:
                counts[des[-1]['Also'][-1]] += 1

        if len(counts) < len(s.SERVERS):
            for server in s.SERVERS.keys():
                if server not in counts.keys():
                    return server
        #sort
        if len(counts) > 0:
            counts = counts.most_common()
            return counts[-1][0]

    return None

def replicate(nodeSaved):
    '''
    Description: Replication function that runs on file creation.
    Assumption: Majority of the servers should have replication.
    '''
    counts = Counter()
    for items, des in s.FILES.items():
        if 'Node' in des[-1].keys():
            counts[des[-1]['Node']] += 1
        if 'Also' in des[-1].keys():
            if len(des[-1]['Also']) > 0:
                counts[des[-1]['Also'][-1]] += 1

    #find how many nodes to replicate on
    #int to get a whole number.
    #wont add the plus 1 because already saved on one server which is
    #the primary
    number = int(len(s.SERVERS)/2)+1
    nodes = []
    counts = counts.most_common()
    servers = list(s.SERVERS.keys())
    if len(counts) == 0:
        for _ in range(number):
            i =  random.randint(0,len(servers)-1)
            if servers[i] != nodeSaved and servers[i] not in nodes:
                nodes.append(servers[i])
            else:
                if len(servers) > i+1:
                    nodes.append(servers[i+1])
                else:
                    nodes.append(servers[i-1])
        return nodes

    if len(counts) == 1:
        for i in range(number):
            if servers[i] == counts[0][0] or servers[i] == nodeSaved:
                pass
            else:
                nodes.append(servers[i])
        return nodes

    if len(counts) == 2:
        for server in servers:
            if server == nodeSaved:
                pass
            else:
                print(server)
                if server not in [counts[0][0],counts[1][0]]:
                    #print(servers[i])
                    nodes.append(server)
                    if len(nodes) == number - 1:
                        return nodes
        return nodes

    if len(counts) > number:
        for i in range(2,(2+number)):
            nodes.append(counts[int('-'+str(i))][0])
        return nodes

    return nodes

def checkName(name):
    if name not in s.FILES.keys():
        return name
    else:
        i = 1
        temp = name.rsplit('.',1)
        name = '{}({}).{}'.format(temp[0],i,temp[1])
        while name in s.FILES.keys():
            i += 1
            name = '{}({}).{}'.format(temp[0],i,temp[1])

    return name
