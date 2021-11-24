# Multi-Threaded Server
#Python 3
# Usage: python3 server3.py portnumber maxlogin
#coding: utf-8
from socket import *
import threading
import time
import sys
from userlog import *
from communicateSys import *
#Server will run on this port
serverPort = int(sys.argv[1])
maxLogin = int(sys.argv[2])

def recv_handler(connectionSocket, addr):
    global loginDB
    global comDB

    login = False
    while not login:
        # wait for login info
        request = connectionSocket.recv(1024).decode('utf-8').split('\n')
        # get user login mode
        # could be login or register (not impletment in this version)
        mode = request[0]

        if mode == 'LOGIN':
            # get user information
            username = request[1]
            password = request[2]
            if loginDB.loginAttempt(username, password, connectionSocket):
                login = True

    #receive user UDP port number
    clientUdpPort = connectionSocket.recv(8).decode('utf-8')
    loginDB.logFile(0, username, addr, clientUdpPort)

    logout = False
    while not logout:
        # get client operation request
        operation = connectionSocket.recv(1024).decode('utf-8').split('\n')

        if operation[0] == 'MSG':
            # post message
            message = operation[1]
            username = operation[2]
            comDB.msgModify(username, connectionSocket, 0, message=message)

        elif operation[0] == 'DLT':
            # delete message
            msgNum = operation[1]
            timestamp = operation[2]
            username = operation[3]
            comDB.msgModify(username, connectionSocket, 1, msgNum=msgNum, timestamp=timestamp)

        elif operation[0] == 'EDT':
            # edit message
            msgNum = operation[1]
            timestamp = operation[2]
            message = operation[3]
            username = operation[4]
            comDB.msgModify(username, connectionSocket, 2, msgNum, message, timestamp)

        elif operation[0] == 'RDM':
            # read message since specific time
            timestamp = time.mktime(time.strptime(operation[1], '%d %b %Y %H:%M:%S'))
            username = operation[2]
            print(f'{username} issued RDM command')
            comDB.readMsg(username, timestamp, connectionSocket)
            

        elif operation[0] == 'ATU':
            # get active user list
            username = operation[1]
            loginDB.logFile(1, username, socket=connectionSocket)

        elif operation[0] == 'OUT':
            # client logout
            # remove posted message
            # remove from active user list
            username = operation[1]
            loginDB.logFile(2, username)
            print(f'{username} logout')
            logout = True
            connectionSocket.send(f'LOS'.encode('utf-8'))
            connectionSocket.close()

if __name__ == '__main__':
    if maxLogin > 5 or maxLogin < 1:
        print(f'Invalid number of allowed failed consecutive attempt: {maxLogin}. The valid value of argument number is an integer between 1 and 5')
    else:
        # get server IP
        serverIP = gethostbyname(gethostname())

        # creating server socket
        serverSocket = socket(AF_INET, SOCK_STREAM)
        serverSocket.setsockopt(SOL_SOCKET, SO_REUSEADDR, 1)
        serverSocket.bind((serverIP, serverPort))
        serverSocket.listen(5)
        
        # create login database to manage login user
        loginDB = UserLog(maxLogin)
        # create message database
        comDB = commuSys()
        print(f'Server start at IP:{serverIP}')
        # this is the main thread to wait client connect to the server
        # once client connected, turn into multithread to handle clients request
        # then continue wait for another client
        while True:
            # get connection requet and create connection socket to connect with client
            connectionSocket, addr = serverSocket.accept()

            # turn into multithread
            recv_thread = threading.Thread(name="RecvHandler", target=recv_handler, args=(connectionSocket, addr))
            recv_thread.daemon = True
            recv_thread.start()