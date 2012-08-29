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
import base64
import ezPyCrypto
import random

from rlmtools.constants import defaultConfFiles
from rlmtools import configDragon
from rlmtools import miscServer

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
        self.misc = miscServer.MiscServer()

        # Imitate a RL machine
        self.location = tempfile.mkdtemp(prefix="LD")
        self.uuid = getUUID(self.location)
        print "\nImitating machine from %s, UUID = %s" \
                % (self.location, self.uuid)

    def tearDown(self):
        # Remove UUID from RLMTools database if present
        host_id = self.misc.getUuidID(self.uuid)
        self.misc.deleteClient(host_id)

        # Remove UUID and keys representing fake host
        os.system("rm -rf %s" % self.location)

    def getDept(self):
        host_id = self.misc.getUuidID(self.uuid)
        if host_id is None:
            return None
        else:
            dept_id = self.misc.getHostDept(host_id)
            return self.misc.getDeptName(dept_id)

    def test000HelloWorld(self):
        i = doRPC(self.server.hello, 1)
        self.assertEqual("Hello World", i)

    def test110SupportedHost(self):
        secret = configDragon.ConfigDragon().secret
        fqdn = doRPC(self.server.getAddress, 1)[1]
        print "APIv1 Support FQDN: %s" % fqdn

        print "initHost()..."
        i = doRPC(self.server.initHost, 1, secret, fqdn)
        self.assertEqual(i, 0)

        print "isRegistered()..."
        i = doRPC(self.server.isRegistered, 1, self.uuid, "")
        self.assertFalse(i)

        print "register()..."
        key = getLocalKey(self.location)
        sig = key.signString(self.uuid)
        i = doRPC(self.server.register, 1, key.exportKey(), "test-dept", 
                  "test-version", self.uuid, -1)
        self.assertEqual(i, 0)

        print "isRegistered()..."
        i = doRPC(self.server.isRegistered, 1, self.uuid, sig)
        self.assertTrue(i)

        print "isSupported()..."
        i = doRPC(self.server.isSupported, 1, self.uuid)
        self.assertTrue(i)

        print "checkIn()..."
        i = doRPC(self.server.checkIn, 1, self.uuid, sig)
        self.assertEqual(i, 0)

        print "message()..."
        m = {}
        m['type'] = 'boot'
        m['success'] = True
        m['timestamp'] = time.time()
        m['data'] = base64.encodestring("")
        i = doRPC(self.server.message, 1, self.uuid, sig, m)
        self.assertEqual(i, 0)

        print "updateRHNSystemID()..."
        r = random.randint(0, 65535)
        i = doRPC(self.server.updateRHNSystemID, 1, self.uuid, sig, r)
        self.assertEqual(i, 0)

        print "getServerKey()..."
        i = doRPC(self.server.getServerKey, 1, self.uuid)
        self.assertTrue(len(i) == 993) # Textual length of pubkey
        rlPub = ezPyCrypto.key()
        rlPub.importKey(i)

        print "getEncKeyFile()..."
        i = doRPC(self.server.getEncKeyFile, 1, self.uuid, sig)
        self.assertFalse(i == [])
        self.assertTrue(rlPub.verifyString(i[0], i[1]))
        blob = key.decStringFromAscii(i[0])

        print "dept check..."
        # Dept should be "ncsu"
        self.assertTrue("ncsu" == self.getDept())
        
    def test120SupportedHost(self):
        secret = configDragon.ConfigDragon().secret
        fqdn = doRPC(self.server.getAddress, 2)[1]
        print "APIv2 Support FQDN: %s" % fqdn

        print "initHost()..."
        ret, sid = doRPC(self.server.initHost, 2, secret, fqdn, "test-dept")
        self.assertEqual(ret, 0)
        self.assertTrue(type(sid) == type(""))

        print "isRegistered()..."
        i = doRPC(self.server.isRegistered, 2, self.uuid, "")
        self.assertFalse(i)

        print "register()..."
        key = getLocalKey(self.location)
        sig = key.signString(self.uuid)
        i = doRPC(self.server.register, 2, key.exportKey(), "test-dept", 
                  "test-version", self.uuid, -1, sid)
        self.assertEqual(i, 0)

        print "isRegistered()..."
        i = doRPC(self.server.isRegistered, 2, self.uuid, sig)
        self.assertTrue(i)

        print "isSupported()..."
        i = doRPC(self.server.isSupported, 2, self.uuid)
        self.assertTrue(i)

        print "checkIn()..."
        i = doRPC(self.server.checkIn, 2, self.uuid, sig, "test-dept")
        self.assertEqual(i, 0)

        print "message()..."
        m = {}
        m['type'] = 'boot'
        m['success'] = True
        m['timestamp'] = time.time()
        m['data'] = base64.encodestring("")
        i = doRPC(self.server.message, 2, self.uuid, sig, m)
        self.assertEqual(i, 0)

        print "updateRHNSystemID()..."
        r = random.randint(0, 65535)
        i = doRPC(self.server.updateRHNSystemID, 2, self.uuid, sig, r)
        self.assertEqual(i, 0)

        print "getServerKey()..."
        i = doRPC(self.server.getServerKey, 2, self.uuid)
        self.assertTrue(len(i) == 993) # Textual length of pubkey
        rlPub = ezPyCrypto.key()
        rlPub.importKey(i)

        print "getEncKeyFile()..."
        i = doRPC(self.server.getEncKeyFile, 2, self.uuid, sig)
        self.assertFalse(i == [])
        self.assertTrue(rlPub.verifyString(i[0], i[1]))
        blob = key.decStringFromAscii(i[0])

        print "dept check..."
        # Dept should be "test-dept"
        self.assertTrue("test-dept" == self.getDept())
        
    def test115NoSupport(self):
        fqdn = doRPC(self.server.getAddress, 1)[1]
        print "APIv1 No Support FQDN: %s" % fqdn

        print "isRegistered()..."
        i = doRPC(self.server.isRegistered, 1, self.uuid, "")
        self.assertFalse(i)

        print "register()..."
        key = getLocalKey(self.location)
        sig = key.signString(self.uuid)
        i = doRPC(self.server.register, 1, key.exportKey(), "test-dept", 
                  "test-version", self.uuid, -1)
        self.assertEqual(i, 0)

        print "isRegistered()..."
        i = doRPC(self.server.isRegistered, 1, self.uuid, sig)
        self.assertTrue(i)

        print "isSupported()..."
        i = doRPC(self.server.isSupported, 1, self.uuid)
        self.assertFalse(i)

        print "getServerKey()..."
        i = doRPC(self.server.getServerKey, 1, self.uuid)
        self.assertTrue(len(i) == 993) # Textual length of pubkey
        rlPub = ezPyCrypto.key()
        rlPub.importKey(i)

        print "getEncKeyFile()..."
        i = doRPC(self.server.getEncKeyFile, 1, self.uuid, sig)
        self.assertTrue(i == [])

        print "dept check..."
        # Dept should be "ncsu"
        self.assertTrue("ncsu" == self.getDept())

    def test125NoSupport(self):
        fqdn = doRPC(self.server.getAddress, 2)[1]
        print "APIv2 No Support FQDN: %s" % fqdn

        print "isRegistered()..."
        i = doRPC(self.server.isRegistered, 2, self.uuid, "")
        self.assertFalse(i)

        print "register()..."
        key = getLocalKey(self.location)
        sig = key.signString(self.uuid)
        i = doRPC(self.server.register, 2, key.exportKey(), "test-dept", 
                  "test-version", self.uuid, -1)
        self.assertEqual(i, 0)

        print "isRegistered()..."
        i = doRPC(self.server.isRegistered, 2, self.uuid, sig)
        self.assertTrue(i)

        print "isSupported()..."
        i = doRPC(self.server.isSupported, 2, self.uuid)
        self.assertFalse(i)

        print "getServerKey()..."
        i = doRPC(self.server.getServerKey, 2, self.uuid)
        self.assertTrue(len(i) == 993) # Textual length of pubkey
        rlPub = ezPyCrypto.key()
        rlPub.importKey(i)

        print "getEncKeyFile()..."
        i = doRPC(self.server.getEncKeyFile, 2, self.uuid, sig)
        self.assertTrue(i == [])

        print "dept check..."
        # Dept should be "ncsu"
        self.assertTrue("ncsu" == self.getDept())

    def test200SecretOps(self):
        secret = configDragon.ConfigDragon().secret
        dump = doRPC(self.server.dumpClients, 2, secret)
        self.assertTrue(isinstance(dump, list))

        client = None
        i = 0
        for c in dump[1]:
            print "Loading Web-Kickstart for %s" % c['hostname']
            if c['uuid'] != "":
                ret = doRPC(self.server.loadWebKickstart, 2, secret, c['uuid'])
                print ret
                if ret == 3:
                    print "Client %s does not have a web-kickstart config" \
                            % c['hostname']
                self.assertTrue(ret == 0 or ret == 3)
                i = i + 1
                if i > 10:
                    break
                
    def test220Bcfg2Opts(self):
        fqdn = doRPC(self.server.getAddress, 2)[1]
        print "APIv2 Support FQDN: %s" % fqdn

        secret = configDragon.ConfigDragon().secret

        key = getLocalKey(self.location)
        sig = key.signString(self.uuid)
        url = "http://foobar.com:8072"
        init = "-S %(url)s -x %(password)s -n -qv"
        ret = doRPC(self.server.setDeptBcfg2, 2, secret, "root",
                init, url)
        self.assertTrue(ret == 0)

        print "initHost()..."
        ret, sid = doRPC(self.server.initHost, 2, secret, fqdn)
        self.assertEqual(ret, 0)
        self.assertTrue(type(sid) == type(""))

        print "isRegistered()..."
        i = doRPC(self.server.isRegistered, 2, self.uuid, "")
        self.assertFalse(i)

        print "register()..."
        i = doRPC(self.server.register, 2, key.exportKey(), "test-dept", 
                  "test-version", self.uuid, -1, sid)
        self.assertEqual(i, 0)

        print "getBcfg2Bootstrap()..."
        ret = doRPC(self.server.getBcfg2Bootstrap, 2, self.uuid, sig)
        print ret
        self.assertTrue(ret[0] == 0)


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

