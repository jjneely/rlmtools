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
import os
import os.path
import tempfile
import ezPyCrypto

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

def getUUID(location):
    cmd = "/usr/bin/uuidgen -t"
    uuidFile = os.path.join(location, "uuid")
    if not os.path.exists(uuidFile):
        fd = os.popen(cmd)
        uuid = fd.read().strip()
        fd.close()
        try:
            fd = open(uuidFile, 'w')
            fd.write(uuid + '\n')
            fd.close()
            os.chmod(uuidFile, 0644)
        except IOError:
            # We are not root!
            return None
    else:
        fd = open(uuidFile)
        uuid = fd.read().strip()
        fd.close()

    return uuid

def saveKey(location, key):
    # make sure the key is written to disk
    publicKey = os.path.join(location, "rkhost.pub")
    privateKey = os.path.join(location, "rkhost.priv")

    if not os.path.exists(publicKey):
        pubKey = key.exportKey()
        privKey = key.exportKeyPrivate()
        
        fd = open(publicKey, "w")
        fd.write(pubKey)
        fd.close()
        os.chmod(publicKey, 0644)

        fd = open(privateKey, "w")
        fd.write(privKey)
        fd.close()
        os.chmod(privateKey, 0600)

def getLocalKey(location):
    "Return an ezPyCrypto keypair for this local host."
    privateKey = os.path.join(location, "rkhost.priv")

    if not os.access(privateKey, os.R_OK):
        key = ezPyCrypto.key(1024)
        saveKey(location, key)
    else: 
        # Check bits
        mode = os.stat(publicKey).st_mode
        if not stat.S_IMODE(mode) == 0644:
            os.chmod(publicKey, 0644)
        mode = os.stat(privateKey).st_mode
        if not stat.S_IMODE(mode) == 0600:
            os.chmod(publicKey, 0600)

        fd = open(privateKey)
        privKeyText = fd.read()
        fd.close()

        key = ezPyCrypto.key()
        key.importKey(privKeyText)

    return key
    
class TestLiquidDragonXMLRPC(unittest.TestCase):

    def setUp(self):
        URL = "http://localhost:8081"
        self.server = setupServer(URL)

        # Imitate a RL machine
        self.location = tempfile.mkdtemp(prefix="rlmtoolstest")
        self.uuid = getUUID(self.location)
        print "Imitating machine from %s, UUID = %s" \
                % (self.location, self.uuid)

    def tearDown(self):
        os.system("rm -rf %s" % self.location)

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

