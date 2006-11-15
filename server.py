#!/usr/bin/python
#
# RealmLinux Manager -- Main server object
# Copyright (C) 2003, 2005, 2006 NC State University
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

import MySQLdb
import sys
import ezPyCrypto
import ConfigParser
import os
import os.path
import time
import logging
import traceback

from datetime import datetime, timedelta

import mysql

try:
    import debug
except ImportError:
    sys.path.append("/afs/unity/web/l/linux/web-kickstart")
else:
    sys.path.append("/home/slack/projects/solaris2ks")

import config
from webKickstart import webKickstart

log = logging.getLogger("xmlrpc")

def logException():
    # even though tracing is not normally done at lower logging levels,
    # we add trace data for exceptions
    file, line, func, txt = traceback.extract_stack(None, 2)[0]
    trace = 'EXCEPTION (File: %s, Method: %s(), Line: %s): [%s]\n' % \
            (file, func, line, txt)
    log.critical(trace)

    (type, value, tb) = sys.exc_info()
    for line in traceback.format_exception(type, value, tb):
        log.critical(line.strip())

def getDBDict():
    db = {}
    db['db_host'] = config.config.get('db', 'host')
    db['db_user'] = config.config.get('db', 'user')
    db['db_pass'] = config.config.get('db', 'passwd')
    db['db_name'] = config.config.get('db', 'db')
    
    return db

def getFile(filename):
    """Helper function to return a file as a string"""
    
    fd = open(filename)
    s = fd.read()
    fd.close()
    return s
    

class Server(object):

    # Use class variables so we don't have to connect each time
    conn = None
    cursor = None
    db = None

    # Other static data that can be class variables
    jumpstarts = None
    defaultKey = None
    privateKey = None
    publicKey = None
    rhnkey = None
    keypath = None

    def __init__(self, client):
        """Set up server and define who we are talking to...well at least
           what we are told we are talking to."""
           
        self.client = client
        self.hostid = None

        log.info("Running Server object for %s" % self.client)
        
        if self.conn == None or self.cursor == None:
            # get MySQL information
            db = getDBDict()
            self.db = mysql.MysqlDB(db)
            self.conn = self.db.getConnection()
            self.cursor = self.db.getCursor()

            # Other config information
            cnf = config.config
            self.jumpstarts = cnf.get('main', 'jumpstarts')
            self.defaultKey = cnf.get('main', 'defaultkey')
            self.privateKey = cnf.get('main', 'privatekey')
            self.publicKey = cnf.get('main', 'publickey')
            self.rhnkey = cnf.get('main', 'rhnkey')
            self.keypath = cnf.get('main', 'key_directory')

    def verifyClient(self, publicKey, sig):
        """Make sure that the public key and sig match this client."""
        
        trustedKey = self.isRegistered()
        if trustedKey == None:
            # We are not registered bail!
            return False
        
        k = ezPyCrypto.key(trustedKey)
        if k.verifyString(publicKey, sig):
            # the signature is good using our, trusted public key for
            # this client.  I don't really about the publicKey the client
            # sent
            return True
        else:
            return False
    
    def isSupported(self):
        """Return true/false if the support flag is set for this client."""
        
        q = """select host_id from realmlinux where host_id = %s and
               support = 1 and recvdkey = 1"""

        id = self.getHostID()
        if id == None:
            return False

        self.cursor.execute(q, (id,))
        return self.cursor.rowcount > 0

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
            log.info("Registered client %s attempted to re-register" \
                     % self.client)
            return 1
        # check to see if client has been logged in DB
        self.cursor.execute("""select installdate from realmlinux where 
            hostname=%s and support=1""", (self.client,))
        if not self.cursor.rowcount > 0:
            # SQL query returned zero rows...this client isn't logged
            # to be registered with support (old return code 2)
            return self.createNoSupport(publicKey, dept, version)

        # Check the Time window for 24 hours
        installDate = self.cursor.fetchone()[0]
        try:
            # MySQL-python 1.0
            if time.time() - installDate.ticks() > 86400:
                #Install date was more than 24 hours ago
                log.info("Client %s attempted to register outside security " \
                         "window" % self.client)
                return 3
        except AttributeError:
            # Mysql-python 1.2
            if datetime.today() - timedelta(days=1) > installDate:
                log.info("Client %s attempted to register outside security " \
                         "window" % self.client)
                return 3

        return self.__register(publicKey, dept, version)
        

    def bless(self, dept, version):
        # Take a System Administrator's Blessing as registration
        # This works by finding the public key on disk.  Supposedly
        # only a sysadmin can put it there, copied from the client to 
        # bless

        file = os.path.join(self.keypath, self.client+".pub")
        # From the above, this must also be called from the client
        # to register

        if not os.access(file, os.R_OK):
            # key not found.  Cannot register
            log.warning("Could not bless %s.  Key file not found." \
                        % self.client)
            return 1

        try:
            fd = open(file)
            publicKey = fd.read()
            fd.close()
        except IOError, e:
            log.critical("Cound not bless %s.  IOError." % self.client)
            return 99

        # check to see if client has been logged in DB
        self.cursor.execute("""select * from realmlinux where 
            hostname=%s""", (self.client,))
        
        if not self.cursor.rowcount > 0:
            # Then we put it there
            ts = time.localtime()
            date = MySQLdb.Timestamp(ts[0], ts[1], ts[2], ts[3], ts[4], ts[5])
            q = """insert into realmlinux 
                   (hostname, installdate, recvdkey, support) 
                   values (%s, %s, %s, %s)"""
            t = (self.client, date, 0, 1)
            self.cursor.execute(q, t)
            
        # Update db 
        ret = self.__register(publicKey, dept, version)
        try:
            os.unlink(file)
        except OSError, e:
            pass

        return ret
            
    def createNoSupport(self, publicKey, dept, version):
        "Create a db entry for a non supported client."

        log.info("Registering no-support for %s" % self.client)

        ts = time.localtime()
        date = MySQLdb.Timestamp(ts[0], ts[1], ts[2], ts[3], ts[4], ts[5])
        id = self.getHostID()
        deptid = self.getDeptID(dept)

        if id == None:
            q = """insert into realmlinux 
                   (hostname, installdate, recvdkey, support) 
                   values (%s, %s, %s, %s)"""
            t = (self.client, date, 0, 0)
        else:
            q = """update realmlinux set 
                   installdate = %s, 
                   recvdkey = 0,
                   publickey = NULL,
                   dept_id = %s,
                   version = '',
                   support = 0
                   where host_id = %s"""
            t = (date, deptid, id)

        self.cursor.execute(q, t)

        return self.__register(publicKey, dept, version)

    def __register(self, publicKey, dept, version):
        log.info("Registering %s" % self.client)
        # Require that a row for the hostname exists in the DB
        ts = time.localtime()
        date = MySQLdb.Timestamp(ts[0], ts[1], ts[2], ts[3], ts[4], ts[5])

        try:
            id = self.getHostID()
            deptid = self.getDeptID(dept)

            q = """update realmlinux 
                   set recvdkey=1, publickey=%s, dept_id=%s, version=%s
                   where host_id=%s"""

            self.cursor.execute(q, (publicKey, deptid, version, id))
            self.cursor.execute("""delete from lastheard where host_id = %s""",
                                (id,))
            self.cursor.execute("""insert into lastheard (host_id, `timestamp`)
                                   values (%s, %s)""", (id, date))
            self.conn.commit()
        except MySQLdb.Warning, e:
            # What's this about?
            log.critical("MySQL Waring: %s\n" % str(e))

        return 0
    
    
    def checkIn(self, publicKey, sig):
        """Workstation checking in.  Update status in DB."""
        
        ts = time.localtime()
        date = MySQLdb.Timestamp(ts[0], ts[1], ts[2], ts[3], ts[4], ts[5])

        if not self.verifyClient(publicKey, sig):
            return 1

        id = self.getHostID()
        if id == None:
            # Cannot check in non-registered client
            return 1

        self.cursor.execute("""update lastheard
           set `timestamp` = %s where host_id = %s""", (date, id))
        self.conn.commit()

        return 0

    def setServiceStatus(self, service, succeed, data=None):
        """Record a service status message into the database."""
        
        sid = self.getServiceID(service)
        if sid == None:
            # We don't store data about services we don't know
            return 1

        q = """insert into status (host_id, service_id, `timestamp`,
                                   success, data)
               values (%s, %s, %s, %s, %s)"""
        ts = time.localtime()
        date = MySQLdb.Timestamp(ts[0], ts[1], ts[2], ts[3], ts[4], ts[5])
        id = self.getHostID()

        if succeed:
            succeed = 1
        else:
            succeed = 0

        self.cursor.execute(q, (id, sid, date, succeed, data))
        self.conn.commit()
        return 0

    def setServiceID(self, serv):
        "Create a Service ID"

        q = "insert into service (name) values (%s)"

        sid = self.getServiceID(serv)
        if sid == None:
            self.cursor.execute(q, (serv,))
            self.conn.commit()
            return self.getServiceID(serv)
        else:
            return sid

    def getServiceID(self, serv):
        "Return the ID for this service.  None if the service doesn't exist."

        q = "select service_id from service where name = %s"
        self.cursor.execute(q, (serv,))

        if self.cursor.rowcount > 0:
            return self.cursor.fetchone()[0]
        else:
            return None

    def getDeptID(self, dept):
        "Return the DB ID of this department.  Create it if needed."

        q1 = "select dept_id from dept where name = %s"
        q2 = "insert into dept (name) values (%s)"

        self.cursor.execute(q1, (dept,))
        if self.cursor.rowcount > 0:
            return self.cursor.fetchone()[0]

        self.cursor.execute(q2, (dept,))
        self.conn.commit()

        self.cursor.execute(q1, (dept,))
        return self.cursor.fetchone()[0]

    def getHostID(self):
        if self.hostid != None:
            return self.hostid

        self.cursor.execute("""select host_id from realmlinux where
                               hostname = %s""", (self.client,))
        if self.cursor.rowcount == 0:
            log.warning("Tried to pull host_id for %s who doesn't exist" \
                        % self.client)
            return None

        self.hostid = self.cursor.fetchone()[0]
        return self.hostid

    def getActivationKey(self, publicKey, sig):
        """Returns the current RHN activation key for this host."""

        if not self.verifyClient(publicKey, sig):
            # verification error
            return 1

        log.info("Client %s requests activation key" % self.client)

        ks = self.__getWebKs()
        data = ks.getKeys('enable', 'activationkey')
        if len(data) == 0:
            # *sigh* no key
            key = self.rhnkey
        else:
            key = data[0]['options'][0]

        return key

    def getServiceStatus(self, service):
        """Return historical information regarding this clients status."""
        
        q = """select `timestamp`, success, data from status where
               host_id = %s and service_id = %s order by `timestamp`"""

        sid = self.getServiceID(status)
        if sid == None:
            return []

        id = self.getHostID()
        self.cursor.execute(q, (id, sid))

        ret = []
        result = self.cursor.fetchone()
        while result != None:
            row = {}
            row['timestamp'] = result[0]
            row['success'] = result[1]
            row['data'] = result[2]

            ret.append(row)
            result = self.cursor.fetchone()

        return ret

    def getDepartments(self):
        q = """select dept_id, name from dept"""
        self.cursor.execute(q)
        ret = []

        for i in range(self.cursor.rowcount):
            result = self.cursor.fetchone()
            row = {}
            row['dept_id'] = result[0]
            row['name'] = result[1]
            ret.append(row)

        return ret

    def getClientList(self, dept_id, services):
        # services is a list of service IDs
        q = """select r.hostname, r.host_id, r.support, `l.timestamp` 
               from realmlinux as r, lastheard as l
               where r.dept_id = %s and r.recvdkey = 1
               order by r.hostname"""

        self.cursor.execute(q, (dept_id,))
        
        ret = []
        for i in range(self.cursor.rowcount):
            result = self.cursor.fetchone()
            row = {}
            row['hostname'] = result[0]
            row['host_id'] = result[1]
            row['support'] = result[2] == 1
            row['lastcheck'] = result[3]
            ret.append(row)

        # XXX: add status fields for requested services
        return ret

    def __makeUpdatesConf(self):
        """Generate the updates.conf file and return a string."""

        ks = self.__getWebKs()
        data = ks.getKeys('users')
        if len(data) == 0:
            usersdata = "users default %s" % self.defaultKey
        else:
            # a list of the options passed to the 'users' key
            args = data[0]['options']
            usersdata = "users " + " ".join(args)
        
        # root data
        data = ks.getKeys('root')
        if len(data) == 0:
            rootdata = "root default %s" % self.defaultKey
        else:
            args = data[0]['options']
            rootdata = "root " + " ".join(args)

        # clusters
        data = ks.getKeys('cluster')
        clusterdata = ""
        if len(data) > 0:
            for row in data:
                clusterdata = "%scluster %s\n" % (clusterdata, 
                              " ".join(row['options']))

        return "%s\n%s\n%s" % (usersdata, rootdata, clusterdata)

    def getEncKeyFile(self, publicKey, sig):
        """Returns an ecrypted string containing what should go in 
           /etc/update.conf on the workstation."""
        
        if not self.verifyClient(publicKey, sig):
            # Can't return None
            return []

        if not self.isSupported():
            return []

        log.info("Client %s retrieving update.conf" % self.client)

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
       

    def __getWebKs(self):
        """Find and return the web-kickstart config object"""
        
        os.chdir(sys.path[-1])
        wks = webKickstart("fakeurl", {})
        scList = wks.findFile(self.client, self.jumpstarts)
        if len(scList) == 0:
            raise Exception("No config for %s in %s" % (self.client,
                                                        self.jumpstarts))
        # Do we care about collisions?
        # If not, this is the same thing that Web-Kickstart does
        sc = scList[0]
        
        try:
            ks = wks.cfg.get_obj(sc.getVersion(), {'url': "fakeurl", 'sc': sc})
        except Exception, e:
            # KeyError or ConfgError from webkickstart
            # Unsupported version key in config file
            ks = wks.cfg.get_obj('default', {'url': "fakeurl", 'sc': sc})

        return ks
    
