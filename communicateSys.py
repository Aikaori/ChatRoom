# communication system module
#Python3
import threading
import time
import sys

class commuSys:
    def __init__(self):
        self.t_lock = threading.Condition()
        self.msgSeq = 0
        self.getMsgSeq()

    def getMsgSeq(self):
        with open('messagelog.txt') as messageLog:
            self.msgSeq = len(messageLog.readlines())

    def msgModify(self, username, socket, mode, msgNum=None, message=None, timestamp=None):
        self.t_lock.acquire()
        deleted = False
        edited = False
        length = 0

        if mode == 0:
            with open('messagelog.txt', 'a') as messageLog:
                self.msgSeq += 1
                postTime = time.strftime('%d %b %Y %H:%M:%S', time.localtime())
                messageLog.write(f'{self.msgSeq}; {postTime}; {username}; {message}; no\n')
                socket.send(f'POS\n{self.msgSeq}\n{postTime}\n\n'.encode('utf-8'))
                print(f'{username} posted MSG #{self.msgSeq} "{message}" at {postTime}.')

        else:
            attemptTime = time.strftime('%d %b %Y %H:%M:%S', time.localtime())
            if (int(msgNum) > self.msgSeq or int(msgNum) < 1):
                if mode == 1:
                    print(f'{username} attempts to delete MSG #{msgNum} at {attemptTime}. Invalid sequence number.')
                    socket.send('DTF 001'.encode('utf-8'))
                else:
                    print(f'{username} attempts to edit MSG #{msgNum} at {attemptTime}. Invalid sequence number.')
                    socket.send(f'ETF 001'.encode('utf-8'))
            else:
                with open('messagelog.txt', 'r+') as logFile:
                    for line in logFile.readlines():
                        length += len(line) if not deleted else 0
                        localLen = len(line) if not deleted else 0
                        line = line.split('; ')

                        if line[0] == msgNum:
                            if line[1] == timestamp and line[2] == username:
                                logFile.seek(length - localLen, 0)
                                if mode == 1:
                                    dltMsg = line[3]
                                    self.msgSeq -= 1
                                    deleted = True
                                else:
                                    edtMsg = message
                                    logFile.write(f'{msgNum}; {attemptTime}; {username}; {message}; yes\n')
                                    edited = True
                            else:
                                if mode == 1:
                                    if line[1] != timestamp:
                                        print(f'{username} attempts to delete MSG #{msgNum} at {attemptTime}. Incorrect timestamp.')
                                        socket.send(f'DTF 002\n'.encode('utf-8'))
                                    else:
                                        print(f'{username} attempts to delete MSG #{msgNum} at {attemptTime}. Authorisation fails.')
                                        socket.send(f'DTF 003\n'.encode('utf-8'))

                                elif mode == 2:
                                    if line[1] != timestamp:
                                        print(f'{username} attempts to edit MSG #{msgNum} at {attemptTime}. Incorrect timestamp.')
                                        socket.send(f'ETF 002'.encode('utf-8'))
                                    else:
                                        print(f'{username} attempts to edit MSG #{msgNum} at {attemptTime}. Authorisation fails.')
                                        socket.send(f'ETF 003'.encode('utf-8'))

                                break

                        elif deleted:
                            modifiedMessageSeq = str(int(line[0]) - 1)
                            modifiedLine = modifiedMessageSeq + '; ' +'; '.join(line[1:])
                            logFile.write(f'{modifiedLine}')
                        elif edited:
                            message = '; '.join(line)
                            logFile.write(f'{message}')

                    if deleted or edited:
                        logFile.truncate()
                        if deleted:
                            print(f'{username} deleted MSG #{msgNum} "{dltMsg}" at {attemptTime}.')
                            socket.send(f'DTS\n{attemptTime}\n\n'.encode('utf-8'))
                        elif edited:
                            print(f'{username} edited MSG #{msgNum} "{edtMsg}" at {attemptTime}.')
                            socket.send(f'ETS\n{attemptTime}\n\n'.encode('utf-8'))
                            
        self.t_lock.notify()
        self.t_lock.release()

    def readMsg(self, username, timestamp, socket):
        with self.t_lock:
            print(f'Return messages:')
            with open('messagelog.txt', 'r+') as messageLog:
                found = False
                response = ''
                for line in messageLog.readlines():
                    cmpUser = line.split('; ')[2]
                    postTime = time.mktime(time.strptime(line.split('; ')[1], '%d %b %Y %H:%M:%S'))
                    if postTime > timestamp:
                        found = True
                        if sys.getsizeof(response.encode('utf-8')) + sys.getsizeof(line.encode('utf-8')) + 5 > 4096:
                            socket.send(f'PRDM\n{response}\n'.encode('utf-8'))
                            printMsg(response)
                            response = ''

                        response += line

                if not found:
                    socket.send('NMSG'.encode('utf-8'))
                else:
                    socket.send(f'ERDM\n{response}\n'.encode('utf-8'))
                    printMsg(response)
                
            self.t_lock.notify()

def printMsg(msgs):
    msgs = msgs.split('\n')
    for message in msgs:
        message = message.split('; ')
        if message[-1] == 'yes':
            message = f'#{message[0]}, {message[2]}: "{message[3]}", edited at {message[1]}.'
            print(message)
        elif message[-1] == 'no':
            message = f'#{message[0]}, {message[2]}: "{message[3]}", posted at {message[1]}.'
            print(message)