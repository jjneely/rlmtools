#!/usr/bin/python

################
# Query all the clients via XMLRPC
# Tell each one with a UUID to reload/parse its web-kickstart
################

import xmlrpclib
import socket
import httplib
import urllib2
import sys

def doRPC(method, apiVersion, *params):
    "Return the xmlrpc opject we want."

    # Apply API versioning
    params = list(params)
    params.insert(0, apiVersion)

    for i in range(5):
        try:
            return apply(method, params)
        except xmlrpclib.Error, e:
            print "XMLRPC Error: " + str(e)
        except socket.error, e:
            print "Socket Error: %s" % str(e)
        except socket.sslerror, e:
            print "Socket SSL Error: %s" % str(e)
        except AssertionError, e:
            print "Assertion Error (this is weird): %s" % str(e)
        except httplib.IncompleteRead, e:
            print "HTTP library reported an Incomplete Read error: %s" % str(e)
        except urllib2.HTTPError, e:
            msg = "\nAn HTTP error occurred:\n"
            msg = msg + "URL: %s\n" % e.filename
            msg = msg + "Status Code: %s\n" % e.code
            msg = msg + "Error Message: %s\n" % e.msg
            print msg

        if i < 5:
            print "Retrying in %s seconds" % (i+1)**2
            time.sleep((i+1)**2)
        
    raise StandardError("Can not initiate XMLRPC protocol to %s" % __serverURL)


def main():
    if len(sys.argv) != 3:
        print "Useage: %s XMLRPC-URL SECRET" % sys.argv[0]
        sys.exit(1)

    url = sys.argv[1]
    secret = sys.argv[2]
    server = xmlrpclib.ServerProxy(url)

    dump = doRPC(server.dumpClients, 2, secret)
    if not isinstance(dump, list):
        print "ERROR: dumpClients API call returned %s" % dump
        sys.exit(1)

    for c in dump[1]:
        if c['uuid'] == "":
            # Old client, nothing we can do to identify it acurately
            continue

        ret = doRPC(server.loadWebKickstart, 2, secret, c['uuid'])
        if ret > 0:
            print "WARNING: loadWebKickstart API call returned %s for %s" \
                    % (ret, c['hostname'])

    print "Done!"

if __name__ == "__main__":
    main()

