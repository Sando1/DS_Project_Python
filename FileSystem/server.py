import socket
import os, signal
import json
import sys
import asyncio
import functools

import settings as s
import connection


async def client_connected(reader, writer, fs=False):
    '''
    Description: Accepts any connections that comes.
    Makes a connection instance that takes care of the reading and writing
    Also, if fs = true, sends an FS request to the client.
    '''
    addr = writer.get_extra_info('peername')
    print('connected with {} at {}'.format(addr[0],addr[1]))

    adr = '{}/{}'.format(addr[0],addr[1])
    s.CONNECTIONS[adr] = connection.Connection(reader, writer)

    if fs == True:
        #send for Fs
        await s.CONNECTIONS[adr].sendFs()

def loadFs():
    '''
    Description: Tries to pick up the file structure on boot.
    If none present, an empty dict is sent.
    '''
    try:
        if os.stat(s.FILES_FILE).st_size > 0:
            f2 = open(s.FILES_FILE ,'r+')
            files = json.load(f2)
            f2.close()
            return files
    except OSError as e:
        #error in open
        print(e)
        f2 = open(s.FILES_FILE,'a+')
        f2.close()
    except (IOError,ValueError) as e:
        #flush everything from the file and start from 0
        print(e)
        f2 = open(s.FILES_FILE, 'w+')
        f2.close()
    return {"files": [{ "Type": "Root"}]}

def boot():
    '''
    Description: Runs all the management commands of
    the file server on boot
    '''
    try:
        if os.stat(s.CONFIG_FILE).st_size > 0:
            f = open(s.CONFIG_FILE,'r+')

            #exists, open and read file
            data = json.load(f)

            #check host, port, files, root
            host = data['host'] if 'host' in data.keys() else ''
            port = data['port'] if 'port' in data.keys() else ''
            servers = data['servers'] if 'servers' in data.keys() else {}
            root = data['root'] if 'root' in data.keys() else ''
            #make files folder
            if not os.path.isdir(root):
                os.mkdir(root)
            f.close()

            return (host, port, servers, root)
    except OSError as e:
        #error in open
        print(e)
        print('Boot Error: {}'.format(e))
        f = open(s.CONFIG_FILE,'a+')
        f.close()

    except (IOError,ValueError) as e:
        #flush everything from the file and start from 0
        print(e)
        print('Boot Error: {}'.format(e))
        f = open(s.CONFIG_FILE, 'w+')
        f.close()

    return (None, None, {}, None)


async def send_connect():
    '''
    Description: Tries to connect with all the servers already in the config
    file. Keeps on retrying until all connections have been connected.
    then breaks out of the loop.
    '''
    done = False
    while not done:
        await asyncio.sleep(5)
        for connection, addr  in s.SERVERS.items():
            if connection == '{}/{}'.format(s.HOST,s.PORT) or addr['connected'] == True:
                continue
            elif addr['connected'] == False:
                try:
                    reader, writer = await asyncio.open_connection(addr['ip'] , int(addr['port']))
                    addr['connected'] = True
                    done = True
                    await client_connected(reader, writer, fs=True)
                except Exception as e:
                    #print('Error in {} {}: {}'.format(addr['ip'] , addr['port'], e))
                    done = False

async def server():
    '''
    Description: Makes the server. Starts the server.
    Waits for incoming connections.
    '''
    try:
        server = await asyncio.start_server(client_connected, s.HOST, s.PORT)
        print('Server Starting on {} {} '.format(s.HOST, s.PORT))
        s.SERVERS['{}/{}'.format(s.HOST,s.PORT)]['connected'] = True
        async with server:
            await server.serve_forever()
    except asyncio.CancelledError:
        print('Closing Server ')
    except Exception as e:
        print('Server Error :{}'.format(e))
    return


async def main():
    #initialise globals
    s.init()
    #try and boot
    s.HOST, s.PORT, s.SERVERS, s.ROOT = boot()
    #add conn field to servers
    for connection, addr  in s.SERVERS.items():
        addr['connected'] = False

    s.FILES = loadFs()

    #if there was an error, exit
    if None in [s.HOST,s.PORT]:
        print('Error in Boot. Reconfigure')
        sys.exit(0)

    #do the connections
    await asyncio.gather(
        send_connect(),
        server(),
    )
    return

try:
    asyncio.run(main())
except KeyboardInterrupt:
    print('Closing')
