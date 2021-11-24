# userlog module
#Python3
import threading
import time
import sys

class UserLog:
    def __init__(self, maxLogin):
        self.t_lock = threading.Condition() # lock for multithread
        self.attempt = {} # attempt user list
        self.maxLogin = maxLogin # every client max login attempt
        self.userSeq = 0 # current number of active client

    def loginAttempt(self, username, password, socket):
        self.t_lock.acquire()
        if username in self.attempt and self.attempt[username][0] == self.maxLogin:
            if time.time() - self.attempt[username][1] <= 10:
                # tell client the account has been locked
                # and the time reamining to unlock

                remainTime = int(10 - (time.time() - self.attempt[username][1]))
                socket.send(f'LOCK 002 {remainTime}'.encode('utf-8'))
                self.t_lock.notify()
                self.t_lock.release()
                return False
            else:
                # unlock the account
                self.attempt[username][0] = 0

        with open('credentials.txt') as loginFile:
            for line in loginFile.readlines():
                # get database's username and password
                attemptName = line.split()[0]
                attemptPass = line.split()[1]

                if username == attemptName:
                    if password == attemptPass:
                        # if pass authentication delete the user's attempt record
                        # and send success response to client
                        if username in self.attempt:
                            del self.attempt[username]
                        self.t_lock.notify()
                        self.t_lock.release()
                        socket.send('SUCCESS'.encode('utf-8'))
                        return True

                    else:
                        remain = self.maxLogin
                        if username not in self.attempt:
                            # add client to attempt list
                            self.attempt[username] = [1, time.time()]
                            remain -= 1
                            socket.send(f'FAIL {remain}'.encode('utf-8'))

                        elif (time.time() - self.attempt[username][1]) > 10:
                            # recount client attempt
                            self.attempt[username][0] = 1
                            self.attempt[username][1] = time.time()
                            remain -= 1
                            socket.send(f'FAIL {remain}'.encode('utf-8'))

                        else:
                            # increase client's number of attempt
                            self.attempt[username][0] += 1
                            self.attempt[username][1] = time.time()
                            if self.attempt[username][0] < self.maxLogin:
                                remain -= self.attempt[username][0]
                                socket.send(f'FAIL {remain}'.encode('utf-8'))
                            else:
                                socket.send('LOCK 001'.encode('utf-8'))

                        self.t_lock.notify()
                        self.t_lock.release()
                        return False

        # not exist account
        socket.send('NOEX'.encode('utf-8'))
        self.t_lock.notify()
        self.t_lock.release()
        return False

    def logFile(self, mode, username, addr=None, clientUdpPort=None, socket=None):
        self.t_lock.acquire()
        if mode == 0:
            # add client into active user file
            with open('userlog.txt', 'a') as userLog:
                self.userSeq += 1
                loginTime = time.strftime('%d %b %Y %H:%M:%S', time.localtime())
                userLog.write(f'{self.userSeq}; {loginTime}; {username}; {addr[0]}; {clientUdpPort}\n')
                print(f'{username} login')

        elif mode == 1:
            # read current active  user
            print(f'{username} issued ATU command.')
            response = ''
            found = False
            with open('userlog.txt') as userLog:     
                for line in userLog.readlines():
                    cmpUser = line.split('; ')[2]
                    if cmpUser != username:
                        if not found:
                            print(f'Return active user list:')
                        found = True

                        if sys.getsizeof(response.encode('utf-8')) + sys.getsizeof(line.encode('utf-8')) + 5 > 2048:
                            # send every 2k packet of current active user list
                            socket.send(f'ATUL\n{response}\n'.encode('utf-8'))
                            printATU(response)
                            response = ''
                        response += line

            if not found:
                print(f'No active user.')
                socket.send('NATU'.encode('utf-8'))
            else:
                # send last packet of active user list
                socket.send(f'EATU\n{response}\n'.encode('utf-8'))
                printATU(response)
        
        elif mode == 2:
            # client logout
            deleted = False
            length = 0
            with open('userlog.txt', 'r+') as userLog:
                for line in userLog.readlines():
                    length += len(line) if not deleted else 0
                    localLen = len(line) if not deleted else 0
                    line = line.split('; ')

                    if not deleted and line[2] == username:
                        # redirect pointer to logout client in file
                        userLog.seek(length - localLen, 0)
                        self.userSeq -= 1 # reduce number of active user
                        deleted = True
                    elif deleted and line[2] != username:
                        # following data cover the logout client data
                        modifiedSeq = str(int(line[0]) - 1)
                        modifiedLine = modifiedSeq + '; ' +'; '.join(line[1:])
                        userLog.write(f'{modifiedLine}')
                userLog.truncate() # delete redundence data
                
        self.t_lock.notify()
        self.t_lock.release()

def printATU(atu):
    # print active user list
    for activeUser in atu.split('\n'):
        if (activeUser):
            activeUser = activeUser.split('; ')
            print(f'{activeUser[2]}, active since {activeUser[1]}')