#!/usr/bin/python

##     RealmLinux Manager -- Main server object
##     Copyright (C) 2003 NC State University
##     Written by Jack Neely <jjneely@pams.ncsu.edu>

##     This program is free software; you can redistribute it and/or modify
##     it under the terms of the GNU General Public License as published by
##     the Free Software Foundation; either version 2 of the License, or
##     (at your option) any later version.

##     This program is distributed in the hope that it will be useful,
##     but WITHOUT ANY WARRANTY; without even the implied warranty of
##     MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
##     GNU General Public License for more details.

##     You should have received a copy of the GNU General Public License
##     along with this program; if not, write to the Free Software
##     Foundation, Inc., 675 Mass Ave, Cambridge, MA 02139, USA.

import sys

sys.path.append("/afs/eos/project/realmlinux/py-modules")

import MySQLdb
import ezPyCrypto
import ConfigParser
import os
import time
import string

testmode = 1

if testmode:
    configFile = "/home/slack/projects/tmp/keys/testing.conf"
    pubKeyFile = "/home/slack/projects/tmp/keys/realmlinux.pub"
    privKeyFile = "/home/slack/projects/tmp/keys/realmlinux.priv"
    jumpstarts = "/home/slack/projects/solaris2ks/configs"
    sys.path.append("/home/slack/projects/solaris2ks")
else:
    configFile = "/afs/eos/www/linux/configs/web-kickstart.conf"
    pubKeyFile = "/afs/eos/www/linux/configs/keys/realmlinux.pub"
    privKeyFile = "/afs/eos/www/linux/configs/keys/realmlinux.priv"
    jumpstarts = "/afs/eos/www/linux/web-kickstart/configs"
    sys.path.append("/afs/eos/www/linux/web-kickstart")

from webKickstart import webKickstart
from baseKickstart import baseKickstart

def getFile(filename):
    """Helper function to return a file as a string"""
    
    fd = open(filename)
    s = fd.read()
    fd.close()
    return s
    

class Server(object):

    def __init__(self, client):
        """Set up server and define who we are talking to...well at least
           what we are told we are talking to."""
           
        self.client = client
        
        # get MySQL information
        global configFile
        cnf = ConfigParser.ConfigParser()
        cnf.read(configFile)
        self.dbhost = cnf.get('main', 'host')
        self.dbuser = cnf.get('main', 'user')
        self.dbpasswd = cnf.get('main', 'passwd')
        self.db = cnf.get('main', 'db')
        
        # Open a MySQL connection and cursor
        self.conn = MySQLdb.connect(host=self.dbhost, user=self.dbuser,
                                    passwd=self.dbpasswd, db=self.db)
        self.cursor = self.conn.cursor()
        
    
    def __del__(self):
        """Destructor.  Clean up MySQL connection."""
        
        self.cursor.close()
        self.conn.commit()
        self.conn.close()
        
        
    def verifyClientKey(publicKey, sig):
        """Make sure that the public key and sig match this client."""
        
        trustedKey = self.isRegistered()
        if trustedKey == None:
            # We are not registered bail!
            return 0
        
        k = ezPyCrypto.key(trustedKey)
        if k.verifyString(publicKey, sig):
            # the signature is good using our, trusted public key for
            # this client.  I don't really about the publicKey the client
            # sent
            return 1
        else:
            return 0
    
    
    def isRegistered():
        """Returns a clients public key if this client is registered.  
           Otherwise None is returned."""
        
        self.cursor.execute("""select publickey from realmlinux where
            hostname=%s and recvdkey=0""" % (self.client,))
        if self.cursor.rowcount > 0:
            return self.cursor.fetchone()[0]
        else:
            return None
    
    
    def register(publicKey, dept, version):
        """Workstation requests registration.  Check DB and register host as
           appropiate.  On success 0 is returned, otherwise a non-zero error
           code is returned."""
        
        # ok..we have no data for the client lets make sure our DB looks ok
        if self.isRegistered() != None:
            # What? Client is already registered?
            # The web-kickstart log should have unregistered this client
            # not registering
            return 1
        # check to see if client has been logged in DB
        self.cursor.execute("""select * from realmlinux where 
            hostname=%s""", (self.client,))
        if not self.cursor.rowcount > 0:
            # SQL query returned zero rows...this client isn't logged
            # to be registered
            return 2
        
        # let's register the client
        ts = time.localtime()
        date = MySQLdb.Timestamp(ts[0], ts[1], ts[2], ts[3], ts[4], ts[5])
        # XXX: insert time window check here
        self.cursor.execute("""update realmlinux 
            set recvdkey=1, publickey=%s, lastcheck=%s, dept=%s, version=%s
            where hostname=%s""", (publicKey, date, dept, version, 
            self.client))

        return 0
    
    
    def declineSupport():
        """Workstation has declined support.  Modify DB as appropiate."""
        
        # This workstation has declined support.  It may not have a key
        # that we know of so there's not much security here.
        
        # This function is insecure...too inseucre
        assert 0 == 1

        self.cursor.execute("""delete from realmlinux where 
            hostname=%s""", (self.client,))
    
    
    def checkIn(publicKey, sig):
        """Workstation checking in.  Update status in DB."""
        
        ts = time.localtime()
        date = MySQLdb.Timestamp(ts[0], ts[1], ts[2], ts[3], ts[4], ts[5])

        if self.verifyClient(publicKey, sig):
            self.cursor.execute("""update realmlinux
               set lastcheck=%s where hostname=%s""", (date, self.client))
        else:
            # ignore
            pass
    
    
    def getEncKeyFile(publicKey, sig):
        """Returns an ecrypted string containing what should go in 
           /etc/update.conf on the workstation."""
        
        if not self.verifyClient(publicKey, sig):
            return None

        # Okay...get the file and return it
        # get a bogus webKickstart instance
        wks = webKickstart("fakeurl", {})
        sc = wks.findFile(self.client, jumpstarts)
        ks = baseKickstart("fakeurl", sc)
        users = ks.getKeys('users')
        if len(users) == 0:
            filedata = "users default Wr1cRGN8EZ6CBcv3SaOSjwZ9tY14jV"
        else:
            # a list of the options passed to the 'users' key
            users_args = users[0]['options']
            filedata = "users " + string.join(users_args)
            
        # Now we encrypt and sign it
        k = ezPyCrypto.key(privKeyFile)
        enc = k.encryptStringiToAscii(filedata)
        sig = k.signString(enc)

        return (enc, sig)
        
