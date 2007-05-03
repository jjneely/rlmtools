#!/usr/bin/python
#
# RealmLinux Manager -- Main server object
# Copyright (C) 2003, 2005, 2006, 2007 NC State University
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
import os
import os.path
import time
import logging
import traceback
import base64

from datetime import datetime, timedelta

from resultSet import resultSet
import mysql

try:
    import debug
except ImportError:
    sys.path.append("/afs/unity/web/l/linux/web-kickstart")
else:
    sys.path.append("/home/slack/projects/solaris2ks")

from webKickstart import config
from webKickstart import webKickstart

log = logging.getLogger("xmlrpc")

# Holds the database class
DataBase = None

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
    db['db_host'] = config.get('db', 'host')
    db['db_user'] = config.get('db', 'user')
    db['db_pass'] = config.get('db', 'passwd')
    db['db_name'] = config.get('db', 'db')
    
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

    def __init__(self, client):
        """Set up server and define who we are talking to...well at least
           what we are told we are talking to."""
           
        self.client = client
        self.hostid = None

        log.info("Running Server object for %s" % self.client)

        global DataBase
        if DataBase == None:
            # Init MySQL Connections
            DataBase = mysql.MysqlDB(getDBDict())

        if self.conn == None or self.cursor == None:
            # get MySQL information
            self.conn = DataBase.getConnection()
            self.cursor = DataBase.getCursor()

    def verifySecret(self, secret):
        # Basically, cheap administrative or script authentication
        return config.secret == secret

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

    def isRegistered(self, pubKey=None, sig=None):
        """Returns a clients public key from the database if this client 
           is registered.  Otherwise None is returned.  If the signature
           on the pubKey parameter is valid attempt to find the host and
           update its hostname."""

        q1 = """select publickey from realmlinux
                where hostname = %s and recvdkey = 1"""
        q2 = """select host_id, hostname, publickey from realmlinux
                where recvdkey = 1 and publickey = %s"""
        q3 = """update realmlinux set hostname = %s where host_id = %s"""
        
        trustedKey = None
        # Look up the host by its hostname
        self.cursor.execute(q1, (self.client,))
        if self.cursor.rowcount > 0:
            trustedKey = self.cursor.fetchone()[0]
        if pubKey == None or sig == None:
            # This may be None.  In this case we still want to indecate failure
            return trustedKey

        # Okay, lets search to see if we know about this RSA key.
        # Verify the signature of the key text.  A valid sig requires
        # the private key which a normal user shouldn't be able to read
        # from the client.
        try:
            key = ezPyCrypto.key(pubKey)
        except ezPyCrypto.CryptoKeyError:
            # Client sent us something else than a key
            return None

        try:
            if not key.verifyString(pubKey, sig):
                return None
        except Exception:
            # Client sent us something other than a signature
            return None

        if trustedKey == pubKey or trustedKey == key.exportKey():
            # Its possible that they key export may be different text
            # for the same key, but at this point we know that the
            # pubKey var is valid as we check it above.
            return trustedKey

        self.cursor.execute(q2, (pubKey,))
        if self.cursor.rowcount < 1:
            self.cursor.execute(q2, (key.exportKey(),))
        if self.cursor.rowcount < 1:
            return None

        hostinfo = resultSet(self.cursor).dump()[0]
        log.warning("Client %s has the host keys for %s. Updating hostname." \
                    % (self.client, hostinfo['hostname']))

        # Change the hostname for this client if it exists
        hid = self.getHostID()
        if hid != None:
            self.cursor.execute(q3, ("unknown - ID: %s" % hid, hid))

        # Now update the registration we found
        self.cursor.execute(q3, (self.client, hostinfo['host_id']))
        self.conn.commit()
        return hostinfo['publickey']
    
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

        file = os.path.join(config.key_directory, self.client+".pub")
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
        else:
            q = """update realmlinux set support = 1 where hostname = %s"""
            self.cursor.execute(q, (self.client,))
            
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

        # Validate the passed in key text.
        # We do not reformat the key by calling key.exportKey() because we
        # deal with clients that use various versions of the pickle format.
        # We need to be able to search on this key rather than select all
        # of them, decode, and compare because the pickle/base64 encoding 
        # differs.
        try:
            key = ezPyCrypto.key(publicKey)
        except ezPyCrypto.CryptoKeyError:
            # Client sent us something else than a key
            return 4

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
            return 2

        self.cursor.execute("""update lastheard
           set `timestamp` = %s where host_id = %s""", (date, id))
        self.conn.commit()

        return 0

    def setServiceStatus(self, service, succeed, timestamp, data=None):
        """Record a service status message into the database.
           timestamp should be a POSIX time...so time.time()
           
           data should be a Base64 encoded blob."""
        
        sid = self.getServiceID(service)
        if sid == None:
            # We don't store data about services we don't know
            log.info("Unknown service message type %s from %s" % \
                     (service, self.client))
            return 2

        q = """insert into status (host_id, service_id, `timestamp`,
                                   received, success, data)
               values (%s, %s, %s, %s, %s, %s)"""
        clientstamp = datetime.fromtimestamp(timestamp)
        date = datetime.today()
        id = self.getHostID()
        if data != None:
            data = base64.decodestring(data)

        if data == "":
            # Enpty message -- we can't marshal None
            data = None

        if succeed:
            succeed = 1
        else:
            succeed = 0

        self.cursor.execute(q, (id, sid, clientstamp, date, succeed, data))
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

    def getDeptName(self, dept_id):
        q = """select name from dept where dept_id = %s"""

        self.cursor.execute(q, (dept_id,))
        result = self.cursor.fetchone()
        if result == None:
            return None
        else:
            return result[0]

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

    def getHostName(self, host_id):
        q = """select hostname from realmlinux where host_id = %s"""
        self.cursor.execute(q, (host_id,))
        if self.cursor.rowcount < 1:
            return None
        else:
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
            key = config.rhnkey
        else:
            key = data[0]['options'][0]

        return key

    def getStatusDetail(self, status_id):
        """Return historical information regarding this clients status."""
        
        q = """select serv.name, s.timestamp, s.success, s.data,
                      s.received, r.hostname, r.host_id
               from status as s, service as serv, realmlinux as r 
               where r.host_id = s.host_id and
                     serv.service_id = s.service_id and
                     s.st_id = %s"""
    
        self.cursor.execute(q, (status_id,))
        result = resultSet(self.cursor).dump()
    
        return result[0]

    def getDepartments(self):
        q1 = """select dept.name, dept.dept_id,
                    count(support = 1 or null) as supported, 
                    count(support = 0 or null) as unsupported 
                from dept left join realmlinux on 
                    dept.dept_id = realmlinux.dept_id
                    and realmlinux.recvdkey = 1
                group by dept.name;"""

        self.cursor.execute(q1)
        return resultSet(self.cursor).dump()

    def getNoUpdates(self):
        # q1 requires the client to have updated sometime
        # Need to run q3 and substract q2
        q1 = """select foo.host_id, realmlinux.hostname, dept.name as deptname 
               from realmlinux, dept, 
                  ( select status.host_id, max(status.timestamp) as maxdate 
                    from status, service 
                    where service.service_id = status.service_id 
                       and service.name = 'updates'
                       and status.success = 1
                    group by host_id 
                  ) as foo 
               where foo.host_id = realmlinux.host_id 
                  and realmlinux.dept_id = dept.dept_id 
                  and TO_DAYS(maxdate) <= TO_DAYS(NOW()) - 7 
                  and TO_DAYS(realmlinux.installdate) <= TO_DAYS(NOW()) - 7"""
        q2 = """select distinct status.host_id, realmlinux.hostname
                from status, service, realmlinux
                where service.service_id = status.service_id
                   and realmlinux.host_id = status.host_id
                   and service.name = 'updates'
                   and status.success = 1 
                   and TO_DAYS(status.timestamp) >= TO_DAYS(NOW()) - 7"""
        q3 = """select realmlinux.host_id, realmlinux.hostname, 
                   dept.name as deptname
                from realmlinux, dept
                where dept.dept_id = realmlinux.dept_id
                   and realmlinux.recvdkey = 1"""

        self.cursor.execute(q3)
        result = resultSet(self.cursor).dump()
        hash = {}

        for row in result:
            hash[row['hostname']] = row

        self.cursor.execute(q2)
        result2 = resultSet(self.cursor).dump()

        for row in result2:
            try:
                del hash[row['hostname']]
            except KeyError:
                pass

        # This method of gathering the data prevents the database
        # from sorting for us
        keys = hash.keys()
        keys.sort(lambda x,y: cmp(x.lower(), y.lower()))

        return map(hash.get, keys)

    def getProblemList(self):
        q  = """select status.host_id, realmlinux.hostname, 
                   dept.name as deptname
                from realmlinux, dept, status, 
                   ( select host_id, service_id as sid, 
                        max(`timestamp`) as maxdate 
                     from status group by host_id, service_id ) as foo
                where status.host_id = foo.host_id 
                   and status.service_id = foo.sid
                   and status.timestamp = foo.maxdate 
                   and status.success=0
                   and status.host_id = realmlinux.host_id
                   and realmlinux.dept_id = dept.dept_id
                order by deptname asc"""

        self.cursor.execute(q)
        return resultSet(self.cursor).dump()

    def getClientList(self, dept_id):
        q1 = """select r.hostname, r.host_id, r.support, r.installdate,
                l.timestamp as lastcheck
                from realmlinux as r, lastheard as l
                where r.dept_id = %s and r.recvdkey = 1 and
                r.host_id = l.host_id
                order by r.hostname"""

        q2 = """select status.host_id, service.name, 
                   status.success, status.timestamp
                from service, status,
                ( select status.host_id, 
                         status.service_id as sid, 
                         max(status.timestamp) as maxdate 
                  from status, realmlinux
                  where realmlinux.host_id = status.host_id
                     and realmlinux.dept_id = %s
                  group by status.host_id, status.service_id
                ) as current
                where current.sid = status.service_id and
                service.service_id = status.service_id and
                status.timestamp = current.maxdate and
                status.host_id = current.host_id"""

        self.cursor.execute(q1, (dept_id,))
        result = resultSet(self.cursor).dump()

        # I'm going to reference the data in result via a hash
        hash = {}

        for row in result:
            hash[row['host_id']] = row

        self.cursor.execute(q2, (dept_id,))
        status = resultSet(self.cursor).dump()

        for row in status:
            service = row['name']
            stime = "%s_time" % service
            hash[row['host_id']][service] = row['success']
            hash[row['host_id']][stime] = row['timestamp']

        return result

    def getClientDetail(self, host_id, history_days=30):
        # returns, hostname, installdate, recvdkey, support, dept, version,
        #    lastcheck, status
        # status is a list of dicts: service, timestamp, success, data
        q1 = """select r.hostname, r.installdate, r.recvdkey, r.support,
                       d.name as dept, r.dept_id, r.version
                from realmlinux as r, dept as d
                where d.dept_id = r.dept_id and r.host_id = %s"""
        q2 = """select `timestamp` as lastcheck from lastheard where
                host_id = %s"""
        q3 = """select service.name as service, status.timestamp, 
                       status.success, status.data, status.st_id,
                       status.received
                from service, status
                where service.service_id = status.service_id and
                      status.host_id = %s and 
                      TO_DAYS(status.timestamp) > TO_DAYS(NOW()) - %s
                order by status.received desc"""

        self.cursor.execute(q1, (host_id,))
        result1 = resultSet(self.cursor).dump()[0]  # This is one row

        self.cursor.execute(q2, (host_id,))
        if self.cursor.rowcount > 0:
            result2 = self.cursor.fetchone()[0]
        else:
            result2 = None

        self.cursor.execute(q3, (host_id, history_days))
        result3 = resultSet(self.cursor).dump()

        result1['lastcheck'] = result2
        result1['status'] = result3
        return result1

    def getTotalClients(self):
        """Returns a tuple with the number of supported, non-supported, 
           and clients that have not registered."""

        q1 = "select count(*) from realmlinux where support = 1 and recvdkey=1"
        q2 = "select count(*) from realmlinux where support = 0 and recvdkey=1"
        q3 = "select count(*) from realmlinux where recvdkey = 0"
        q4 = "select count(*) from dept"
        # q5 select the number of hosts with problems
        q5 = """select count(*) from status, 
                   ( select host_id, service_id as sid, 
                        max(`timestamp`) as maxdate 
                     from status group by host_id, service_id ) as foo
                where status.host_id = foo.host_id 
                   and status.service_id = foo.sid
                   and status.timestamp = foo.maxdate 
                   and status.success=0"""
        # The number of hosts not updating           
        q6 = """select count(*) 
               from realmlinux, 
                  ( select status.host_id, max(status.timestamp) as maxdate 
                    from status, service 
                    where service.service_id = status.service_id 
                       and service.name = 'updates' 
                    group by host_id 
                  ) as foo 
               where foo.host_id = realmlinux.host_id 
                  and TO_DAYS(maxdate) <= TO_DAYS(NOW()) - 7 
                  and TO_DAYS(realmlinux.installdate) <= TO_DAYS(NOW()) - 7"""

        ret = {}
        self.cursor.execute(q1)
        ret['supported'] = self.cursor.fetchone()[0]
        
        self.cursor.execute(q2)
        ret['unsupported'] = self.cursor.fetchone()[0]

        self.cursor.execute(q3)
        ret['unregistered'] = self.cursor.fetchone()[0]

        self.cursor.execute(q4)
        ret['departments'] = self.cursor.fetchone()[0]

        self.cursor.execute(q5)
        ret['problems'] = self.cursor.fetchone()[0]

        self.cursor.execute(q6)
        ret['noupdates'] = self.cursor.fetchone()[0]

        return ret

    def getNotRegistered(self):
        """Returns information about clients that have not registered."""

        q = """select host_id, hostname, support from realmlinux where
                  recvdkey = 0 order by hostname asc"""

        self.cursor.execute(q)
        return resultSet(self.cursor).dump()

    def getActiveClients(self, hours=6):
        """Returns the number of clients heard from in the last hours hours."""

        q = """select count(host_id) from lastheard where
               `timestamp` > %s"""
        date = datetime.today() - timedelta(hours=hours)

        self.cursor.execute(q, (date,))
        return self.cursor.fetchone()[0]

    def deleteClient(self, host_id):
        """Removes a client from the database."""
        log.warning("Removing client from database: %s" \
                    % self.getHostName(host_id))
        q1 = """delete from realmlinux where host_id = %s"""
        q2 = """delete from lastheard where host_id = %s"""
        q3 = """delete from status where host_id = %s"""

        self.cursor.execute(q1, (host_id,))
        self.cursor.execute(q2, (host_id,))
        self.cursor.execute(q3, (host_id,))
        self.conn.commit()

    def cleanDB(self, days=31):
        """Removes status events older than the variable days and removes
           clients that have not checked in in variable days."""

        q1 = """select host_id from lastheard where 
                `timestamp` < %s"""
        q2 = """delete from status where received < %s and service_id = %s"""
        q3 = """select host_id from realmlinux where 
                recvdkey = 0 and installdate < %s"""
        q4 = """select service_id from service where
                  name != 'login' and name != 'logout'"""

        date = datetime.today() - timedelta(days)

        self.cursor.execute(q1, (date,))
        result = resultSet(self.cursor).dump()
        for client in result: self.deleteClient(client['host_id'])

        self.cursor.execute(q3, (date,))
        result = resultSet(self.cursor).dump()
        for client in result: self.deleteClient(client['host_id'])

        # XXX: Handle persistant statuses
        self.cursor.execute(q2, (date,))
        self.conn.commit()

    def initHost(self, secret, fqdn):
        """Logs a newly installing host.  To work with Web-Kickstart.
           FQDN is the FQDN of the host we are installing.
           A secret is used to auth web-kickstart or an admin."""

        q1 = """select host_id from realmlinux where hostname=%s"""
        q2 = """update realmlinux set 
                   installdate = %s, recvdkey = 0, publickey = NULL,
                   dept_id = %s, version = '', support = 1
                where host_id = %s"""
        q3 = """insert into realmlinux 
                   (hostname, installdate, recvdkey, publickey, dept_id, 
                    version, support) 
                values (%s, %s, 0, NULL, %s, '', 1)"""
        # Log in/out events are persistant
        q4 = """select service_id from service where
                  name != 'login' and name != 'logout'"""
        q5 = """delete from status where host_id = %s and service_id = %s"""
        q6 = """delete from lastheard where host_id = %s"""
        q7 = """insert into lastheard (host_id, `timestamp`) 
                values (%s,'0000-00-00 00:00:00')"""

        if not self.verifySecret(secret):
            log.warning("initHost() called with bad secret")
            return 1

        date = datetime.today()
        dept = self.getDeptID('unknown')
        self.cursor.execute(q1, (fqdn,))
        if self.cursor.rowcount == 0:
            self.cursor.execute(q3, (fqdn, date, dept))
            self.cursor.execute(q1, (fqdn,))
            hostid = self.cursor.fetchone()[0]
        else:
            hostid = self.cursor.fetchone()[0]
            self.cursor.execute(q2, (date, dept, hostid))
            self.cursor.execute(q4)
            result = resultSet(self.cursor).dump()
            for row in result:
                self.cursor.execute(q5, (hostid, row['service_id'],))

        self.cursor.execute(q6, (hostid,))
        self.cursor.execute(q7, (hostid,))
        self.conn.commit()
        
        log.info("Initialized host: %s" % fqdn)
        
        return 0

    def __makeUpdatesConf(self):
        """Generate the updates.conf file and return a string."""

        ks = self.__getWebKs()
        data = ks.getKeys('users')
        if len(data) == 0:
            usersdata = "users default %s" % config.defaultkey
        else:
            # a list of the options passed to the 'users' key
            args = data[0]['options']
            usersdata = "users " + " ".join(args)
        
        # root data
        data = ks.getKeys('root')
        if len(data) == 0:
            rootdata = "root default %s" % config.defaultkey
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
        fd = open(config.privateKey)
        server = ezPyCrypto.key(fd.read())
        fd.close()
        sig = server.signString(enc)

        ret = [enc, sig]

        return ret
       

    def __getWebKs(self):
        """Find and return the web-kickstart config object"""
        
        os.chdir(sys.path[-1])
        wks = webKickstart("fakeurl", {})
        scList = wks.findFile(self.client, config.jumpstarts)
        if len(scList) == 0:
            raise Exception("No config for %s in %s" % (self.client,
                                                        config.jumpstarts))
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
    
