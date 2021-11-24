#Python 3
#Usage: python3 client3.py serverIP serverPort UDPport
#coding: utf-8
from socket import *
import threading
import sys
import time

# get server information
serverName = sys.argv[1]
serverPort = int(sys.argv[2])

# get client receive udp port
recvUdpPort = int(sys.argv[3])

# get client ip
clientIP = gethostbyname(gethostname())

# create client tcp socket
clientSocket = socket(AF_INET, SOCK_STREAM)
clientSocket.connect((serverName, serverPort))

# create active user list
activeUser = {}

def sendFile(sendSocket, addr):
    # tell audience ready to receive file
    regist = f'UPD\n{username}\n{fileName}\n\n'
    sendSocket.sendto(regist.encode('utf-8'), addr)

    with open(fileName, 'rb') as fileObject:
        finish = False
        while not finish:
            # send every 8k packet of to audience
            data = fileObject.read(8192)
            if not data:
                sendSocket.sendto(''.encode('utf-8'), addr)
                finish = True
            else:
                sendSocket.sendto(data, addr)
                # wait audience finish write
                time.sleep(0.01)
    print(f'\n{fileName} has been uploaded\n\nEnter one of the following commands (MSG, DLT, EDT, RDM, ATU, OUT, UPD): ', end='')


def recvFile(audSocket):
    # recevie file from sender
    while True:
        data = audSocket.recvfrom(1024)[0].decode('utf-8').split('\n')
        if data[0] == 'UPD':
            presenter = data[1]
            fileName = presenter + '_' + data[2]
            
            with open(fileName, 'wb') as downloadFile:
                finish = False
                while not finish:
                    data = audSocket.recvfrom(8192)[0]
                    if not data:
                        finish = True
                    else:
                        downloadFile.write(data)
                print(f'\nReceived {fileName} from {presenter}\n\n'+\
                'Enter one of the following commands (MSG, DLT, EDT, RDM, ATU, OUT, UPD): ', end='')

def checkTime(testTime):
    # check whether input time is valid
    try:
        if testTime[1][1:].isupper() or testTime[1][0].islower() or len(testTime[3]) < 8:
            return False

        testTime = ' '.join(testTime)
        # if input time can be translated into timestamp
        time.strptime(testTime, "%d %b %Y %H:%M:%S")
        return True
    except:
        # error raise if input cannot be translated into timestamp
        return False

if __name__ == '__main__':
    login = False
    lock = False
    while not login and not lock:
        # get client login information
        username = input("Username: ")
        if not username:
            print("Username cannot be empty, please input your username.")
            continue

        password = input("Password: ")
        if not password:
            print("Password cannot be empty, please input your password.")
            continue

        # send client login information to server
        clientSocket.send(f'LOGIN\n{username}\n{password}\n\n'.encode('utf-8'))
        loginInfo = clientSocket.recv(64).decode('utf-8').split(' ')

        if loginInfo[0] == 'SUCCESS':
            # login success
            print("Welcome to TOOM!")
            login = True

        elif loginInfo[0] == 'FAIL':
            # print fail message and reamin attempts
            print(f'Invalid Password. Please try again (remain attempt: {loginInfo[1]})')

        elif loginInfo[0] == 'LOCK':
            if loginInfo[1] == '001':
                # print lock message
                print("Your account is blocked due to multiple login failures. Please try again later")
                lock = True
            else:
                # print lock message and reamining time to unlock
                print(f'Your account has been blocked ({loginInfo[2]}s left). Please try again later')
                lock = True

        elif loginInfo[0] == 'NOEX':
            # print account not exist message
            print("Your account does not exist, please check your username.")
    
    if not lock:
        # send client login detail to server
        clientSocket.send(str(recvUdpPort).encode('utf-8'))
        
        # udp socket is to send file to another clients
        clientUdpSocket = socket(AF_INET, SOCK_DGRAM)
        clientUdpSocket.setsockopt(SOL_SOCKET, SO_REUSEADDR, 1)
        clientUdpSocket.bind((clientIP, 0)) # set udp socket by local address and random assigned port number

        # udp socket to listen and download file from other clients
        recvUdpSocket = socket(AF_INET, SOCK_DGRAM)
        recvUdpSocket.setsockopt(SOL_SOCKET, SO_REUSEADDR, 1)
        recvUdpSocket.bind((clientIP, recvUdpPort))

        # set receive function into multithread
        recvThread = threading.Thread(name="recvFile", target=recvFile, args=(recvUdpSocket,))
        recvThread.daemon=True
        recvThread.start()

        while True:
            command = input("Enter one of the following commands (MSG, DLT, EDT, RDM, ATU, OUT, UPD): ").split()
            
            if not command:
                continue
            if command[0] == 'MSG':
                # send message
                if len(command) < 2:
                    print("Invalid syntax. Syntax: MSG message")
                else:
                    message = ' '.join(command[1:])
                    clientSocket.send(f'MSG\n{message}\n{username}\n\n'.encode('utf-8'))
                    receipt = clientSocket.recv(1024).decode('utf-8').split('\n')
                    print(f'Message #{receipt[1]} posted at {receipt[2]}.')
                    
            elif command[0] == 'DLT':
                # delete message
                if len(command) < 6 or command[1][0] != '#' or len(command[1]) < 2 or not command[1][1:].isdigit():
                    print('Invalid syntax. Syntax: DLT #sequence time')
                elif not checkTime(command[2:]):
                    print("Incorrect timestamp format. Format: dd Mmm yyyy hh:mm:ss")
                else:
                    timestamp = ' '.join(command[2:])
                    seq = command[1][1:]
                    clientSocket.send((f'DLT\n{seq}\n{timestamp}\n{username}\n\n').encode('utf-8'))
                    receipt = clientSocket.recv(1024).decode('utf-8').split()
                    if receipt[0] == 'DTF':
                        if receipt[1] == '001':
                            print('Message does not exist, please check you sequence number!')
                        elif receipt[1] == '002':
                            print('Delete message fail, please check you timestamp!')
                        else:
                            print(f'Unauthorised to delete Message #{seq}')

                    elif receipt[0] == 'DTS':
                        deleteTime = ' '.join(receipt[1:])
                        print(f'Message {seq} deleted at {deleteTime}.')
            
            elif command[0] == 'EDT':
                # edit message
                if len(command) < 7 or command[1][0] != '#' or len(command[1]) < 2 or not command[1][1:].isdigit():
                    print('Invalid syntax. Syntax: EDT #sequence time message')
                elif not checkTime(command[2:-1]):
                    print("Incorrect timestamp format. Format: dd Mmm yyyy hh:mm:ss")
                else:
                    seq = command[1][1:]
                    timestamp = ' '.join(command[2:6])
                    message = ' '.join(command[6:])
                    clientSocket.send(f'EDT\n{seq}\n{timestamp}\n{message}\n{username}\n\n'.encode('utf-8'))
                    receipt = clientSocket.recv(1024).decode('utf-8').split()
                    if receipt[0] == 'ETF':
                        if receipt[1] == '001':
                            print('Message does not exist, please check you sequence number!')
                        elif receipt[1] == '002':
                            print('Edit message fail, please check you timestamp!')
                        else:
                            print(f'Unauthorised to edit Message #{seq}')

                    elif receipt[0] == 'ETS':
                        editTime = ' '.join(receipt[1:])
                        print(f'Message {seq} edited at {editTime}.')

            elif command[0] == 'RDM':
                # read message since specific time
                if len(command) < 5:
                    print("Missing specific timestamp. Syntax: RDM timestamp")
                elif not checkTime(command[1:]):
                    print("Incorrect timestamp format. Format: dd Mmm yyyy hh:mm:ss")
                else:
                    timestamp = ' '.join(command[1:])
                    clientSocket.send((f'RDM\n{timestamp}\n{username}\n\n').encode('utf-8'))
                    finish = False
                    while not finish:
                        receipt = clientSocket.recv(4096).decode('utf-8').split('\n')
                        if receipt[0] == 'ERDM':
                            # last packet of message receive
                            finish = True
                        elif receipt[0] == 'NMSG':
                            print("No new Message")
                            break

                        for response in receipt[1:]:
                            if response:
                                message = response.split('; ')
                                if message[-1] == 'yes':
                                    message = f'#{message[0]}, {message[2]}: "{message[3]}", edited at {message[1]}.'
                                    print(message)
                                elif message[-1] == 'no':
                                    message = f'#{message[0]}, {message[2]}: "{message[3]}", posted at {message[1]}.'
                                    print(message)

            elif command[0] == 'ATU':
                # get active user list
                if len(command) > 1:
                    print('Extra arguments given. Syntax: ATU')
                else:
                    clientSocket.send((f'ATU\n{username}\n\n').encode('utf-8'))
                    activeUser.clear()
                    
                    finish = False
                    while not finish:
                        receipt = clientSocket.recv(2048).decode('utf-8').split('\n')
                        if receipt[0] == 'NATU':
                            print("No activce user currently.")
                            break
                        elif receipt[0] == 'EATU':
                            # last packet of active user list
                            finish = True
                            
                        for response in receipt[1:]:
                            if response:
                                info = response.split('; ')
                                activeUser[info[2]] = (info[3], int(info[4]))
                                print(f'{info[2]}, {info[3]}, {info[4]}, active since {info[1]}.')

            elif command[0] == 'OUT':
                # logout
                if len(command) > 1:
                    print('Extra arguments given. Syntax: OUT')
                else:
                    clientSocket.send(f'OUT\n{username}\n\n'.encode('utf-8'))
                    receipt = clientSocket.recv(64).decode('utf-8')
                    if receipt == 'LOS':
                        print("Logout successfully.")
                    break

            elif command[0] == 'UPD':
                # send file to another client
                if len(command) < 3:
                    print("Insufficient given arguments. Syntax: UPD username filename")
                else:
                    # get audience and file information
                    audience = command[1]
                    fileName = command[2]

                    if audience in activeUser:
                        addr = activeUser[audience]
                        sendThread = threading.Thread(name="sendFile", target=sendFile, args=(clientUdpSocket, addr))
                        sendThread.daemon=True
                        sendThread.start()

                    else:
                        print(f'{audience} is offline, Retry later')
            else:
                print("Invalid command, please follow the correct format!")

            print()

        # Close the socket
        clientSocket.close()
        clientUdpSocket.close()
        recvUdpSocket.close()
        print(f'Bye, {username}!')