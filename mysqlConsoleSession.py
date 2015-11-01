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
            
#        @inlineCallbacks
#        def ping():
#            watchdog = reactor.callLater(2, closeSession)
#            try:
#                yield self.call(u'com.mysql.console.pong.' + sys.argv[1])
#                watchdog.cancel()
#            except ApplicationError:
#                sess_log('pong not found!!!')
#                watchdog.cancel()
#                closeSession()
            
        
        sess_log('registering rpc query and close')
        yield self.register(repeat, u'com.mysql.console.query.' + sys.argv[1])
        sess_log('rpcs registered')
        
#        self.l = task.LoopingCall(ping)
#        self.l.start(2) 

#    def onLeave(self, details):
#        sess_log('Leaving: ' + str(details)) 
            
#    def onDisconnect(self):
#        sess_log('Disconnecting: ');
        
if __name__ == '__main__':
    sess_log('running as main')
    runner = ApplicationRunner(u'ws://localhost:8081/ws', u'realm1')
    runner.run(mysqlSession)
    #d.addErrback(sess_log)
    #reactor.run()
    sess_log('process ending')
