import queue
import struct
import asyncio
import dill
import json, os

import settings as s
import services as sr

CREATE, UPDATE, FS, FILE, REPLICATEFILE, GIVEFILE, NEWFOLDER, RENAME, QUIT, ERROR, SUCCESS, CONN, INVALID = range(13)

class CommandObject(object):
    '''A command object to pass. It ensures security'''

    def __init__(self, command, data=None):
        self.command = command
        self.data = data

class Connection():
    '''
    Description: Handle every client.
    '''
    def __init__(self, reader, writer):
        self.reader = reader
        self.writer = writer
        self.msg_q = asyncio.Queue()
        self.write_q = asyncio.Queue()
        self.readTask = asyncio.create_task(self.read())
        self.handleTask = asyncio.create_task(self.handle())
        self.writeTask = asyncio.create_task(self.write())

    async def sendFs(self):
        await self.write_q.put(CommandObject(FS))

    async def read(self):
        '''
        Description: Reads from the reader object,
        decodes the message and saves to queue.
        '''
        while True:
            try:
                header = await self.reader.readexactly(4)
                length = struct.unpack('!I', header)[0]

                data = await self.reader.readexactly(length)
                message = dill.loads(data)
                #print('received {}'.format(message.command))
                await self.msg_q.put(message)
            except (asyncio.CancelledError, asyncio.IncompleteReadError, asyncio.TimeoutError, ConnectionResetError) as e:
                await self.endConnection()
                break

    async def write(self):
        '''
        Description: Writes to the reader object after
        picking up from the queue
        '''
        while True:
            try:
                command = await self.write_q.get()
                data = dill.dumps(command)
                header = struct.pack('!I', len(data))
                self.writer.write(header + data)
            except asyncio.CancelledError as e:
                print(e)
                break
            except Exception as e:
                print(e)
                break


    async def handle(self):
        '''
        Description: Picks each command up. Handles the command
        saves the result either error or success in the message queue
        '''
        while True:
            command = await self.msg_q.get()

            if command.command == CREATE:
                '''
                CREATE COMMAND:
                File will be saved on the current node. Node to replicate on
                will be figured out from the node which has the least number of
                files saved. The node replication is the majority of the
                participating servers.
                '''
                data = command.data
                name = list(command.data.keys())[0]
                #find node to save on
                #check if file exists already or not.
                #if exists create a new name for it
                new_name = sr.checkName(name)

                node = sr.NodeToSaveOn()
                if not node == None:
                    data[name]['Node'] = node
                    data[name]['Path'] = 'files/{}'.format(name)
                    data[name]['Version'] = 0
                    #find node to replicate on
                    nodesForReplication = sr.replicate(node)

                    #if some node found
                    if not nodesForReplication == None:
                        #save the Also of the data
                        data[name]['Also'] = nodesForReplication

                    #update the FS
                    s.FILES[new_name] = [data[name]]
                    #send an update to all servers
                    for name, connection in s.CONNECTIONS.items():
                        if name in s.SERVERS.keys():
                            await connection.write_q.put(CommandObject(FS, s.FILES))

                    #make an update in the local file
                    await self.updateFileFile()
                    #send an update to client
                    await self.write_q.put(CommandObject(FS, s.FILES))
                print('message processed')

            if command.command == UPDATE:
                '''
                UPDATE COMMAND:
                Updates the FS with the correct versioning and addes a new
                script to the Fs.
                '''
                name = command.data
                #update in list
                if name in s.FILES.keys():
                    #grab the last entry:
                    fileInfo = s.FILES[name][-1]
                    #add the new entry
                    newEntry = {'Type':'F',
                                'Parent':fileInfo['Parent'],
                                'Version': len(s.FILES[name]),
                                'Node':fileInfo['Node'],
                                'Also':fileInfo['Also'], 'Path': 'files/{}{}'.format(len(s.FILES[name]), name)}

                    s.FILES[name].append(newEntry)

                #make an update in the local file
                await self.updateFileFile()

                #send an update to all servers
                for name, connection in s.CONNECTIONS.items():
                    if name in s.SERVERS.keys():
                        await connection.write_q.put(CommandObject(FS, s.FILES))

                #send an update to client
                await self.write_q.put(CommandObject(FS, s.FILES))

                print('message processed')

            if command.command == FS:
                '''
                FS COMMAND:
                A command to send or receive nodes to replicate on.
                If FS command with no data : FS requested.
                If FS command with data : FS sent by a server
                Update FS if sent.
                '''
                if command.data == None:
                    #reply with FS
                    await self.write_q.put(CommandObject(FS, s.FILES))
                else:
                    if not sr.updateFs(command.data):
                        print('error in updating FS')
                        await self.write_q.put(CommandObject(ERROR))
                    else:
                        #update FS
                        await self.updateFileFile()

                print('message processed')

            if command.command == NEWFOLDER:
                '''
                NEWFOLDER COMMAND:
                A new folder was created in the client and an update was sent
                to the server. Since this is just symbollic, so it is arbitary.
                It is just a change in the FS
                '''
                data = command.data
                name = list(command.data.keys())[0]
                name = sr.checkName(name)
                #update Fs
                s.FILES[name] = [data[name]]

                #send an update to all servers
                for name, connection in s.CONNECTIONS.items():
                    if name in s.SERVERS.keys():
                        await connection.write_q.put(CommandObject(FS, s.FILES))

                #update Fs File
                await self.updateFileFile()

                #send an update to client
                await self.write_q.put(CommandObject(FS, s.FILES))
                print('message processed')

            if command.command == RENAME:
                '''
                RENAME COMMAND:
                A file was renamed. Folders cannot be renamed.
                Search for the old name and replace with new name in the fs
                Update the fs.
                '''
                #a new file is being sent
                oldName = command.data['old']
                newName = command.data['new']
                #if successful
                if sr.rename(oldName, newName):
                    #send an update to all servers
                    for name, connection in s.CONNECTIONS.items():
                        if name in s.SERVERS.keys():
                            await connection.write_q.put(CommandObject(FS, s.FILES))
                    #update fs file
                    await self.updateFileFile()

                    #send an update to client
                    await self.write_q.put(CommandObject(FS, s.FILES))

                print('message processed')

            if command.command == FILE:
                '''
                FILE COMMAND:
                A file is being sent. The file can be a new file or an updated
                file. For both cases, we find the primary node where it is
                saved on. If the primary node is the current node, then the
                file is saved in the files folder on the current server. Else
                the file is sent to the primary node. Once saved on the primary
                node, the lazy appraoch is used and the file is copied to the
                'Also' of file node with the replicate file command.
                '''
                #check if current server has to store it
                data = command.data
                name = list(command.data.keys())[0]
                nodes = sr.findFile(name)

                #if current server is the primary server
                if nodes[0] == '{}/{}'.format(s.HOST,s.PORT):
                    #save files in files folder
                    #check if file exists
                    try:
                        #get path
                        path = s.FILES[name][-1]['Path']
                        with open(path, 'w+') as f:
                            f.write(command.data[name])
                    except (IOError, OSError) as e:
                        print(e)
                else:
                    #else send it to the primary server
                    #check if the node is connected
                    if nodes[0] in s.CONNECTIONS.keys():
                        s.CONNECTIONS[nodes[0]].write_q.put(CommandObject(FILE, command.data))
                    else:
                        #primary server is not connected
                        #make primary server the current server
                        s.FILES[name][-1]['Node'] = '{}/{}'.format(s.HOST,s.PORT)
                        try:
                            #get path
                            path = s.FILES[name][-1]['Path']
                            with open(path, 'w+') as f:
                                f.write(command.data[name])
                        except (IOError, OSError) as e:
                            print(e)
                #send file to other servers
                #lazy approach. Send file after sending success response
                for i in range(1,len(nodes)):
                    if nodes[i] in s.CONNECTIONS.keys():
                        await s.CONNECTIONS[nodes[1]].write_q.put(CommandObject(REPLICATEFILE, command.data))

                print('message processed')

            if command.command == REPLICATEFILE:
                '''
                REPLICATEFILE COMMAND:
                Using the lazy appraoch, the primary node is sending a copy of
                the file to the secondary node. The secondary will also save
                the file in its 'files' folder.
                This is a server only command
                '''
                #file has come to be replicated
                data = command.data
                name = list(command.data.keys())[0]
                path = s.FILES[name][-1]['Path']
                try:
                    with open(path, 'w+') as f:
                        f.write(command.data[name])
                        await self.write_q.put(CommandObject(SUCCESS))
                except (IOError, OSError) as e:
                    print(e)
                    await self.write_q.put(CommandObject(ERROR))

            if command.command == GIVEFILE:
                '''
                GIVEFILE COMMAND:
                Either the client is asking the server for a file, or a
                different server is asking for a file not on their node. The
                current node will check if the file is saved on this node. If
                found, the file is sent else a conn command is sent in
                response.
                '''
                nodes = sr.findFile(command.data)
                if nodes == False:
                    #file does not exist
                    await self.write_q.put(CommandObject(ERROR))
                #else file is on the current server
                elif nodes[0] == '{}/{}'.format(s.HOST,s.PORT):
                    #get file
                    path = s.FILES[command.data][-1]['Path']
                    #check path
                    if os.path.isfile(path):
                        with open(path, 'r') as f:
                            data = f.read()
                            #send file contents to server
                            await self.write_q.put(CommandObject(FILE, data))
                #file is not on the current server
                else:
                    #send conn request to the client to connect with the
                    #other server
                    for node in nodes:
                        if node in s.CONNECTIONS.keys():
                            IP, PORT = nodes[0].split('/')
                            await self.write_q.put(CommandObject(CONN, {'IP': IP, 'PORT':PORT}))
                            break
                print('message processed')

            if command.command == QUIT:
                '''
                QUIT COMMAND:
                Quit command sent by a server or client. The server runs the
                end connection callback
                '''
                await self.endConnection()
                print('message processed')

            if command.command == ERROR:
                '''
                ERROR COMMAND:
                Server can't do much.
                '''
                print('message processed')

            if command.command in [SUCCESS, INVALID]:
                '''
                SUCCESS COMMAND:
                Server doesnt have to do anything
                '''
                print('message processed')

            self.msg_q.task_done()

    async def updateFileFile(self):
        '''
        Description:Picks up a file update
        Saves it to files.txt
        '''
        #open file in write more and flush out everything
        with open(s.FILES_FILE, 'w+') as f:
            json.dump(s.FILES, f, indent=4)

    async def endConnection(self):
        '''
        Description:Finds all pending tasks, waits for all tasks to be
        finished. Once done, writer is close. connection finished.
        '''
        # Find all running tasks:
        try:
            pending = asyncio.Task.all_tasks()
            # Run loop until tasks done:
            asyncio.gather(*pending)
        finally:
            self.writer.transport.close()
            #print('Connection Ended')
            return


