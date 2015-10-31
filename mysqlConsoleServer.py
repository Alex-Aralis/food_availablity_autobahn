import time
from subprocess import Popen
from twisted.internet.defer import inlineCallbacks
from twisted.internet import reactor
from autobahn.twisted.util import sleep
from autobahn.twisted.wamp import ApplicationSession, ApplicationRunner

def srv_log(msg):
    print('[server] ' + msg)

class Server(ApplicationSession):

    @inlineCallbacks
    def onJoin(self, details):
        srv_log('server joined')
   
        def createSession():
            global sessionCount
            srv_log('session requested')
            creation = str(int(time.time()*1000))
            Popen(['python','mysqlConsoleSession.py', creation])
            srv_log('mysqlConsoleSession.py called: ' + creation)
            return creation

#        def meep(msg):
#            srv_log(msg)
#        try:
        yield self.register(createSession, u'com.mysql.console.requestSession')
#        except Exception  as e:
#            srv_log(str(e))
#            srv_log('it didnt work')

        srv_log('request session registered')
        

if __name__ == '__main__':
    srv_log('running as main')
    serverRunner = ApplicationRunner(u'ws://localhost:8081/ws', u'realm1')
    serverRunner.run(Server)

