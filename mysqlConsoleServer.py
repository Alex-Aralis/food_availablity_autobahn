import time
import signal
import mysql.connector as mariadb
from subprocess import Popen
from twisted.internet.defer import inlineCallbacks
from twisted.internet import reactor, task
from autobahn.twisted.util import sleep
from autobahn.twisted.wamp import ApplicationSession, ApplicationRunner
import base64
from Crypto.Cipher import AES

def srv_log(msg):
    print('[server] ' + str(msg))

class Server(ApplicationSession):
    sessions = {}
    watchdogs = {}
    hunger = 30;
#    rootConn = None;
#    rootCursor = None;

    @inlineCallbacks
    def onJoin(self, details):
        srv_log('server joined')

        def closeSession(sessionName, exited=True):
            srv_log('closing session ' + sessionName)
            srv_log('current sessions ' + str(self.sessions))
            srv_log('current watchdogs ' + str(self.watchdogs))
            try:
                #self.sessions[sessionName].terminate()
                self.sessions[sessionName].send_signal(signal.SIGINT)
                if exited:
                    self.watchdogs[sessionName].cancel()

                del self.watchdogs[sessionName]
                del self.sessions[sessionName]
                return 'session '+sessionName+' closed'
            except Exception as e:
                srv_log('error closing ' + sessionName)
                srv_log(str(e))
                return 'error closing session:' + str(e)

        def createSession(accountSessionId, accountSessionEncPW):
            srv_log('session requested')
            srv_log('accountSessionId: ' + str(int(accountSessionId)));
            srv_log('accountSessionEncPW: ' + str(base64.b64decode(accountSessionEncPW)));
            srv_log('accountSessionEncPW length: ' + str(len(base64.b64decode(accountSessionEncPW)[8:])));

            self.rootCursor.execute("SELECT user_name, pw_enc_key, iv FROM account_sessions WHERE id=%s", 
                                  (accountSessionId,))

            accountUserName, pwEncKey, iv = self.rootCursor.fetchone()
            
            cipher = AES.new(bytes(pwEncKey), AES.MODE_CBC, bytes(iv))

            unpad = lambda b : b[0:-b[-1]]

            plaintextPw = unpad(cipher.decrypt(base64.b64decode(accountSessionEncPW))).decode()
            
            srv_log(accountUserName + ": " + plaintextPw);
            
            creation = str(int(time.time()*1000))
            self.sessions[creation] = Popen(['python','mysqlConsoleSession.py', creation, accountUserName, plaintextPw])
            self.watchdogs[creation] = reactor.callLater(self.hunger, closeSession, creation, False)
            srv_log('mysqlConsoleSession.py called: ' + creation)
            return creation



        def giveBone(sessionName):
            srv_log('bone given to ' + sessionName)
            self.watchdogs[sessionName].cancel()
            self.watchdogs[sessionName] = reactor.callLater(self.hunger, closeSession, sessionName, False)

            return self.hunger;

        yield self.register(createSession, u'com.mysql.console.requestSession')
        yield self.register(closeSession, u'com.mysql.console.closeSession')
        yield self.register(giveBone, u'com.mysql.console.giveBone')
        
        srv_log('request session registered')

        

if __name__ == '__main__':
    srv_log('running as main')

    srv_log('connecting to mariadb...')
    Server.rootConn = mariadb.connect(user='root', password='skunkskunk2', database='food_account_data')
    Server.rootCursor = Server.rootConn.cursor(buffered=True)
    srv_log('mariadb connected.')

    serverRunner = ApplicationRunner(u'ws://localhost:8081/ws', u'realm1')
    d = serverRunner.run(Server, False)
    d.addErrback(srv_log)

    reactor.run()
    
    srv_log('server proc ending')

