import sys
import signal
import os
import mysql.connector as mariadb
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

        sess_log('made by user ' + sys.argv[2] + ' identified by ' + sys.argv[3])

        def repeat(msg):
            sess_log(msg)
            return msg
            
        def query(sql):
            
            try:
                cursor = self.conn.cursor(buffered=True)

                cursor.execute(sql)
            
                result = ''
                for row in cursor:
                    result += str(row) + '<br>'

                cursor.close()

                return result;

            except mariadb.errors.ProgrammingError as e:
                sess_log(e)
                return str(e)

        sess_log('registering rpc query and close')
        yield self.register(query, u'com.mysql.console.query.' + sys.argv[1])
        sess_log('rpcs registered')
        #need to tell Server session is ready here <---
        
if __name__ == '__main__':
    sess_log('running as main')

    sess_log('creating mariadb connection')
    mysqlSession.conn = mariadb.connect(user=sys.argv[2], password=sys.argv[3], database='food_account_data')
    #mysqlSession.cursor = mysqlSession.conn.cursor(buffered=True)
    sess_log('mariadb connection made')

    runner = ApplicationRunner(u'ws://localhost:8081/ws', u'realm1')
    runner.run(mysqlSession)
    #d.addErrback(sess_log)
    #reactor.run()
    sess_log('process ending')
