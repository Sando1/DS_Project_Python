import asyncio
import dill
import struct
import os, sys
import signal
import functools

from PyQt5 import QtCore, QtGui, QtWidgets
import gui as main

IP = 'localhost'
PORT = 30001


CREATE, UPDATE, FS, FILE, REPLICATEFILE, GIVEFILE, CONNCLIENT, NEWFOLDER, RENAME, QUIT, ERROR, SUCCESS, CONN = range(13)

class CommandObject(object):
    '''A command object to pass. It ensures security'''

    def __init__(self, command, data=None):
        self.command = command
        self.data = data


class Client():

    async def __aenter__(self):
        '''
        Description: Function to enter and connect with the server
        '''
        try:
            self.reader, self.writer = await asyncio.open_connection(IP, PORT)
            return
        except Exception as e:
            print(e)
            sys.exit(0)

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
            return False

    async def __aexit__(self, *args, **kwargs):
        '''
        Description: Loop to run upon closing the server
        '''
        pass

    async def close(self):
        self.writer.transport.close()

class Browser(main.Ui_MainWindow,QtWidgets.QMainWindow):

    def __init__(self):
        super(Browser, self).__init__()
        self.client = Client()
        self.loop = asyncio.get_event_loop()
        self.Fs = self.getFs()
        self.setupUi(self)
        self.treeWidget.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        self.treeWidget.customContextMenuRequested.connect(self.contextMenu)
        self.populate()

    def populate(self):
        '''
        Description: Populate the GUI with the FS
        '''
        if self.Fs != None:
            for item, des in self.Fs.items():
                if des[-1]['Type'] == 'Root':
                    root = QtWidgets.QTreeWidgetItem([item, des[-1]['Type']])
                    self.treeWidget.addTopLevelItem(root)
                elif des[-1]['Parent'] == root.text(0):
                    root.addChild(QtWidgets.QTreeWidgetItem([item, des[-1]['Type']]))
                else:
                    pars = self.treeWidget.findItems(des[-1]['Parent'], QtCore.Qt.MatchContains|QtCore.Qt.MatchRecursive, 0)
                    pars[0].addChild(QtWidgets.QTreeWidgetItem([item, des[-1]['Type']]))
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

        open.triggered.connect(self.openFile)
        newFolder.triggered.connect(self.createNewFolder)
        newFile.triggered.connect(self.createNewFile)
        rename.triggered.connect(self.rename)
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
        #get all info on the item

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

        #update FS
        self.Fs[name] = {'Type' : type, 'Parent': parent.text(0)}
        if command == 'newfile':
            args = "gedit temp/{}".format(name)
            process = QtCore.QProcess(self)
            process.finished.connect(functools.partial(self.saveFileOnClose, name))
            process.start(args)
            await self.__NewFsSave(name)

        elif command == 'newfolder':
            await self.client.send(CommandObject(NEWFOLDER , {name : self.Fs[name]}))
            message = await self.client.receive()
            if message.command == FS:
                self.Fs = message.data
                self.treeWidget.clear()
                self.populate()
                return

        elif command == 'rename':
            await self.client.send(CommandObject(RENAME, {'old': oldName, 'new' : name}))
            message = await self.client.receive()
            if message.command == FS:
                self.Fs = message.data
                return


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
        self.addChild(item, '', 'F', 'newfile')


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
        await self.client.send(CommandObject(CREATE, {name : self.Fs[name]}))
        message = await self.client.receive()
        if message.command == FS:
            self.Fs = message.data
            return


    def saveFileOnClose(self,  name, exitStatus):
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
                print(data)
                #send file contents to server
                await self.client.send(CommandObject(FILE, {name : data}))
                #message = await self.client.receive()
                #if message.command == SUCCESS:
                    #delete file from the client end.
                    #os.remove('temp/'+name)
                    #break


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
        await self.client.send(data)
        message = await self.client.receive()
        #if proper command received
        if message.command == FILE:
            print(message.data)
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
            IP = message.data['IP']
            PORT = int(message.data['PORT'])
            new_client = Client()
            await new_client.send(CommandObject(GIVEFILE, name))
            file = await new_client.receive()
            if file.command == FILE:
                print(file.data)
                new_client.close()
        else:
            print('File Cannot Open')


if __name__ == '__main__':

    #make temp folder
    if not os.path.isdir('temp'):
        os.mkdir('temp')
    #start the app
    app = QtWidgets.QApplication([])
    browser = Browser()
    browser.show()
    app.exec_()


