#!/usr/bin/python
#
# RealmLinux Manager -- Main server object
# Copyright (C) 2003, 2005 - 2010 NC State University
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
from rlattributes import RLAttributes
from sessions import Session

import webKickstart.libwebks

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

        global config
        if config is None:        # Hmmm...check again
            import configDragon
            config = configDragon.config
        if config is None:        # Still?  Bail
            raise StandardError("Configuration environment not setup")

        self.apiVersion = apiVersion
        self.client = client
        self.uuid = uuid
        self.hostid = None

        if self.apiVersion > 0 and self.uuid == None:
            raise APIFault("Client must supply its UUID with this API version")

        if self.apiVersion == 0 and self.uuid != None:
            raise APIFault("Client passed in a UUID for invalid API version")

        log.debug("API version %s started for client: %s" % (self.apiVersion,
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
        
        #log.debug("In isRegistered()")
        log.info("Client '%s' identifies with UUID '%s'" % \
                 (self.client, self.uuid))

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
        if not self.cmpHostname(hostinfo['hostname'], self.client):
            self.changeHostname(hostinfo['host_id'], hostinfo['hostname'],
                                self.client)

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
        self.changeHostname(hostinfo['host_id'], hostinfo['hostname'], 
                            self.client)

        return hostinfo['publickey']

    def resetHostname(self):
        """Allow a logged in host to update its hostname."""

        host_id = self.getHostID()
        oldname = self.getHostName(host_id) # Query the DB for the old name
        if self.cmpHostname(self.client, oldname):
            # Name change is complete...it didn't need updating
            return 0

        self.changeHostname(host_id, oldname, self.client)
        return 0

    def cmpHostname(self, h1, h2):
        "Compare host names.  Handle the :ID:foo parts"

        i = h1.find(":ID:")
        if i == -1:
            t1 = h1
        else:
            t1 = h1[:i]
        i = h2.find(":ID:")
        if i == -1:
            t2 = h2
        else:
            t2 = h2[:i]

        return t1 == t2

    def changeHostname(self, hostID, oldname, newname):
        q1 = """select host_id from realmlinux where hostname = %s"""
        q2 = """update realmlinux set hostname = %s where host_id = %s"""

        # Change the hostname for this client if it exists
        self.cursor.execute(q1, (newname,))
        if self.cursor.rowcount > 0:
            # Can only be one match -- see DB schema
            hid = self.cursor.fetchone()[0]
            log.info("changeHostname: duplicate host renamed %s:ID:%s" %
                      (newname, hid))
            self.cursor.execute(q2, ("%s:ID:%s" % (newname, hid), hid))

        if self.apiVersion < 1:
            # XXX: unknown host names are most likely masquraded hosts and we
            # don't know how to better handle this right now
            if not oldname.startswith('unknown - ID'):
                # Now update the registration we found
                log.info("apiVersion 0 client %s changing hostname to %s" %
                         (oldname, newname))
                self.cursor.execute(q2, (newname, hostID))
        else:
            # UUID based version APIs track hosts not by hostname, just do it
            log.info("Hostname update %s -> %s" % (oldname, newname))
            self.cursor.execute(q2, (newname, hostID))
        
        self.conn.commit()
    
    def register(self, publicKey, dept, version, rhnid, sid):
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
        
        if self.apiVersion >= 2:
            if sid is not None and sid != '':
                sess = Session(sid=sid, secret=config.secret)
                if sess.isNew() or not sess.isValid():
                    # We have an invalid session hash, its expired or
                    # just junk.  NoSupport
                    return self.createNoSupport(publicKey, dept, version, 
                                                rhnid)
                else:
                    log.info("Registering support for %s" % self.client)
                    return self.__register(publicKey, dept, version, 
                                           rhnid, sess['hostid'])
            else:
                # No session to match a previous initHost.  
                # Not installed via Web-Kickstart?
                return self.createNoSupport(publicKey, dept, version, rhnid)

        ### The following is API Versions 1 and 0 ###

        # check to see if client has been logged in DB
        self.cursor.execute("""select installdate, host_id
            from realmlinux where 
            hostname=%s and support=1""", (self.client,))
        result = resultSet(self.cursor)
        if not result.rowcount() > 0:
            # SQL query returned zero rows...this client isn't logged
            # to be registered with support (old return code 2)
            return self.createNoSupport(publicKey, dept, version, rhnid)

        # Check the Time window for 24 hours
        installDate = result['installdate']
        if datetime.today() - timedelta(days=1) > installDate:
            # Client did not register inside 24 hours
            log.info("Client %s attempted to register outside security " \
                     "window" % self.client)
            # Old return code 3
            return self.createNoSupport(publicKey, dept, version, rhnid)

        log.info("Registering support for %s" % self.client)
        return self.__register(publicKey, dept, version, rhnid, 
                               result['host_id'])
        

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
            # XXX: We have no source for the dept.  As this is to be a 
            # trusted client, we trust the client's reported dept value
            hid, sid = self.initHost(self.client, 1, blessing=True, dept=dept)
        else:
            hid = self.cursor.fetchone()[0]
            q = """update realmlinux set support = 1 where host_id = %s"""
            self.cursor.execute(q, (hid,))

        # Update db 
        ret = self.__register(publicKey, dept, version, rhnid, hid)

        # Log history information
        if ret == 0:
            self.storeHistoryEvent('blessing', hid, self.client)
            log.info("Blessing of %s successful." % self.client)
        
        try:
            os.unlink(file)
        except OSError, e:
            pass

        return ret
            
    def createNoSupport(self, publicKey, dept, version, rhnid):
        "Create a db entry for a non supported client."

        log.info("Registering no-support for %s" % self.client)

        # No-supports are initially set to dept=ncsu
        hid, sid = self.initHost(self.client, 0, dept="ncsu")
        return self.__register(publicKey, dept, version, rhnid, hid)

    def __register(self, publicKey, dept, version, rhnid, host_id):
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
            # initHost now sets the dept field

            q1 = "delete from hostkeys where host_id = %s"
            q2 = """update realmlinux 
                   set recvdkey=1, version=%s, uuid=%s, rhnid=%s
                   where host_id=%s"""
            q3 = "insert into hostkeys (host_id, publickey) values (%s, %s)"

            self.cursor.execute(q1, (host_id,))
            if self.apiVersion > 0:
                self.cursor.execute(q2, (version, self.uuid, 
                                         rhnid, host_id))
            else:
                self.cursor.execute(q2, (version, None, None, host_id))
            self.cursor.execute(q3, (host_id, publicKey))
            self.cursor.execute("""delete from lastheard where host_id = %s""",
                                (host_id,))
            self.cursor.execute("""insert into lastheard (host_id, `timestamp`)
                                   values (%s, %s)""", (host_id, date))
            self.conn.commit()
        except MySQLdb.Warning, e:
            # What's this about?
            log.critical("MySQL Waring: %s\n" % str(e))
            return 99

        return 0
    
    
    def checkIn(self, uuid, sig, dept=None):
        """Workstation checking in.  Update status in DB."""
       
        q1 = """update realmlinux set dept_id = %s where host_id = %s"""
        q2 = """update lastheard set `timestamp` = %s where host_id = %s"""

        date = datetime.today()

        if not self.verifyClient(uuid, sig):
            return 1

        id = self.getHostID()
        if id == None:
            # Cannot check in non-registered client
            return 2

        self.cursor.execute(q2, (date, id))

        if self.apiVersion >= 2:
            dept = dept.strip()
            if self.getHostDept(id) != dept and dept != '':
                dept_id = self.getDeptID(dept)
                self.cursor.execute(q1, (dept_id, id))

        self.conn.commit()

        return 0

    def getActivationKey(self, publicKey, sig):
        """Returns the current RHN activation key for this host."""

        if not self.verifyClient(publicKey, sig):
            # verification error
            return 1

        log.info("Client %s requests activation key" % self.client)

        libks = self.__getWebKs()
        keys = libks.getKeys(self.client)
        if keys.has_key('enable') and keys['enable'].hasMember('activationkey'):
            key = keys['enable'].activationkey.verbatim()
        else:
            # *sigh* no key
            profile = libks.getProfileKeys(self.client)
            if profile.has_key('defaultActivation'):
                key = profile['defaultActivation']
            else:
                key = None

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

    def setDeptBcfg2(self, deptName, bcfg2args, url):
        """Set bcfg2.init attribute on the dept name given"""
        rla = RLAttributes()
        dept_id = self.getDeptID(deptName)
        aptr = rla.getDeptAttrPtr(dept_id)

        rla.setAttribute(aptr, 'bcfg2.init', bcfg2args)
        rla.setAttribute(aptr, 'bcfg2.url', url)

        # XXX: Return code / check?
        return 0

    def getBcfg2Bootstrap(self):
        """Return the bcfg2.* attributes for bcfg2 bootstrapping.  This
           is for authenticated clients only."""

        rla = RLAttributes()
        host_id = self.getHostID()
        if host_id == None:
            # Cannot check in non-registered client
            return (2, {})
        if not self.isSupported():
            return (3, {})

        m, a = rla.hostAttrs(host_id)
        d = {}
        for k in a.keys():
            if k.startswith('bcfg2.'):
                d[k[6:]] = a[k]

        return (0, d)

    def loadWebKickstart(self):
        rla = RLAttributes()
        try:
            ret = rla.importWebKickstart(self.getHostID())
        except Exception, e:
            log.warning("Exception loading web-kickstart: %s" % str(e))
            return 2

        if ret:
            return 0
        else:
            return 3 # No Web-Kickstart config file?

    def dumpClients(self):
        """This function dumps out a report sent out over XMLRPC."""
        q = """select r.hostname, IFNULL(r.uuid, "") as uuid,
                   IFNULL(r.rhnid, "") as rhnid, 
                   DATE_FORMAT(r.installdate, "%a %b %d %H:%M:%S %Y") 
                       as installdate,
                   r.version, r.support, d.name
               from realmlinux as r, dept as d
               where r.dept_id = d.dept_id"""

        self.cursor.execute(q)
        return (0, resultSet(self.cursor).dump())

    def initHost(self, fqdn, support, blessing=False, dept='ncsu'):
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
        dept = self.getDeptID(dept)
        self.cursor.execute(q1, (fqdn,))
        if self.cursor.rowcount == 0:
            # Create a new entry
            self.cursor.execute(q3, (fqdn, date, dept, support))
            self.cursor.execute(q1, (fqdn,))
            hostid = self.cursor.fetchone()[0]
        elif self.apiVersion < 2:
            # reuse the old entry
            hostid = self.cursor.fetchone()[0]
            self.cursor.execute(q2, (date, dept, support, hostid))
            self.cursor.execute(q4, (hostid,))
            self.cursor.execute(q5, (hostid,))
        else:
            # For APIv2 if this is a duplicate, rename the old host
            # and create a completely new entry rather than reuse an old
            oldhostid = self.cursor.fetchone()[0]
            self.changeHostname(oldhostid, fqdn, 
                                "%s:ID:%s" % (fqdn, oldhostid))
            self.cursor.execute(q3, (fqdn, date, dept, support))
            self.cursor.execute(q1, (fqdn,))
            hostid = self.cursor.fetchone()[0]

        self.cursor.execute(q6, (hostid,))
        self.cursor.execute(q7, (hostid,))
        self.conn.commit()

        # Attributes
        rla = RLAttributes()
        rla.removeAllHostAttrs(hostid)
        rla.importWebKickstart(hostid)
        
        log.info("Initialized host: %s" % fqdn)
        if support:
            htype = 'install_support'
        else:
            htype = 'install_nosupport'
        if not blessing:
            self.storeHistoryEvent(htype, hostid, fqdn)

        # Generate a unique session so that we can ID this host later
        # 43,200 seconds = 1 day
        sess = Session(lifetime=43200, secret=config.secret)
        sess['fqdn'] = fqdn
        sess['hostid'] = hostid
        sess.save()
        
        return hostid, sess.sid

    def setUsageSync(self, host_id, timestamp):
        # We need to know when its safe to populate the RRDs for
        # the usage information per host.  This must be done sequentially.
        q = """insert into rrdqueue (ds_id, host_id, `timestamp`) 
               values (%s, %s, %s)"""

        ds_id = self.getDSID('usagesync')
        self.cursor.execute(q, (ds_id, host_id, timestamp))
        # self.conn.commit() purposely left out

    def storeUsage(self, hid, receivedstamp, clientstamp, pic):
        q = """insert into rrdqueue (ds_id, host_id, `timestamp`, 
                                     received, data)
               values (%s, %s, %s, %s, %s)"""

        data = pickle.loads(pic)
        dsid = self.getDSID('usage')
        self.cursor.execute(q, (dsid, hid, clientstamp, receivedstamp,
                                data['time']))

        if data.has_key('sync') and data['sync']:
            self.setUsageSync(hid, clientstamp)

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

        if data is not None and len(data) > 5242880:
            # Ugh...more than 5MiB?  Snip this...
            log.info("Greater than 5MiB status message from %s" % \
                     self.client)
            data = data[0:5242880] + "\n\n< SNIP!  More than 5MiB >\n"

        if service == "usagelog":
            return self.storeUsage(id, date, clientstamp, data)
        if service == "boot":
            self.setUsageSync(id, clientstamp)

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
       
        q = """update realmlinux set uuid = %s, rhnid = %s
               where host_id = %s"""

        if self.apiVersion < 1:
            raise APIFault("Invaild API version %s for convertApi_1()" % \
                           self.apiVersion)

        # This will generate a warning log because we can't find UUID
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

    def signCert(self, fingerprint):
        """Instruct the Puppet Master to sign the certificate for
           this machine."""

        pass

    def __makeUpdatesConf(self):
        """Generate the updates.conf file and return a string."""

        libks = self.__getWebKs()
        ks = libks.getKeys(self.client)
        if not ks.has_key('users'):
            usersdata = "users default %s" % config.defaultkey
        else:
            # a list of the options passed to the 'users' key
            usersdata = "users " + ks['users'].verbatim()
        
        # root data
        if not ks.has_key('root'):
            rootdata = "root default %s" % config.defaultkey
        else:
            rootdata = "root " + ks['root'].verbatim()

        # clusters
        clusterdata = ""
        if ks.has_key('cluster'):
            for row in ks['cluster'].allRows():
                clusterdata = "%scluster %s\n" % (clusterdata, 
                              row.verbatim())

        return "%s\n%s\n%s" % (usersdata, rootdata, clusterdata)

    def __getWebKs(self):
        """Find and return the web-kickstart config object"""

        return webKickstart.libwebks.LibWebKickstart(config.webks_dir)


# Make things a little easier for the API module
Server = APIServer

