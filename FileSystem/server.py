import socket
import os
import json
import sys
import asyncio
import errno

import settings as s
import connection

async def updateConfig():
    '''
    Description:Picks up an update from the config
    Saves it to file
    '''
    with open(s.CONFIG_FILE,'r') as f:
        data = json.load(f)
    #make the connection dict
    connections = {}
    for conn, des in s.CONNECTIONS.items():
        ip, port = conn.split('/')
        connections[conn] = {'ip':ip,'port':port}
    #append the thing to the main data
    data['connections'] = connections
    #open file again in write more and flush out everything
    with open(s.CONFIG_FILE, 'w+') as f:
        json.dump(data, f, indent=4)

async def client_connected(reader, writer):
    '''
    Description: Accepts any connections that comes.
    Makes a connection instance that takes care of the reading and writing
    '''

    addr = writer.get_extra_info('peername')
    print('connected with {} at {}'.format(addr[0],addr[1]))
    s.CONNECTIONS[addr[0] +'/'+str(addr[1])] = connection.Connection(reader, writer)
    #update config
    await asyncio.create_task(updateConfig())

def loadFs():
    '''
    Description: Tries to pick up the file structure on boot.
    If none present, an empty dict is sent.
    '''
    if not os.stat(s.FILES_FILE).st_size == 0:
        try:
            f2 = open(s.FILES_FILE ,'r+')
            files = json.load(f2)
            f2.close()
            return files
        except OSError as e:
            #error in open
            f2 = open(s.FILES_FILE,'a+')
            f2.close()
            return {"files": [{ "Type": "Root"}]}
        except (IOError,ValueError) as e:
            #flush everything from the file and start from 0
            f2 = open(s.FILES_FILE, 'w+')
            f2.close()
            return {"files": [{ "Type": "Root"}]}
        return {"files": [{ "Type": "Root"}]}

def boot():
    '''
    Description: Runs all the management commands of
    the file server on boot
    '''
    try:
        if not os.stat(s.CONFIG_FILE).st_size == 0:
            f = open(s.CONFIG_FILE,'r+')

            #exists, open and read file
            data = json.load(f)

            #check host, port, connections, files
            host = data['host'] if 'host' in data else ''
            port = data['port'] if 'port' in data else ''
            connections = data['connections'] if 'connections' in data else {}
            servers = data['servers'] if 'servers' in data else {}
            #make files folder
            if not os.path.isdir('files'):
                os.mkdir('files')
            f.close()
            return (connections, host, port, servers)
    except OSError as e:
        #error in open
        print('Boot Error: {}'.format(e))
        f = open(s.CONFIG_FILE,'a+')
        f.close()
        return ({}, '', 0, '')
    except (IOError,ValueError) as e:
        #flush everything from the file and start from 0
        print('Boot Error: {}'.format(e))
        f = open(s.CONFIG_FILE, 'w+')
        f.close()
        return ({},'', 0, '')

    return ({}, None, None, {})

async def main():
    #initialise globals
    s.init()

    #connections, files can be empty. shows starting from scratch
    #try and boot
    connections, s.HOST, s.PORT, s.SERVERS = boot()
    s.FILES = loadFs()
    if s.FILES == None:
        s.FILES = {"files": [{ "Type": "Root"}]}
    #if there was an error, exit
    if None in [s.HOST,s.PORT]:
        print('Error in Boot')
        sys.exit(0)

    #bind a socket
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.bind((s.HOST, s.PORT))
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        print("Socket successfully created")
    except socket.error as e:
        print("socket creation failed with error %s" %(e))
        sys.exit(0)

    #now try and connect from the connections already saved
    if len(connections) > 0:
        for connection, addr  in connections.items():
            try:
                sock.connect((addr['ip'] , int(addr['port'])))
                reader, writer = await asyncio.open_connection(sock=sock)
                await client_connected(reader, writer)
            except Exception as e:
                print('Error in {} {}: {}'.format(addr['ip'] , addr['port'], e))

    #make server.
    try:
        server = await asyncio.start_server(client_connected, sock=sock)
        print('Server Starting on {} {} '.format(s.HOST, s.PORT))
        async with server:
            await server.serve_forever()
    except asyncio.CancelledError:
        print('Closing Server: ')
        sock.close()
    except Exception as e:
        print('Server Error :{}'.format(e))

#root path
BASE_PATH = os.path.dirname(os.getcwd())

try:
    asyncio.run(main())
except KeyboardInterrupt:
    print('Closing')
