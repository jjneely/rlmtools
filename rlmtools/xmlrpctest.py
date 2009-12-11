import cherrypy
import optparse
import configDragon

from constants import defaultConfFiles

class XMLRPCTest(object):
    # Test Harness for XMLRPC calls

    def __init__(self):
        import API

        for method in API.__API__:
            # Setup the object...
            setattr(self, method, getattr(API, method))
            # Set the exposed flag
            setattr(getattr(self, method), 'exposed', True)

def main():
    parser = optparse.OptionParser()
    parser.add_option("-C", "--configfile", action="store",
                      default=defaultConfFiles,
                      dest="configfile",
                      help="Configuration file")
    (options, args) = parser.parse_args()

    # Start up configuration/logging/databases
    configDragon.initConfig(options.configfile)

    cherrypy.root = XMLRPCTest()
    cherrypy.config.update({'xmlrpc_filter.on': True,
                            'server.socket_port': 8081,
                            'server.thread_pool':10,
                            'server.socket_queue_size':10 
                            })

    cherrypy.server.start()

if __name__ == "__main__":
    main()

