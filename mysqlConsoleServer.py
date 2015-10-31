import time
from subprocess import Popen
from twisted.internet.defer import inlineCallbacks
from twisted.internet import reactor, task
from autobahn.twisted.util import sleep
from autobahn.twisted.wamp import ApplicationSession, ApplicationRunner

def srv_log(msg):
    print('[server] ' + msg)

class Server(ApplicationSession):
    sessions = {}
    @inlineCallbacks
    def onJoin(self, details):
        srv_log('server joined')

        def createSession():
            global sessionCount
            srv_log('session requested')
            creation = str(int(time.time()*1000))
            self.sessions[creation] = Popen(['python','mysqlConsoleSession.py', creation])

#            def monitor():
#                if not (newP.poll() is None) :
#                    srv_log('waiting for subproc to exit: ' + str(newP.poll()))
#                    l.stop() 
#                    newP.wait()
#                    newP.terminate()

#            l = task.LoopingCall(monitor)
#            l.start(1)
            srv_log('mysqlConsoleSession.py called: ' + creation)
            return creation

        def closeSession(sessionName):
            self.sessions[sessionName].terminate()
            return 'session '+sessionName+' closed'

        yield self.register(createSession, u'com.mysql.console.requestSession')
        yield self.register(closeSession, u'com.mysql.console.closeSession')
#        except Exception  as e:
#            srv_log(str(e))
#            srv_log('it didnt work')

        srv_log('request session registered')
        

if __name__ == '__main__':
    srv_log('running as main')
    serverRunner = ApplicationRunner(u'ws://localhost:8081/ws', u'realm1')
    serverRunner.run(Server)

