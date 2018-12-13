def init():
    global CONFIG_FILE
    global FILES_FILE
    global CONNECTIONS
    global SERVERS
    global FILES

    global HOST
    global PORT

    CONFIG_FILE = 'config.txt'
    FILES_FILE = 'files.txt'
    SERVERS = {}
    CONNECTIONS = {}
    FILES = {}

    HOST = ''
    PORT = 0
