#!/usr/bin/python
#
# RealmLinux Manager -- client code
# Copyright (C) 2004 - 2010 NC State University
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
import os
import os.path
import re
import socket
import stat
import time
import optparse
import rpm
import logging
import uuid

from message   import Message
from xmlrpc    import doRPC
from constants import *

import clientconf
import ezPyCrypto
import xmlrpc

logger = logging.getLogger("rlmclient")

def isSupportOn():
    file = "/etc/sysconfig/support"
    regex = re.compile("^SUPPORT=yes")
    
    if not os.access(file, os.R_OK):
        return 0
    
    fd = open(file)
    for line in fd.readlines():
        if regex.match(line):
            return 1

    return 0


def getUUID():
    """Return my unique ID for this machine.  Returns None if we are not
       root and a UUID has not been previously created."""

    if not os.path.exists(uuidFile):
        u = str(uuid.uuid4())
        try:
            fd = open(uuidFile, 'w')
            fd.write(u + '\n')
            fd.close()
            os.chmod(uuidFile, 0644)
        except IOError:
            # We are not root!
            return None
    else:
        fd = open(uuidFile)
        u = fd.read().strip()
        fd.close()

    return u


def getRHNSystemID():
    "Return the RHN System ID or -1 if not present."

    file = "/etc/sysconfig/rhn/systemid"
    if not os.access(file, os.R_OK):
        return -1

    rhn = xmlrpc.parseSystemID(file)
    if rhn == None or rhn == {}:
        return -1

    id = rhn['system_id']
    if isinstance(id, str) and id.startswith('ID-'):
        return int(id[3:])
    else:
        return int(id)


def getDepartment():
    try:
        fd = open("/etc/rc.conf.d/HostDept")
        dept = fd.read().strip()
        fd.close()
    except IOError, e:
        dept = "ncsu"
   
    return dept


def getRPMDist():
    "Figure out my dist tag for this OS"

    packages = [('redhat-release', 'el'),
                ('centos-release', 'el'),
                ('fedora-release', 'fc'),
               ]
    ts = rpm.TransactionSet("", (rpm._RPMVSF_NOSIGNATURES or
                                 rpm.RPMVSF_NOHDRCHK or
                                 rpm._RPMVSF_NODIGESTS or
                                 rpm.RPMVSF_NEEDPAYLOAD))

    for pkg, prefix in packages:
        mi = ts.dbMatch('name', pkg)
        for h in mi:
            # If the Match Iterator is empty we don't get here
            if h['version'].endswith('Client'):
                version = h['version'][:-6]
            elif h['version'].endswith('Server'):
                version = h['version'][:-6]
            else:
                version = h['version']
            try:
                if int(version) < 6 and pgk[:-8] in ['redhat', 'centos']:
                    return "%s%s" % (prefix.upper(), version)
            except Exception:
                pass
            return "%s%s" % (prefix, version)

    return "Unknown"

def getVersion():
    "Return the version string for a Realm Linux product."

    packages = [('redhat-release', ''),
                ('centos-release', 'CentOS'),
                ('fedora-release', 'FC'),
               ]
    ts = rpm.TransactionSet("", (rpm._RPMVSF_NOSIGNATURES or
                                 rpm.RPMVSF_NOHDRCHK or
                                 rpm._RPMVSF_NODIGESTS or
                                 rpm.RPMVSF_NEEDPAYLOAD))

    for pkg, prefix in packages:
        mi = ts.dbMatch('name', pkg)
        for h in mi:
            # If the Match Iterator is empty we don't get here
            return "%s%s" % (prefix, h['version'])

    return "Unknown"
    

def saveKey(key):
    # make sure the key is written to disk

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


def getLocalKey():
    "Return an ezPyCrypto keypair for this local host."
    
    if not os.access(privateKey, os.R_OK):
        logger.error("Creating public/private keypair.")
        key = ezPyCrypto.key(1024)
        saveKey(key)
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


def doRegister(server):
    # Need a new public/private key pair, dept, and version
    # Generate new key pair
    keypair = getLocalKey()
    pubKey = keypair.exportKey()
    rhnid = getRHNSystemID()
    uuid = getUUID()

    ret = doRPC(server.register, pubKey, getDepartment(), getVersion(),
                uuid, rhnid)
    
    if ret == 0:
        return ret
    elif ret == 1:
        logger.error("Registration failed: Client already registered in database")
    elif ret == 2:
        logger.error("Registration failed: Client not in support database")
    elif ret == 3:
        logger.error(
                "Registration failed: Client did not register within 24 hours")
    elif ret == 4:
        logger.error("Registration failed: Client sent a malformed public key")
    elif ret == 99:
        logger.error("Registration failed: Server blew up -- Bad day.")
    else:
        logger.error("Registration failed with return code %s" % ret)
        
    return ret


def getUpdateConf(server):
    "Get the update.conf file"
    
    keypair = getLocalKey()
    uuid = getUUID()
    sig = keypair.signString(uuid)
   
    update = doRPC(server.getEncKeyFile, uuid, sig)
        
    if update == []:
        logger.error("Error receiving update.conf file")
        return
    
    # check sig
    serverKey = getRealmLinuxKey(server)
    if not serverKey.verifyString(update[0], update[1]):
        logger.error("ERROR: Encrypted update.conf did not verify.")
        return
    
    dec = keypair.decStringFromAscii(update[0])
    fd = open("/etc/update.conf", "w")
    fd.write(dec)
    fd.close()
    os.chmod("/etc/update.conf", 0600)


def getRealmLinuxKey(server):
    "Return the public key for Realm Linux."
        
    key = ezPyCrypto.key()

    if os.access(publicRLKey, os.R_OK):
        fd = open(publicRLKey)
        key.importKey(fd.read())
        fd.close()
    else:
        data = doRPC(server.getServerKey, getUUID())
        key.importKey(data)

        # We are at registration.  Save key
        fd = open(publicRLKey, "w")
        fd.write(key.exportKey())
        fd.close()

    return key


def isRegistered(server):
    """Return True if this machine is registered."""

    if not os.access("/etc/sysconfig/RLKeys", os.X_OK):
        os.mkdir("/etc/sysconfig/RLKeys", 0755)

    if not os.access(privateKey, os.R_OK):
        return False
   
    key = getLocalKey()
    uuid = getUUID()
    sig = key.signString(uuid)

    uuidRegistered = doRPC(server.isRegistered, uuid, sig)
    if not uuidRegistered:
        pubKey = key.exportKey()
        keysig = key.signString(pubKey)
        api = xmlrpc.apiVersion
        xmlrpc.apiVersion = 0
        keyRegistered = doRPC(server.isRegistered, pubKey, keysig)
        xmlrpc.apiVersion = api

        if keyRegistered:
            ret = doRPC(server.convertApi_1, uuid, getRHNSystemID(), 
                                             pubKey, sig)
            if ret == 0:
                uuidRegistered = doRPC(server.isRegistered, uuid, sig)

    return uuidRegistered


def doCheckIn(server):
    "Check in with the XMLRPC server."

    key = getLocalKey()
    uuid = getUUID()
    sig = key.signString(uuid)

    ret = doRPC(server.checkIn, uuid, sig)
        
    if ret == 0:
        pass
    elif ret == 1:
        logger.error("Checkin failed: Server could not verify our public key and sig.")
    elif ret == 2:
        logger.error("Checkin failed: Server did not find our database entry.")
    else:
        logger.error("Checkin failed with return code %s" % ret)


def doBlessing(server):
    """Administratively bless a client."""

    rhnid = getRHNSystemID()
    uuid = getUUID()
    fqdn = socket.getfqdn()

    if uuid == None:
        print "This client has not created its Universally Unique Identifier"
        print "(UUID). Please wait until the UUID is created before blessing"
        print "this machine.  It should be created within 4 hours."
        sys.exit(13)

    print "Hostname: %s" % fqdn
    print "The above hostname must match the A record for your IP address."
    print

    try:
        key = ezPyCrypto.key()
        fd = open(publicKey)
        key.importKey(fd.read())
    except Exception, e:
        logger.error("Blessing failed reading public key.  Error: %s" % str(e))
        print "Error reading public key file.  Cannot bless."
        print "Error was: %s" % str(e)
        sys.exit(12)

    pubKeyText = key.exportKey()
    print "Successfully imported client's public key."
    print

    file = os.path.join(blessings_dir, fqdn+".pub")
    try:
        fd = open(file, "w")
        fd.write(pubKeyText)
        fd.close()
    except Exception, e:
        logger.error("Blessing failed writing key file with error: %s" % str(e))
        print "An error occured: %s" % str(e)
        print "You must have permission to create Web-Kickstart configs to"
        print "administratively bless machines."
        sys.exit(10)

    print "Sending XMLRPC request..."
    ret = doRPC(server.bless, getDepartment(), getVersion(), uuid, rhnid)

    if ret != 0:
        logger.error("Blessing failed with return code %s" % ret, True)
    else:
        logger.error("Blessing successful")
        print "Blessing successful.  This machine is now a trusted machine"
        print "on NCSU's network."


def runQueue(server):
    """Process the message queue."""
    expire = time.time() - 3600 * 24 * 30 # 30 days ago (time.time() 
                                          # for python 2.2)

    key = getLocalKey()
    uuid = getUUID()
    sig = key.signString(uuid)

    queue = []

    if not os.access(mqueue, os.W_OK):
        # we are root, we should have write access, if not create it
        try:
            os.mkdir(mqueue)
            os.chmod(mqueue, 01777)
        except IOError, e:
            print "Error creating RLM queue directory: %s" % str(e)
            return

    for file in os.listdir(mqueue):
        m = Message()
        m.load(os.path.join(mqueue, file))

        tStamp = m.getTimeStamp()
        if tStamp is None or tStamp < expire:
            # If the message is 30 days told we aren't interested
            # This also removes corrupt messages
            m.remove()
        else:
            queue.append(m)

    for m in queue:
        code = m.send(server, uuid, sig)
        if code == 0:
            m.remove()
        else:
            # This could log...a lot...if client is not verified.
            logger.error("Failed to send message, return code %s" % code)


def main():
    """This either runs via a cron job to register and checkin
       with the trusted Realm Linux security stuffs or it can be
       called directly via 'ncsubless' to administratively register
       a machine."""

    parser = optparse.OptionParser()
    parser.add_option("-C", "--configfile", action="store",
                      default=defaultConfFiles,
                      dest="configfile",
                      help="Configuration file")

    (options, args) = parser.parse_args()

    URL = clientconf.initConfig(options.configfile)
    server = xmlrpc.setupServer(URL)

    if os.path.basename(sys.argv[0]) == "ncsubless":
        # called via ncsubless script
        doBlessing(server)
        return

    if os.getuid() != 0:
        print "You are not root.  Insert error message here."
        sys.exit(1)

    if not isRegistered(server):
        if doRegister(server) != 0:
            sys.exit()

    doCheckIn(server)

    if isSupportOn() and not os.access("/etc/update.conf", os.R_OK):
        getUpdateConf(server)

    runQueue(server)


if __name__ == "__main__":
    main()
