#!/usr/bin/python
                                                                                
##     RealmLinux Manager -- client code
##     Copyright (C) 2003 NC State University
##     Written by Jack Neely <jjneely@pams.ncsu.edu>

##     SDG

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
import os
import xmlrpclib
import re

sys.path.append("/afs/eos/project/realmlinux/py-modules")

import ezPyCrypto

# XMLRPC Interface
URL = "http://anduril.pams.ncsu.edu/~slack/realmkeys/handler.py"

# Locally stored keys
publicKey = "/etc/sysconfig/rkhost.pub"
privateKey = "/etc/sysconfig/rkhost.priv"

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

    server = xmlrpclib.ServerProxy(URL)
    try:
        test = server.hello()
    except Error, e:
        print "Hmmm...something goofed: " + str(v)
        sys.exit(1)
        
    return server


def getVersion():
    "Return the version string for a Realm Linux product."

    if os.access("/etc/redhat-release", os.R_OK):
        pipe = os.popen("/bin/rpm -q redhat-release --qf '%{version}'")
        version = pipe.read().strip()
        pipe.close()
        return version
    elif os.access("/etc/fedora-release", os.R_OK):
        pipe = os.popen("/bin/rpm -q fedora-release --qf '%{version}'")
        version = pipe.read().strip()
        pipe.close()
        return "FC%s" % version
    
                        
def doRegister():
    # Need a new public/private key pair, dept, and version
    # Generate new key pair
    keypair = ezPyCrypto.key(1024)
    pubKey = keypair.exportKey()
    privKey = keypair.exportKeyPrivate()

    # Store keys
    fd = open(publicKey, "w")
    fd.write(pubKey)
    fd.close()
    os.chmod(publicKey, 600)

    fd = open(privateKey, "w")
    fd.write(privKey)
    fd.close()
    os.chmod(privateKey, 600)

    # get department
    fd = open("/etc/rc.conf.d/HostDept")
    dept = fd.read().strip()

    server = getRPCObject()
    ret = server.register(pubKey, dept, getVersion())
    if ret != 0:
        print "Registration failed with return code %s" % ret


def doCheckIn():
    # Need our public key and then a sig on it
    pass
    

def main():
    """Run via a cron job.  Figure out if we need to register or just
       check in.  Then do the proper action."""
    
    if os.getuid() != 0:
        print "You are not root.  Insert error message here."
        
    if os.access("/etc/update.conf", os.W_OK):
        register = 0
    else:
        register = 1

    if register == 1:
        if not isSupported():
            print "Your machine is not configured for support."
            return 1
        else:
            doRegister()

    else:
        doCheckIn()


if __name__ == "__main__":
    main()
