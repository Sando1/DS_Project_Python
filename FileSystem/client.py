import asyncio
import dill
import struct
import os, sys, json
import functools

from PyQt5 import QtCore, QtGui, QtWidgets
import gui as main

IP = 'localhost'
PORT = 30000
CREATE, UPDATE, FS, FILE, REPLICATEFILE, GIVEFILE, NEWFOLDER, RENAME, QUIT, ERROR, SUCCESS, CONN, INVALID = range(13)

class CommandObject(object):
    '''A command object to pass. It ensures security'''
    def __init__(self, command, data=None):
        self.command = command
        self.data = data

class Client():

    def __init__(self, ip, port):
        self.ip = ip
        self.port = port
        self.reader = None
        self.writer = None

    async def __aenter__(self):
        '''
        Description: Function to enter and connect with the server
        '''
        try:
            self.reader, self.writer = await asyncio.open_connection(self.ip, self.port)
        except Exception as e:
            print(e)
            sys.exit()

    async def send(self, data):
        '''
        Description: Function to send data to the server
        '''
        datatoSend = dill.dumps(data)
        header = struct.pack('!I', len(datatoSend))
        self.writer.write(header + datatoSend)

    async def receive(self):
        '''
        Description: Function to receive data from the server
        '''
        try:
            header = await self.reader.readexactly(4)
            length = struct.unpack('!I', header)[0]

            data = await self.reader.readexactly(length)
            message = dill.loads(data)
            return message
        except (asyncio.CancelledError, asyncio.IncompleteReadError, asyncio.TimeoutError, ConnectionResetError) as e:
            print(e)

    async def __aexit__(self, *args, **kwargs):
        '''
        Description: Loop to run upon closing the server
        '''
        self.writer.transport.close()
        #print('Exiting')


class Browser(main.Ui_MainWindow,QtWidgets.QMainWindow):

    def __init__(self):
        super(Browser, self).__init__()
        self.loop = asyncio.get_event_loop()
        self.client = Client(IP, PORT)
        self.Fs = self.getFs()
        self.setupUi(self)
        self.treeWidget.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        self.treeWidget.customContextMenuRequested.connect(self.contextMenu)
        self.checkIncomplete()
        self.populate()
        self.processes = []


    def checkIncomplete(self):
        '''
        Description: Wrapper function to get async code running
        '''
        return self.loop.run_until_complete(self.__checkIncomplete())

    async def __checkIncomplete(self):
        '''
        Description: Checks if nay files in temp folder not sent to
        server. Sends file to server.
        '''
        onlyfiles = [f for f in os.listdir('temp/') if os.path.isfile(os.path.join('temp/', f))]
        if len(onlyfiles) > 0:
            for file in onlyfiles:
                await self.__saveFileOnClose(file,0)


    def refresh(self):
        '''
        Description: Wrapper FS function to get async code running
        '''
        return self.loop.run_until_complete(self.__refresh())

    async def __refresh(self):
        '''
        Description: Refreshes the client after every 5 secs to ensure
        the single system image requirement.
        '''
        async with self.client:
            data = CommandObject(FS)
            await self.client.send(data)
            message = await self.client.receive()
            if message.command == FS:
                self.Fs = message.data
                self.treeWidget.clear()
                self.populate()


    def closeEvent(self, event):
        '''
        Description: Wrapper closeEvent function to get async code running
        '''
        return self.loop.run_until_complete(self.__close())

    async def __close(self):
        '''
        Description: Close event for the app. This will send a quit
        command to the server, then kill all the child processes and
        quit the app
        '''
        async with self.client:
            data = CommandObject(QUIT)
            await self.client.send(data)
            for process in self.processes:
                process.kill()

    def populate(self):
        '''
        Description: Populate the GUI with the FS
        '''
        if self.Fs == None:
            return
        else:
            for item, des in self.Fs.items():
                if des[-1]['Type'] == 'Root':
                    root = QtWidgets.QTreeWidgetItem([item, des[-1]['Type']])
                    self.treeWidget.addTopLevelItem(root)
                elif des[-1]['Parent'] == root.text(0):
                    root.addChild(QtWidgets.QTreeWidgetItem([item, des[-1]['Type']]))
                else:
                    pars = self.treeWidget.findItems(des[-1]['Parent'], QtCore.Qt.MatchContains|QtCore.Qt.MatchRecursive, 0)
                    for par in pars:
                        if par.text(1) == 'D':
                            par.addChild(QtWidgets.QTreeWidgetItem([item, des[-1]['Type']]))
            self.treeWidget.expandToDepth(root.childCount())

    def getFs(self):
        '''
        Description: Wrapper FS function to get async code running
        '''
        return self.loop.run_until_complete(self.__getFs())


    async def __getFs(self):
        '''
        Description: Connect to Client. Ask for Fs.
        Return FS
        '''
        async with self.client:
            data = CommandObject(FS)
            await self.client.send(data)
            message = await self.client.receive()
            return message.data if message.command == FS else None


    def contextMenu(self):
        '''
        Description: Makes the context menu and
        adds the triggers on it.
        '''
        menu = QtWidgets.QMenu()
        open = menu.addAction('Open')
        menu.addSeparator()
        newFolder = menu.addAction('New Folder')
        newFile = menu.addAction('New File')
        menu.addSeparator()
        rename = menu.addAction('Rename')
        menu.addSeparator()
        refreshs = menu.addAction('Refresh')

        open.triggered.connect(self.openFile)
        newFolder.triggered.connect(self.createNewFolder)
        newFile.triggered.connect(self.createNewFile)
        rename.triggered.connect(self.rename)
        refreshs.triggered.connect(self.refresh)
        cursor = QtGui.QCursor()
        menu.exec_(cursor.pos())

    def createNewFolder(self):
        '''
        Description: Pick up which folder/file was clicked.
        Ask the server for the file
        Save the file in a temp folder and return
        '''
        #get current item
        item = self.treeWidget.currentItem()
        #if item is a file, get the parent directory
        if item.text(1) == 'F':
            item = item.parent()
        #get new name
        self.addChild(item, 'D', 'newfolder')

    def addChild(self, parent, item1, command, oldName=''):
        child = QtWidgets.QTreeWidgetItem([' ', item1])
        parent.setFlags(QtCore.Qt.ItemIsEditable)
        parent.addChild(child)

        self.lineEdit = QtWidgets.QLineEdit()
        self.treeWidget.setItemWidget(child, 0, self.lineEdit)
        self.lineEdit.returnPressed.connect(lambda: self.onEnter(child, command, oldName))

    def onEnter(self, child, command, oldName=''):
        '''
        Description: Wrapper OnEnter function to get async code running
        To be executed when the user presses enter
        '''
        return self.loop.run_until_complete(self.__onEnter(child, command, oldName))


    async def __onEnter(self, child, command, oldName=''):
        '''
        Description: Actual on enter function
        This script picks up the user input, handles the input
        Then sends a Change request to the server depending on
        the argument. and waits for a reply to finally update the FS
        '''
        type = child.text(1)
        parent = child.parent()
        name = self.lineEdit.text().strip()
        #empty string
        if name == '':
            print("you cannot do this")
            return

        self.treeWidget.removeItemWidget(child,0)
        child.setText(0, name)
        parent.setFlags(parent.flags() & ~QtCore.Qt.ItemIsEditable)

        if parent.isDisabled():
            parent.setDisabled(False)

        #check name
        if name in self.Fs.keys():
            i = 1
            temp = name.rsplit('.',1)
            name = '{}({}).{}'.format(temp[0],i,temp[1])
            while name in self.Fs.keys():
                i += 1
                name = '{}({}).{}'.format(temp[0],i,temp[1])

        #update FS
        self.Fs[name] = {'Type' : type, 'Parent': parent.text(0)}

        if command == 'newfile':
            args = "gedit temp/{}".format(name)
            process = QtCore.QProcess(self)
            process.finished.connect(functools.partial(self.saveFileOnClose, name))
            process.start(args)
            self.processes.append(process)
            await self.__NewFsSave(name)

        elif command == 'newfolder':
            async with self.client:
                await self.client.send(CommandObject(NEWFOLDER , {name : self.Fs[name]}))
                message = await self.client.receive()
                if message.command == FS:
                    self.Fs = message.data
                    self.treeWidget.clear()
                    self.populate()

        elif command == 'rename':
            async with self.client:
                await self.client.send(CommandObject(RENAME, {'old': oldName, 'new' : name}))
                message = await self.client.receive()
                if message.command == FS:
                    self.Fs = message.data
                    self.treeWidget.clear()
                    self.populate()



    def createNewFile(self):
        '''
        Description: Pick up which folder/file was clicked.
        Ask the server for the file
        Save the file in a temp folder and return
        '''
        #get current item
        item = self.treeWidget.currentItem()
        #if item is a file, get the parent directory
        if item.text(1) == 'F':
            item = item.parent()
        #get new name
        self.addChild(item, 'F', 'newfile')


    def rename(self):
        '''
        Description: Call back function for when the rename
        for the context menu is clicked
        '''

        #get current item
        item = self.treeWidget.currentItem()
        #check if item is parent
        if item.text(1) == 'D':
            print('You shall not Do This')
            return
        else:
            self.lineEdit = QtWidgets.QLineEdit()
            self.treeWidget.setItemWidget(item, 0, self.lineEdit)
            self.lineEdit.returnPressed.connect(lambda: self.onEnter(item, 'rename', item.text(0)))


    async def __NewFsSave(self, name):
        '''
        Description: Sends a new created file fs change to the server
        Waits for reply and updates the current client Fs
        '''
        #send addition to fs
        async with self.client:
            await self.client.send(CommandObject(CREATE, {name : self.Fs[name]}))
            message = await self.client.receive()
            if message.command == FS:
                self.Fs = message.data
                self.treeWidget.clear()
                self.populate()
            else:
                print('Error')


    def saveFileOnClose(self, name, exitStatus):
        '''
        Description: Wrapper function to get async code running of OnFileClose
        '''
        return self.loop.run_until_complete(self.__saveFileOnClose(name, exitStatus))


    async def __saveFileOnClose(self, name, exitStatus):
        '''
        Description: Save the file to server on close. For new files and update files
        '''

        if exitStatus == 0 and os.path.isfile('temp/'+name):
            #properly shutdown and check if file exists
            with open('temp/'+name, 'r') as f:
                data = f.read()
                #send file contents to server
                async with self.client:
                    await self.client.send(CommandObject(FILE, {name : data}))
            #delete file from the client end.
            os.remove('temp/'+name)
        else:
            pass

    def openFile(self):
        '''
        Description: Wrapper OpenFile function to get async code running
        '''
        return self.loop.run_until_complete(self.__openFile())


    async def __openFile(self):
        '''
        Description: Pick up which folder/file was clicked.
        Ask the server for the file
        Save the file in a temp folder and return
        '''
        item = self.treeWidget.currentItem()
        #file_name
        name = item.text(0)

        #send request to server for file and wait for answer
        data = CommandObject(GIVEFILE, name)
        async with self.client:
            await self.client.send(data)

            message = await self.client.receive()
            #if proper command received
            if message.command == FILE:
                #save the file in temp folder
                args = "gedit temp/{}".format(name)
                try:
                    with open('temp/{}'.format(name), 'w+') as f:
                        f.write(message.data)
                except IOError as e:
                    print(e)
                #open the file
                process = QtCore.QProcess(self)
                process.finished.connect(functools.partial(self.saveFileOnClose, name))
                process.start(args)
                self.processes.append(process)
                #send the update command
                data = CommandObject(UPDATE, name)
                await self.client.send(data)
                message = await self.client.receive()
                if message.command == FS:
                    self.Fs = message.data
                    self.treeWidget.clear()
                    self.populate()

            elif message.command == CONN:
            #connect to a different client and send the file
                new_client = Client(message.data['IP'], int(message.data['PORT']))
                async with new_client:
                    await new_client.send(CommandObject(GIVEFILE, name))
                    file = await new_client.receive()
                    if file.command == FILE:
                        #FIGURE THIS OUT
                        print(file.data)
            else:
                print('File Cannot Open')
                return


if __name__ == '__main__':

    #read from file
    config = 'clientconfig.txt'
    try:
        if not os.stat(config).st_size == 0:
            f = open(config,'r+')

            #exists, open and read file
            data = json.load(f)

            #check host, port, connections, files
            IP = data['host'] if 'host' in data else ''
            PORT = data['port'] if 'port' in data else ''

            #make temp folder
            if not os.path.isdir('temp'):
                os.mkdir('temp')
            f.close()

    except OSError as e:
        #error in open
        print('Boot Error: {}'.format(e))
        f = open(config,'a+')
        f.close()

    except (IOError,ValueError) as e:
        #flush everything from the file and start from 0
        print('Boot Error: {}'.format(e))
        f = open(config, 'w+')
        f.close()

    #start the app
    app = QtWidgets.QApplication([])
    browser = Browser()
    browser.show()
    app.exec_()


