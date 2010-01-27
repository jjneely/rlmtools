#!/usr/bin/python
#
# testXMLRPC.py -- unit tests for the XMLRPC interface for LD
# Copyright (C) 2010 NC State University
# Written by Jack Neely <jjneely@ncsu.edu>
#
# SDG
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 675 Mass Ave, Cambridge, MA 02139, USA.

import unittest
import socket
import httplib
import urllib2
import xmlrpclib
import time
import optparse

from rlmtools.constants import defaultConfFiles
from rlmtools import configDragon

__serverURL = None

def setupServer(URL):
    global __serverURL
    __serverURL = URL

    return xmlrpclib.ServerProxy(__serverURL)

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

class TestLiquidDragonXMLRPC(unittest.TestCase):

    def setUp(self):
        URL = "http://localhost:8081"
        self.server = setupServer(URL)

    def test000HelloWorld(self):
        i = doRPC(self.server.hello, 1)
        self.assertEqual("Hello World", i)

    def test100InitHost(self):
        secret = configDragon.ConfigDragon().secret
        i = doRPC(self.server.initHost, 1, secret, "fqdn.example.net")
        self.assertEqual(i, 0)

        i = doRPC(self.server.isRegistered, 1, "fqdn.example.net", "")
        self.assertFalse(i)


if __name__ == "__main__":
    # access to server configuration so we can find the "secret"
    parser = optparse.OptionParser()
    parser.add_option("-C", "--configfile", action="store",
                      default=defaultConfFiles,
                      dest="configfile",
                      help="Configuration file")
    (options, args) = parser.parse_args()
    configDragon.initConfig(options.configfile)

    # Start the tests
    unittest.main()

