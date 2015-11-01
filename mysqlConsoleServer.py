import time
import signal
from subprocess import Popen
from twisted.internet.defer import inlineCallbacks
from twisted.internet import reactor, task
from autobahn.twisted.util import sleep
from autobahn.twisted.wamp import ApplicationSession, ApplicationRunner

def srv_log(msg):
    print('[server] ' + msg)

class Server(ApplicationSession):
    sessions = {}
    watchdogs = {}
    hunger = 5;

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

        def createSession():
            srv_log('session requested')
            creation = str(int(time.time()*1000))
            self.sessions[creation] = Popen(['python','mysqlConsoleSession.py', creation])
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
    serverRunner = ApplicationRunner(u'ws://localhost:8081/ws', u'realm1')
    serverRunner.run(Server)

