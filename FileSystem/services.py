import settings as s
from collections import Counter

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
    #file is present and we are not doing this to a directory
    if name in s.FILES.keys() and s.FILES[name][-1]['Type'] != 'D':
        return [s.FILES[name][-1]['Node'] , s.FILES[name][-1]['Also']]
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
            counts[des[-1]['Also'][-1]] += 1

        #sort
        counts = counts.most_common()
        return counts[-1][0]

    return None

def replicate():
    '''
    Description: Replication function that runs on file creation.
    Assumption: Majority of the servers should have replication.
    '''
    #count the number of servers we have
    files = s.FILES
    counts = Counter()
    for items, des in s.FILES.items():
        if 'Node' in des[-1].keys():
            counts[des[-1]['Node']] += 1
            counts[des[-1]['Also'][-1]] += 1

    #find how many nodes to replicate on
    #int t get a whole number.
    #wont add the plus 1 because already saved on one server which is
    #the primary
    number = int(len(counts)/2)
    nodes = []

    for i in range(number):
        nodes.append(counts[int('-'+i)][0])

    return nodes

