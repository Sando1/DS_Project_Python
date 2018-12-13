Setup

The system comes with the following code files:
    • Server.py
    • connection.py
    • services.py
    • settings.py
    • gui.py
    • client.py

There are separate config files and files file which ensures correct boot. Also in the folder are dsenv.yml file which is the environment file for the system and packages.txt which holds the current snapshot of the system packages.

To setup:
    • Ensure that anaconda is installed on the server
    • Download the folder containing the files.
    • Open terminal and navigate to where you have downloaded the folder
    • Enter the folder directory
    • Run command conda-env create -n dsenv -f=dsenv.yml. Ensure yml file path is correct
    • If successful, run command source activate dsenv
    • To start the server, open config file, and update host and port address
    • Then in the terminal type command python3 server.py
    • To start the client open configclient file and update host and port to the server you want to connect to.
    • Open a new terminal, navigate to client.py, run environment and type command python3 client.py
