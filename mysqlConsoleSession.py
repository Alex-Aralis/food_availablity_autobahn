import sys
import signal
import os
from twisted.internet.defer import inlineCallbacks
from twisted.internet import reactor, task
from autobahn.twisted.util import sleep
from autobahn.twisted.wamp import ApplicationSession, ApplicationRunner
from autobahn.wamp.exception import ApplicationError
def sess_log(msg):
    print("[pid:" + str(os.getpid()) + " session:" + sys.argv[1] + "]: " + str(msg))

class mysqlSession(ApplicationSession):
    @inlineCallbacks
    def onJoin(self, details):
        sess_log('mysqlSession has joined')

        def repeat(msg):
            sess_log(msg)
            return msg

        def closeSession():
            sess_log('session exiting')
            self.l.stop()
            #reactor.stop()
            #d.cancel() 
            #reactor.stop()
            os.kill(os.getpid(), signal.SIGTERM)
            #sys.exit(32)
            sess_log('printed after int')
            
        @inlineCallbacks
        def ping():
            watchdog = reactor.callLater(2, closeSession)
            try:
                yield self.call(u'com.mysql.console.pong.' + sys.argv[1])
                watchdog.cancel()
            except ApplicationError:
                sess_log('pong not found!!!')
                watchdog.cancel()
                closeSession()
            
        
        sess_log('registering rpc query and close')
        yield self.register(repeat, u'com.mysql.console.query.' + sys.argv[1])
        yield self.register(closeSession , u'com.mysql.console.close.' + sys.argv[1])
        sess_log('rpcs registered')
        
        self.l = task.LoopingCall(ping)
        self.l.start(2) 

    def onLeave(self, details):
        sess_log('Leaving: ' + str(details)) 
            
    def onDisconnect(self):
        sess_log('Disconnecting: ');
        
if __name__ == '__main__':
    sess_log('running as main')
    runner = ApplicationRunner(u'ws://localhost:8081/ws', u'realm1')
    d = runner.run(mysqlSession, False)
    d.addErrback(sess_log)
    reactor.run()
    sess_log('process ending')
