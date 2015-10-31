import sys
import signal
import os
from twisted.internet.defer import inlineCallbacks
from twisted.internet import reactor, task
from autobahn.twisted.util import sleep
from autobahn.twisted.wamp import ApplicationSession, ApplicationRunner
from autobahn.wamp.exception import ApplicationError
def sess_log(msg):
    print("[session " + sys.argv[1] + "]: " + msg)

class mysqlSession(ApplicationSession):
    @inlineCallbacks
    def onJoin(self, details):
        sess_log(' mysqlSession has joined')

        def repeat(msg):
            sess_log(msg)
            return msg

        def closeSession():
            sess_log('session exiting')
            reactor.stop()
            
        @inlineCallbacks
        def ping():
            watchdog = reactor.callLater(2, closeSession)
            try:
                yield self.call(u'com.mysql.console.pong.' + sys.argv[1])
            except ApplicationError:
                sess_log('pong not found!!!')
                closeSession()
            
            watchdog.cancel()
        
        self.l = task.LoopingCall(ping)
        self.l.start(2)

        sess_log(' registering function query')
        yield self.register(repeat, u'com.mysql.console.query.' + sys.argv[1])
        yield self.register(closeSession , u'com.mysql.console.close.' + sys.argv[1])
        sess_log(' query registered')
     

    def onLeave(self, details):
        sess_log('Leaving: ' + str(details)) 
        self.l.stop()
        os.kill(os.getpid(), signal.SIGKILL)
            
if __name__ == '__main__':
    sess_log(' running as main')
    runner = ApplicationRunner(u'ws://localhost:8081/ws', u'realm1')
    runner.run(mysqlSession, False)
    reactor.run()
    sess_log('process ending')
