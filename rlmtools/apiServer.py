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

import sys
import ezPyCrypto
import os
import os.path
import logging
import base64
import pickle
import server
import time
import MySQLdb

from datetime import datetime, timedelta
from resultSet import resultSet
from configDragon import config

try:
    import debug
except ImportError:
    sys.path.append("/afs/unity/web/l/linux/web-kickstart")
else:
    sys.path.append("/home/slack/projects/solaris2ks")

import webKickstart

log = logging.getLogger("xmlrpc")

class APIFault(StandardError): pass

class APIServer(server.Server):

    # Use class variables so we don't have to connect each time
    conn = None
    cursor = None

    def __init__(self, apiVersion, client, uuid=None):
        """Set up server and define who we are talking to...well at least
           what we are told we are talking to."""
           
        server.Server.__init__(self)

        self.apiVersion = apiVersion
        self.client = client
        self.uuid = uuid
        self.hostid = None

        if self.apiVersion > 0 and self.uuid == None:
            raise APIFault("Client must supply its UUID with this API version")

        if self.apiVersion == 0 and self.uuid != None:
            raise APIFault("Client passed in a UUID for invalid API version")

        log.info("API version %s started for client: %s" % (self.apiVersion,
                                                            self.client))

    def getHostID(self, byFQDN=False):
        """Return the database ID for this host.  byFQDN can be set
           to True to force a lookup via the hostname rather than UUID.
           Which is useful during registration when we haven't received
           the UUID yet.
           """
        if self.hostid == None:
            if byFQDN or self.apiVersion == 0:
                self.hostid = server.Server.getHostID(self, self.client)
            else:
                self.hostid = server.Server.getUuidID(self, self.uuid)
            
        return self.hostid

    def getPublicKey(self):
        """Return the server's public key"""
        return config.publickey

    def verifySecret(self, secret):
        # Basically, cheap administrative or script authentication
        return config.secret == secret

    def verifyClient(self, uuid, sig):
        """Make sure that the public key and sig match this client."""
        
        trustedKey = self.isRegistered()

        if trustedKey == None:
            # We are not registered bail!
            return False
        
        k = ezPyCrypto.key(trustedKey)
        if k.verifyString(uuid, sig):
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
           update its hostname.
           
           In API versions > 0 the pubKey parameter is the clients UUID.
        """

        q1 = """select hostkeys.publickey from realmlinux, hostkeys
                where realmlinux.host_id = hostkeys.host_id
                and realmlinux.hostname = %s and realmlinux.recvdkey = 1"""
        q4 = """select realmlinux.host_id, realmlinux.hostname
                from realmlinux
                where realmlinux.recvdkey = 1 and realmlinux.uuid = %s"""
        q5 = """select hostkeys.publickey from realmlinux, hostkeys
                where realmlinux.host_id = hostkeys.host_id
                and realmlinux.uuid = %s and realmlinux.recvdkey = 1"""
        
        log.debug("In isRegistered()")
        log.debug("client: %s  uuid: %s" % (self.client, self.uuid))

        if self.apiVersion < 1:
            # Look up the host by its hostname
            self.cursor.execute(q1, (self.client,))
        else:
            # Look up by the hosts uuid
            self.cursor.execute(q5, (self.uuid,))
        if self.cursor.rowcount > 0:
            trustedKey = self.cursor.fetchone()[0]
        else:
            log.debug("uuid/client not found in database")
            trustedKey = None

        if pubKey == None or sig == None:
            # This may be None.  In this case we still want to indecate failure
            #log.debug("No key/sig to check, returning public key from db")
            return trustedKey

        if self.apiVersion == 0:
            return self._isRegistered_api_0(trustedKey, pubKey, sig)

        if trustedKey == None:
            return None

        try:
            tkey = ezPyCrypto.key(trustedKey)
        except ezPyCrypto.CryptoKeyError:
            log.warning("Public RSA key from database does not validate!")
            log.warning("Failed key belongs to UUID: %s" % self.uuid)
            return None

        try:
            if not tkey.verifyString(pubKey, sig):
                return None
        except Exception:
            log.debug("Client sent us a bad signature.")
            return None

        self.cursor.execute(q4, (self.uuid,))
        hostinfo = resultSet(self.cursor).dump()[0]
        if hostinfo['hostname'] != self.client:
            self.changeHostname(hostinfo['host_id'], self.client)

        return trustedKey

    def findHostByKey(self, publicKey):
        """Return a dict with keys 'host_id', 'uuid', 'hostname', 'publickey'
           for the host that matches this key.  Possibly very slowly."""

        q = """select realmlinux.host_id, realmlinux.uuid, realmlinux.hostname, 
               hostkeys.publickey from realmlinux, hostkeys
               where realmlinux.host_id = hostkeys.host_id
               and realmlinux.recvdkey = 1 and hostkeys.publickey = %s"""

        self.cursor.execute(q, (publicKey,))
        if self.cursor.rowcount < 1:
            self.cursor.execute(q, (ezPyCrypto.key(publicKey).exportKey(),))
        if self.cursor.rowcount < 1:
            return None

        return resultSet(self.cursor).dump()[0]

    def _isRegistered_api_0(self, trustedKey, pubKey, sig):
        q2 = """select realmlinux.host_id, realmlinux.hostname, 
                       hostkeys.publickey 
                from realmlinux, hostkeys
                where realmlinux.host_id = hostkeys.host_id
                and realmlinux.recvdkey = 1 and hostkeys.publickey = %s"""

        # Okay, lets search to see if we know about this RSA key.
        # Verify the signature of the key text.  A valid sig requires
        # the private key which a normal user shouldn't be able to read
        # from the client.
        try:
            key = ezPyCrypto.key(pubKey)
        except ezPyCrypto.CryptoKeyError:
            # Client sent us something else than a key
            log.warning("Client sent a malformed public key")
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

        hostinfo = self.findHostByKey(pubKey)
        if hostinfo == None: return None

        log.warning("Client %s has the host keys for %s. Updating hostname." \
                    % (self.client, hostinfo['hostname']))
        self.changeHostname(hostinfo['host_id'], self.client)

        return hostinfo['publickey']

    def changeHostname(self, hostID, newname):
        q1 = """select host_id from realmlinux where hostname = %s"""
        q2 = """update realmlinux set hostname = %s where host_id = %s"""

        # Change the hostname for this client if it exists
        self.cursor.execute(q1, (newname,))
        if self.cursor.rowcount > 0:
            hid = self.cursor.fetchone()[0]
            self.cursor.execute(q2, ("unknown - ID: %s" % hid, hid))

        # Now update the registration we found
        self.cursor.execute(q2, (newname, hostID))
        self.conn.commit()
    
    def register(self, publicKey, dept, version, rhnid):
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
            return self.createNoSupport(publicKey, dept, version, rhnid)

        # Check the Time window for 24 hours
        installDate = self.cursor.fetchone()[0]
        if datetime.today() - timedelta(days=1) > installDate:
            # Client did not register inside 24 hours
            log.info("Client %s attempted to register outside security " \
                     "window" % self.client)
            # Old return code 3
            return self.createNoSupport(publicKey, dept, version, rhnid)

        return self.__register(publicKey, dept, version, rhnid)
        

    def bless(self, dept, version, rhnid):
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
        if self.apiVersion < 1:
            self.cursor.execute("""select host_id from realmlinux where 
                hostname=%s""", (self.client,))
        else:
            q = """select host_id from realmlinux where
                      uuid = %s or
                      isnull(uuid) and hostname = %s"""
            self.cursor.execute(q, (self.uuid, self.client))
        
        if not self.cursor.rowcount > 0:
            # Then we put it there
            self.initHost(self.client, 1)
        else:
            hid = self.cursor.fetchone()[0]
            q = """update realmlinux set support = 1 where host_id = %s"""
            self.cursor.execute(q, (hid,))
            
        # Update db 
        ret = self.__register(publicKey, dept, version, rhnid)
        try:
            os.unlink(file)
        except OSError, e:
            pass

        return ret
            
    def createNoSupport(self, publicKey, dept, version, rhnid):
        "Create a db entry for a non supported client."

        log.info("Registering no-support for %s" % self.client)

        self.initHost(self.client, 0)
        return self.__register(publicKey, dept, version, rhnid)

    def __register(self, publicKey, dept, version, rhnid):
        log.info("Registering %s" % self.client)

        if self.apiVersion > 0 and not isinstance(rhnid, int):
            raise APIFault("API version requires an integer for the RHN ID")

        # We can't marshal None so -1 == no RHN ID
        if rhnid == -1:
            rhnid = None

        # Require that a row for the hostname exists in the DB
        date = datetime.today()

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
            id = self.getHostID(byFQDN=True) 
            deptid = self.getDeptID(dept)

            q1 = "delete from hostkeys where host_id = %s"
            q2 = """update realmlinux 
                   set recvdkey=1, dept_id=%s, version=%s, uuid=%s, rhnid=%s
                   where host_id=%s"""
            q3 = "insert into hostkeys (host_id, publickey) values (%s, %s)"

            self.cursor.execute(q1, (id,))
            if self.apiVersion > 0:
                self.cursor.execute(q2, (deptid, version, self.uuid, rhnid, id))
            else:
                self.cursor.execute(q2, (deptid, version, None, None, id))
            self.cursor.execute(q3, (id, publicKey))
            self.cursor.execute("""delete from lastheard where host_id = %s""",
                                (id,))
            self.cursor.execute("""insert into lastheard (host_id, `timestamp`)
                                   values (%s, %s)""", (id, date))
            self.conn.commit()
        except MySQLdb.Warning, e:
            # What's this about?
            log.critical("MySQL Waring: %s\n" % str(e))
            return 99

        return 0
    
    
    def checkIn(self, uuid, sig):
        """Workstation checking in.  Update status in DB."""
        
        date = datetime.today()

        if not self.verifyClient(uuid, sig):
            return 1

        id = self.getHostID()
        if id == None:
            # Cannot check in non-registered client
            return 2

        self.cursor.execute("""update lastheard
           set `timestamp` = %s where host_id = %s""", (date, id))
        self.conn.commit()

        return 0

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

    def initHost(self, fqdn, support):
        """Logs a newly installing host.  To work with Web-Kickstart.
           FQDN is the FQDN of the host we are installing.
           A secret is used to auth web-kickstart or an admin."""

        q1 = """select host_id from realmlinux where hostname=%s"""
        q2 = """update realmlinux set 
                   installdate = %s, recvdkey = 0, uuid = NULL, rhnid = NULL,
                   dept_id = %s, version = '', support = %s
                where host_id = %s"""
        q3 = """insert into realmlinux 
                   (hostname, installdate, recvdkey, dept_id, 
                    version, support) 
                values (%s, %s, 0, %s, '', %s)"""
        q4 = """delete from hostkeys where host_id = %s"""
        q5 = """delete from status where host_id = %s"""
        q6 = """delete from lastheard where host_id = %s"""
        q7 = """insert into lastheard (host_id, `timestamp`) 
                values (%s,'0000-00-00 00:00:00')"""

        date = datetime.today()
        dept = self.getDeptID('unknown')
        self.cursor.execute(q1, (fqdn,))
        if self.cursor.rowcount == 0:
            self.cursor.execute(q3, (fqdn, date, dept, support))
            self.cursor.execute(q1, (fqdn,))
            hostid = self.cursor.fetchone()[0]
        else:
            hostid = self.cursor.fetchone()[0]
            self.cursor.execute(q2, (date, dept, support, hostid))
            self.cursor.execute(q4, (hostid,))
            self.cursor.execute(q5, (hostid,))

        self.cursor.execute(q6, (hostid,))
        self.cursor.execute(q7, (hostid,))
        self.conn.commit()
        
        log.info("Initialized host: %s" % fqdn)
        
        return 0

    def storeUsage(self, hid, receivedstamp, clientstamp, pic):
        q = """insert into rrdqueue (ds_id, host_id, `timestamp`, 
                                     received, data)
               values (%s, %s, %s, %s, %s)"""

        data = pickle.loads(pic)
        dsid = self.getDSID('usage')
        self.cursor.execute(q, (dsid, hid, clientstamp, receivedstamp,
                                data['time']))
        self.conn.commit()

        return 0

    def setServiceStatus(self, service, succeed, timestamp, data=None):
        """Record a service status message into the database.
           timestamp should be a POSIX time...so time.time()
           
           data should be a Base64 encoded blob."""
       
        log.info("Received a %s status message from %s" % (service, 
                                                           self.client))
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

        if service == "usagelog":
            return self.storeUsage(id, date, clientstamp, data)

        if succeed:
            succeed = 1
        else:
            succeed = 0

        self.cursor.execute(q, (id, sid, clientstamp, date, succeed, data))
        self.conn.commit()
        return 0

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
        server = ezPyCrypto.key(config.privatekey)
        sig = server.signString(enc)

        ret = [enc, sig]

        return ret

    def convertApi_1(self, publicKey, uuid, rhnid, sig):
        """Find a client via its public key, and attach the UUID to it."""
       
        q = """update realmlinux set uuid = %s and rhnid = %s
               where host_id = %s"""

        if self.apiVersion < 1:
            raise APIFault("Invaild API version %s for convertApi_1()" % \
                           self.apiVersion)

        if self.getHostID() != None:
            log.debug("client already has its UUID registered: %s" % self.uuid)
            return 0

        # -1 equates to "I don't have an RHN ID"
        try:
            rhnid = int(rhnid)
            if rhnid == -1: 
                rhnid = None
        except ValueError:
            rhnid = None

        hostinfo = self.findHostByKey(publicKey)
        if hostinfo == None:
            log.warning("Cound not convert client to API 1.  Not registered?")
            log.warning("Hostname: %s   UUID: %s" % (self.client, self.uuid))
            return 10

        key = ezPyCrypto.key(hostinfo['publickey'])
        if not key.verifyString(uuid, sig):
            log.debug("Could not verify signature in convertApi_1()")
            return 1

        self.cursor.execute(q, (self.uuid, rhnid, hostinfo['host_id']))
        self.conn.commit()
        log.info("Converted UUID %s Host %s to APIv1" \
                 % (self.uuid, self.client))
        return 0

    def updateRHNSystemID(self, rhnid):
        "Client must be already verified.  Update the RHN ID."

        q = """update realmlinux set rhnid = %s where uuid = %s"""

        if rhnid == -1:
            # Can't marshal None
            rhnid = None

        self.cursor.execute(q, (rhnid, self.uuid))
        self.conn.commit()
        log.info("Updated RHN System ID for host %s" % self.client)

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

    def __getWebKs(self):
        """Find and return the web-kickstart config object"""
        
        os.chdir(sys.path[-1])
        wks = webKickstart.webKickstart("fakeurl", {})
        scList = wks.findFile(self.client, webKickstart.config.jumpstarts)
        if len(scList) == 0:
            raise Exception("No config for %s in %s" % (self.client,
                                       webKickstart.config.jumpstarts))
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


# Make things a little easier for the API module
Server = APIServer

