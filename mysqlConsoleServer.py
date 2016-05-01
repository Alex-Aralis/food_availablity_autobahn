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
import ujson
import json


from Crypto.Cipher import AES

unpad = lambda b : b[0:-b[-1]]


class SessionThread:
    def __init__(self, wampAppSess, timeout, **kwargs):
        
        self.log('initing new session')

        self.log('initing new session with' + str(kwargs))
        self.conn = mariadb.connect(**kwargs)
        self.log('conn initialized')

        self.log('initing with timeout=' + str(timeout))
        self.timeout = timeout
        self.wampAppSess = wampAppSess

        self.log('setting watchdog')
        self.watchdog = reactor.callLater(timeout, self.cleanup, True)
        self.log('init complete')

    def log(self, msg):
        try:
            print('[session ' + str(self.conn.connection_id) + '] ' + str(msg))
        except Exception: 
            print('[session ?] ' + str(msg))
        
    def wampQuery(self, sql):
        self.log('wamp query recieved: ' + str(sql));

        resDict =  {}

        try:
            cursor = self.conn.cursor(buffered=True)

            cursor.execute(sql)
 

            resDict['columnNames'] = cursor.column_names
            resDict['warnings'] = cursor.fetchwarnings()
            resDict['rows'] = cursor.fetchall()
 
            cursor.close()

        except mariadb.errors.ProgrammingError as e:
            self.log(e)
            resDict['error'] = str(e)
        except Exception as e:
            self.log(e)
            resDict['error'] = str(e)
        finally:
            self.log('json encoding')
            jsons = ujson.dumps(resDict)
            self.log('returning result')
            return jsons
        
    def threadedWampQuery(self, sql):
        self.log('threaded query request recieved')
        return threads.deferToThread(self.wampQuery, sql)
        self.log('query thread spun')

    def cleanup(self, Timedout):
        self.log('cleanup entered')

        if not Timedout: 
            self.watchdog.cancel()

        try:
            self.conn.disconnect()
            self.log('disconnected from mysql server')
            return 0
        except Exception as e:
            self.log('disconnect failed, attempting shutdown')
            sess.conn.shutdown()
            return 1


class Server(ApplicationSession):
    sessions = {}
    hunger = 30;

    def log(self, msg):
        try:
            print('[server ' + str(self.rootConn.connection_id) + '] ' + str(msg))
        except Exception:
            print('[server ?] ' + str(msg))

    def padder(self, func, msg):
        def padded(*argv, **kwargs):
            try:
                return func(*argv, **kwargs)
            except Exception as e:
                self.log(msg)
                self.log(str(e))

        return padded

    def closeSession(self, sessionName, timedout=True):
        self.log('closing session ' + str(sessionName))
        self.log('current sessions ' + str(self.sessions))
        try:
            self.sessions[sessionName].cleanup(timedout)

            del self.sessions[sessionName]

            return 'session '+str(sessionName)+' closed'
        except Exception as e:
            self.log('error closing ' + str(sessionName))
            self.log(str(e))
            return 'error closing session:' + str(e)

    @inlineCallbacks
    def onJoin(self, details):
        self.log('server joined')


        def createSession(accountSessionId, accountSessionEncPW):
            self.log('session requested')
            self.log('accountSessionId: ' + str(int(accountSessionId)));
            
            self.log(self.rootConn.reconnect())

            try:
                rootCursor = self.rootConn.cursor(buffered=True)
            except mariadb.errors.OperationalError as e:
                self.log('rootConn failed to create cursor.')
                self.log(e)
                self.log('attempting reconnect with mysql server...') 
                self.log(self.rootConn.reconnect())
                rootCursor = self.rootConn.cursor(buffered=True)
            
            rootCursor.execute("SELECT user_name, pw_enc_key, iv FROM account_sessions WHERE id=%s", 
                                  (accountSessionId,))

            accountUserName, pwEncKey, iv = rootCursor.fetchone()
            
            cipher = AES.new(bytes(pwEncKey), AES.MODE_CBC, bytes(iv))

            plaintextPw = unpad(cipher.decrypt(base64.b64decode(accountSessionEncPW))).decode()
            
            self.log(accountUserName + ": " + plaintextPw);
           
            sess = SessionThread(self, self.hunger, user=accountUserName,  
                password=plaintextPw, use_pure=False)
             
          
            self.sessions[sess.conn.connection_id] = sess 

           
            self.log('new SessionThread called: ' + str(sess.conn.connection_id))


            return sess.conn.connection_id;



        def giveBone(sessionName):
            self.log('bone given to ' + str(sessionName))
            if (sessionName in self.sessions):
                self.sessions[sessionName].watchdog.cancel()
                self.sessions[sessionName].watchdog = reactor.callLater(self.hunger, self.closeSession, sessionName, True)
                return self.hunger;
            else:
                self.log('unknown name refused bone');
                return -1;

        @inlineCallbacks
        def querySession(sessionName, sql):
            d = self.sessions[sessionName].threadedWampQuery(sql)
            d.addErrback(self.log)
            res =  yield d
            return res
  
            
        yield self.register(self.padder(createSession,'Session creation failed!!!'), 
          u'com.mysql.console.requestSession')
        yield self.register(self.padder(self.closeSession, 'Session closing failed!!!'),
          u'com.mysql.console.closeSession')
        yield self.register(self.padder(giveBone, 'Session give bone failed!!!'), 
          u'com.mysql.console.giveBone')
        yield self.register(querySession, 
          u'com.mysql.console.query')
        
        self.log('request session registered')

        

if __name__ == '__main__':
    print('running as main')

    print('connecting to mariadb...')
    Server.rootConn = mariadb.connect(user='root', password='skunkskunk2', 
      database='food_account_data', use_pure=False)

    print('root connected to mariadb.')

    serverRunner = ApplicationRunner(u'ws://localhost:8081/ws', u'realm1')
    d = serverRunner.run(Server, False)
    d.addErrback(print)

    reactor.run()
    
    print('server proc ending')

