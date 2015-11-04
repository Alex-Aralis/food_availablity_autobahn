import time
import signal
import mysql.connector as mariadb
from subprocess import Popen
from twisted.internet.defer import inlineCallbacks
from twisted.internet import reactor, task, threads
from autobahn.twisted.util import sleep
from autobahn.twisted.wamp import ApplicationSession, ApplicationRunner
import base64
import sys
import json


import mysqlConsoleSession

from Crypto.Cipher import AES

unpad = lambda b : b[0:-b[-1]]

def srv_log(msg):
    print('[server] ' + str(msg))

class SessionThread(mariadb.MySQLConnection):
    def __init__(self, wampAppSess, timeout, **kwargs):
        
        self.log('initing new session')

        self.log('initing new session with' + str(kwargs))
        super().__init__(**kwargs)
        self.log('MySQLConnection initialized')

        self.log('initing with timeout=' + str(timeout))
        self.timeout = timeout
        self.wampAppSess = wampAppSess

        self.log('setting watchdog')
        self.watchdog = reactor.callLater(timeout, self.cleanup)
        self.log('init complete')

    def log(self, msg):
        try:
            print('[session ' + str(self.connection_id) + '] ' + str(msg))
        except Exception: 
            print('[session ?] ' + str(msg))
        
    def wampQuery(self, sql):
        self.log('wamp query recieved: ' + str(sql));

        try:
            cursor = self.cursor(buffered=True)

            cursor.execute(sql)
 
            result = json.dumps(cursor.fetchall())
 
            cursor.close()

        except mariadb.errors.ProgrammingError as e:
            self.log(e)
            result = str(e)
        except Exception as e:
            self.log(e)
            result = str(e)
        finally:
            self.log('returning result')
            return result;

        
    def threadedWampQuery(self, sql):
        self.log('threaded query request recieved')
        return threads.deferToThread(self.wampQuery, sql)
        self.log('query thread spun')

    def cleanup(self, exited):
        self.log('cleanup entered')

        if exited: 
            self.watchdog.cancel()

        try:
            self.disconnect()
            self.log('disconnected from mysql server')
            return 0
        except Exception as e:
            self.log('disconnect failed, attempting shutdown')
            sess.shutdown()
            return 1


class Server(ApplicationSession):
    sessions = {}
    hunger = 30;

    def closeSession(self, sessionName, exited=True):
        srv_log('closing session ' + str(sessionName))
        srv_log('current sessions ' + str(self.sessions))
        try:
            self.sessions[sessionName].cleanup(exited)

            del self.sessions[sessionName]

            return 'session '+str(sessionName)+' closed'
        except Exception as e:
            srv_log('error closing ' + str(sessionName))
            srv_log(str(e))
            return 'error closing session:' + str(e)

    @inlineCallbacks
    def onJoin(self, details):
        srv_log('server joined')


        def createSession(accountSessionId, accountSessionEncPW):
            srv_log('session requested')
            srv_log('accountSessionId: ' + str(int(accountSessionId)));
            srv_log('accountSessionEncPW: ' + str(base64.b64decode(accountSessionEncPW)));
            srv_log('accountSessionEncPW length: ' + str(len(base64.b64decode(accountSessionEncPW))));

            
            rootCursor = self.rootConn.cursor(buffered=True)

            rootCursor.execute("SELECT user_name, pw_enc_key, iv FROM account_sessions WHERE id=%s", 
                                  (accountSessionId,))

            accountUserName, pwEncKey, iv = rootCursor.fetchone()
            
            cipher = AES.new(bytes(pwEncKey), AES.MODE_CBC, bytes(iv))


            plaintextPw = unpad(cipher.decrypt(base64.b64decode(accountSessionEncPW))).decode()
            
            srv_log(accountUserName + ": " + plaintextPw);
           
            sess = SessionThread(self, self.hunger, user=accountUserName,  
                password=plaintextPw, database='food_account_data')
             
          
            self.sessions[sess.connection_id] = sess 

           
            srv_log('new SessionThread called: ' + str(sess.connection_id))


            return sess.connection_id;



        def giveBone(sessionName):
            srv_log('bone given to ' + str(sessionName))
            self.sessions[sessionName].watchdog.cancel()
            self.sessions[sessionName].watchdog = reactor.callLater(self.hunger, self.closeSession, sessionName, False)

            return self.hunger;

        @inlineCallbacks
        def querySession(sessionName, sql):
            res =  yield self.sessions[sessionName].threadedWampQuery(sql)
            return res
  
            
        yield self.register(createSession, u'com.mysql.console.requestSession')
        yield self.register(self.closeSession, u'com.mysql.console.closeSession')
        yield self.register(giveBone, u'com.mysql.console.giveBone')
        yield self.register(querySession, u'com.mysql.console.query')
        
        srv_log('request session registered')

        

if __name__ == '__main__':
    srv_log('running as main')

    srv_log('connecting to mariadb...')
    Server.rootConn = mariadb.connect(user='root', password='skunkskunk2', 
      database='food_account_data')

    srv_log('mariadb connected.')

    serverRunner = ApplicationRunner(u'ws://localhost:8081/ws', u'realm1')
    d = serverRunner.run(Server, False)
    d.addErrback(srv_log)

    reactor.run()
    
    srv_log('server proc ending')

