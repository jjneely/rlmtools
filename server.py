#!/usr/bin/python
#
#     RealmLinux Manager -- Main server object
#     Copyright (C) 2003 NC State University
#     Written by Jack Neely <jjneely@pams.ncsu.edu>
#
#     SDG
#
#     This program is free software; you can redistribute it and/or modify
#     it under the terms of the GNU General Public License as published by
#     the Free Software Foundation; either version 2 of the License, or
#     (at your option) any later version.
#
#     This program is distributed in the hope that it will be useful,
#     but WITHOUT ANY WARRANTY; without even the implied warranty of
#     MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#     GNU General Public License for more details.
#
#     You should have received a copy of the GNU General Public License
#     along with this program; if not, write to the Free Software
#     Foundation, Inc., 675 Mass Ave, Cambridge, MA 02139, USA.

import sys

sys.path.append("/afs/eos/project/realmlinux/py-modules")

import MySQLdb
import ezPyCrypto
import ConfigParser
import os
import time
import string

testmode = 0

if testmode:
    configFile = "/home/slack/projects/tmp/keys/testing.conf"
    sys.path.append("/home/slack/projects/solaris2ks")
else:
    configFile = "/afs/eos/www/linux/configs/web-kickstart.conf"
    sys.path.append("/afs/eos/www/linux/web-kickstart")

from webKickstart import webKickstart

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
		
        self.dbhost = cnf.get('db', 'host')
        self.dbuser = cnf.get('db', 'user')
        self.dbpasswd = cnf.get('db', 'passwd')
        self.db = cnf.get('db', 'db')

        # Other config information
        self.jumpstarts = cnf.get('main', 'jumpstarts')
        self.defaultKey = cnf.get('main', 'defaultkey')
        self.privateKey = cnf.get('main', 'privatekey')
        self.publicKey = cnf.get('main', 'publickey')
        
        # Open a MySQL connection and cursor
        self.conn = MySQLdb.connect(host=self.dbhost, user=self.dbuser,
                                    passwd=self.dbpasswd, db=self.db)
        self.cursor = self.conn.cursor()
        
    
    def __del__(self):
        """Destructor.  Clean up MySQL connection."""
        
        self.cursor.close()
        self.conn.commit()
        self.conn.close()
        
        
    def verifyClient(self, publicKey, sig):
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
    
    
    def isRegistered(self):
        """Returns a clients public key if this client is registered.  
           Otherwise None is returned."""
        
        self.cursor.execute("""select publickey from realmlinux where
            hostname = %s and recvdkey = 1""", (self.client,))
        if self.cursor.rowcount > 0:
            return self.cursor.fetchone()[0]
        else:
            return None
    
    
    def register(self, publicKey, dept, version):
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

        # Check the Time window for 24 hours
        row = self.cursor.fetchone()
        #if time.time() - row[1].ticks() > 86400:
            # Install date was more than 24 hours ago
            #return 3
        
        # let's register the client
        ts = time.localtime()
        date = MySQLdb.Timestamp(ts[0], ts[1], ts[2], ts[3], ts[4], ts[5])

        try:
            self.cursor.execute("""update realmlinux 
               set recvdkey=1, publickey=%s, lastcheck=%s, dept=%s, version=%s
               where hostname=%s""", (publicKey, date, dept, version, 
               self.client))
        except MySQLdb.Warning, e:
            # What's this about?
            fd = open("/tmp/mysql.warnings", "a")
            fd.write("MySQL Waring: %s\n" % str(e))
            fd.close()

        return 0
    
    
    def declineSupport(self):
        """Workstation has declined support.  Modify DB as appropiate."""
        
        # This workstation has declined support.  It may not have a key
        # that we know of so there's not much security here.
        
        # This function is insecure...too inseucre
        assert 0 == 1

        self.cursor.execute("""delete from realmlinux where 
            hostname=%s""", (self.client,))
    
    
    def checkIn(self, publicKey, sig):
        """Workstation checking in.  Update status in DB."""
        
        ts = time.localtime()
        date = MySQLdb.Timestamp(ts[0], ts[1], ts[2], ts[3], ts[4], ts[5])

        if self.verifyClient(publicKey, sig):
            self.cursor.execute("""update realmlinux
               set lastcheck=%s where hostname=%s""", (date, self.client))
        else:
            return 1

        return 0
    

    def __makeUpdatesConf(self):
        """Generate the updates.conf file and return a string."""

        # Okay...get the file and return it
        # get a bogus webKickstart instance
        # must also make CWD sane for webKickstart
        os.chdir(sys.path[-1])
        wks = webKickstart("fakeurl", {})
        sc = wks.findFile(self.client, self.jumpstarts)
        if sc == None:
            raise Exception("No config for %s in %s" % (self.client,
                                                        self.jumpstarts))
        try:
            ks = wks.cfg.get_obj(sc.getVersion(), {'url': "fakeurl", 'sc': sc})
        except KeyError, e:
            # Unsupported version key in config file
            ks = wks.cfg.get_obj('default', {'url': "fakeurl", 'sc': sc})

        data = ks.getKeys('users')
        if len(data) == 0:
            usersdata = "users default %s" % self.defaultKey
        else:
            # a list of the options passed to the 'users' key
            args = data[0]['options']
            usersdata = "users " + string.join(args)
        
        # root data
        data = ks.getKeys('root')
        if len(data) == 0:
            rootdata = "root default %s" % self.defaultKey
        else:
            args = data[0]['options']
            rootdata = "root " + string.join(args)

        # clusters
        data = ks.getKeys('cluster')
        clusterdata = ""
        if len(data) > 0:
            for row in data:
                clusterdata = "%scluster %s\n" % (clusterdata, 
                    string.join(row['options']))

        return "%s\n%s\n%s" % (usersdata, rootdata, clusterdata)

    def getEncKeyFile(self, publicKey, sig):
        """Returns an ecrypted string containing what should go in 
           /etc/update.conf on the workstation."""
        
        if not self.verifyClient(publicKey, sig):
            # Can't return None
            return []

        filedata = self.__makeUpdatesConf()
        
        # Now we encrypt and sign it
        trustedKey = self.isRegistered()
        if trustedKey == None:
            # WTF?  Not registered?
            return [] 
        client = ezPyCrypto.key()
        client.importKey(trustedKey)
        enc = client.encStringToAscii(filedata)
		
        # Get the RK key to sign with
        fd = open(self.privateKey)
        server = ezPyCrypto.key(fd.read())
        fd.close()
        sig = server.signString(enc)

        ret = [enc, sig]

        return ret
        
