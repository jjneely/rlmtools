#!/usr/bin/python
#
#     RealmLinux Manager -- client code
#     Copyright (C) 2004 NC State University
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
import os
import os.path
import xmlrpclib
import re
import syslog
import socket
import stat
import ezPyCrypto

# XMLRPC Interface
#URL = "https://secure.linux.ncsu.edu/xmlrpc/handler.py"
URL = "https://anduril.pams.ncsu.edu/~slack/realmkeys/handler.py"

# Locally stored keys
publicKey = "/etc/sysconfig/RLKeys/rkhost.pub"
privateKey = "/etc/sysconfig/RLKeys/rkhost.priv"
publicRLKey = "/etc/sysconfig/RLKeys/realmlinux.pub"

# Where blessings go
#blessings_dir = "/afs/bp/system/config/linux-kickstart/blessings"
blessings_dir = "/home/slack/projects/tmp/keys"

def error(message, verbose=False):
    "Log an error message to syslog."

    if verbose:
        print message
        
    priority = syslog.LOG_ERR or syslog.LOG_USER
    syslog.syslog(priority, "Realm Linux Support: %s" % message)


def isSupported():
    file = "/etc/sysconfig/support"
    regex = re.compile("^SUPPORT=yes")
    
    if not os.access(file, os.R_OK):
        return 0
    
    fd = open(file)
    for line in fd.readlines():
        if regex.match(line):
            return 1

    return 0


def getRPCObject():
    "Return the xmlrpc opject we want."

    try:
        server = xmlrpclib.ServerProxy(URL)
        test = server.hello()
    except xmlrpclib.Error, e:
        error("Error creating XMLRPC object: " + str(e))
        sys.exit(1)
    except socket.error, e:
        error("Socket Error: %s" % str(e))
        sys.exit(1)
    except socket.sslerror, e:
        error("Socket Error: %s" % str(e))
        sys.exit(1)
    except AssertionError, e:
        error("Hell, it Broke: %s" % str(e))
        sys.exit(1)
        
    return server


def getDepartment():
    try:
        fd = open("/etc/rc.conf.d/HostDept")
        dept = fd.read().strip()
        fd.close()
    except OSError, e:
        dept = "ncsu"
   
    return dept


def getVersion():
    "Return the version string for a Realm Linux product."

    if os.path.exists("/etc/redhat-release") and not os.path.islink("/etc/redhat-release"):
        pipe = os.popen("/bin/rpm -q redhat-release --qf '%{version}'")
        version = pipe.read().strip()
        pipe.close()
        return version
    elif os.path.exists("/etc/fedora-release"):
        pipe = os.popen("/bin/rpm -q fedora-release --qf '%{version}'")
        version = pipe.read().strip()
        pipe.close()
        return "FC%s" % version
    else:
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


def doRegister(server):
    # Need a new public/private key pair, dept, and version
    # Generate new key pair
    keypair = getLocalKey()
    pubKey = keypair.exportKey()

    saveKey(keypair)
    
    try:
        ret = server.register(pubKey, getDepartment(), getVersion())
    except xmlrpclib.Fault, e:
        error("Exception Occured: %s" % str(e))
        sys.exit(1)
        
    if ret != 0:
        error("Registration failed with return code %s" % ret)
        
    return ret


def getUpdateConf(server):
    "Get the update.conf file"
    
    keypair = getLocalKey()
    pubKey = keypair.exportKey()
    sig = keypair.signString(pubKey)
   
    try:
        update = server.getEncKeyFile(pubKey, sig)
    except xmlrpclib.Fault, e:
        error("Exception Occured: %s" % str(e))
        sys.exit(1)
        
    if update == []:
        error("Error receiving update.conf file")
        return
    
    # check sig
    serverKey = getRealmLinuxKey(server)
    if not serverKey.verifyString(update[0], update[1]):
        error("ERROR: Encrypted update.conf did not verify.")
        return
    
    dec = keypair.decStringFromAscii(update[0])
    fd = open("/etc/update.conf", "w")
    fd.write(dec)
    fd.close()
    os.chmod("/etc/update.conf", 0600)


def getLocalKey():
    "Return an ezPyCrypto keypair for this local host."
    
    if not os.access(privateKey, os.R_OK):
        error("Creating public/private keypair.")
        key = ezPyCrypto.key(1024)
    else: 
        # Check bits
        mode = os.stat(publicKey).st_mode
        if not stat.S_IMODE(mode) == 0644:
            os.chmod(publicKey, 0644)

        fd = open(privateKey)
        privKeyText = fd.read()
        fd.close()

        key = ezPyCrypto.key()
        key.importKey(privKeyText)

    return key


def getRealmLinuxKey(server):
    "Return the public key for Realm Linux."
        
    key = ezPyCrypto.key()

    if os.access(publicRLKey, os.R_OK):
        fd = open(publicRLKey)
        key.importKey(fd.read())
        fd.close()
    else:
        data = server.getServerKey()
        key.importKey(data)

        # We are at registration.  Save key
        fd = open(publicRLKey, "w")
        fd.write(key.exportKey())
        fd.close()

    return key


def doCheckIn(server):
    "Check in with the XMLRPC server."

    key = getLocalKey()
    pubKeyText = key.exportKey()
    sig = key.signString(pubKeyText)

    try:
        ret = server.checkIn(pubKeyText, sig)
    except AssertionError, e:
        # Sigh...this appears to be a bug in httplib when the server
        # craps out on us.  Here, lets just ignore and checkIn() later
        error("AssertionError cought from httplib...exiting")
        ret = -1
        
    if ret != 0:
        error("Checkin failed with return code %s" % ret)


def doBlessing(server):
    """Administratively bless a client."""

    fqdn = socket.getfqdn()
    key = getLocalKey()
    pubKeyText = key.exportKey()
    
    print "Hostname: %s" % fqdn
    print "The above hostname must match the A record for your IP address."
    print

    file = os.path.join(blessings_dir, fqdn+".pub")
    try:
        fd = open(file, "w")
        fd.write(pubKeyText)
        fd.close()
    except Exception, e:
        error("Blessing failed writing key file with error: %s" % str(e))
        print "An error occured: %s" % str(e)
        print "You must have permission to create Web-Kickstart configs to"
        print "administratively bless machines."
        sys.exit(10)

    print "Sending XMLRPC request..."
    try:
        ret = server.bless(getDepartment(), getVersion())
    except AssertionError, e:
        error("Blessing failed with AssertionError: %s" % str(e))
        print "A communications error occured.  Please try again."
        sys.exit(11)

    if ret != 0:
        error("Blessing failed with return code %s" % ret, True)
    else:
        error("Blessing successful")
        print "Blessing successful.  This machine is now a trusted machine"
        print "on NCSU's network."

    
def main():
    """This either runs via a cron job to register and checkin
       with the trusted Realm Linux security stuffs or it can be
       called directly via 'ncsubless' to administratively register
       a machine."""

    if sys.argv[0] == "ncsubless":
        # called via ncsubless script
        doBlessing(getRPCObject())
        return
    
    if os.getuid() != 0:
        print "You are not root.  Insert error message here."
        sys.exit(1)
        
    server = getRPCObject()
    if not server.isRegistered():
        if not isSupported():
            error("Your machine is not configured for support.")
            return 1
        
        else:
            if not os.access("/etc/sysconfig/RLKeys", os.X_OK):
                os.mkdir("/etc/sysconfig/RLKeys", 0755)
        
            if doRegister(server) != 0:
                sys.exit()

    doCheckIn(server)

    if not os.access("/etc/update.conf", os.R_OK):
        getUpdateConf(server)


if __name__ == "__main__":
    main()
