#!/usr/bin/python
#
# RealmLinux Manager -- client code
# Copyright (C) 2004 - 2006 NC State University
# Written by Jack Neely <jjneely@pams.ncsu.edu>
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
import xmlrpclib
import re
import syslog
import socket
import stat
import ezPyCrypto
import time
import urllib2
import httplib
import sha
import pickle
import optparse

# XMLRPC Interface
#URL = "https://secure.linux.ncsu.edu/xmlrpc/handler.py"
URL = "https://anduril.unity.ncsu.edu/~slack/realmkeys/handler.py"

# Locally stored keys
publicKey = "/etc/sysconfig/RLKeys/rkhost.pub"
privateKey = "/etc/sysconfig/RLKeys/rkhost.priv"
publicRLKey = "/etc/sysconfig/RLKeys/realmlinux.pub"

# Where blessings go
blessings_dir = "/afs/bp/system/config/linux-kickstart/blessings"
#blessings_dir = "/ncsu/jjneely/slack2/keys"

# Message Queue Directory
mqueue = "/var/spool/rlmqueue"

class Message(object):

    def __init__(self):
        self.data = {}
        self.sum = None

    def _setCheckSum(self):
        # dicts are unordered so we need to impose some order to checksum
        keys = self.data.keys()
        keys.sort()
        s = ""
        for key in keys:
            s = "%s%s:%s\n" % (s, key, self.data[key])
        self.sum = sha.new(s).hexdigest()

    def save(self):
        # Possibly raises IOError
        if not self.data.has_key('timestamp'):
            self.setTimeStamp()
        if self.sum == None:
            self._setCheckSum()

        filename = os.path.join(mqueue, self.sum)
        blob = pickle.dumps(self.data)
        fd = open(filename, 'w')
        fd.write(blob)
        fd.close()

    def send(self, server, text, sig):
        doRPC(server.message, text, sig, self.data)
        return True

    def remove(self):
        if self.sum != None:
            filename = os.path.join(mqueue, self.sum)
            try:
                os.unlink(filename)
            except (IOError, OSError):
                pass

    def load(self, filename):
        # Possibly raises IOError
        fd = open(filename)
        blob = fd.read()
        fd.close()
        self.data = pickle.loads(blob)
        self._setCheckSum()
        if self.sum != os.path.basename(filename):
            print "ERROR: Checksum does not equal filename."
            print "Checksum: %s" % self.sum
            print "Filename: %s" % filename

    def setType(self, t):
        self.sum = None
        self.data['type'] = t

    def setSuccess(self, bool):
        self.sum = None
        self.data['success'] = bool

    def setTimeStamp(self):
        self.sum = None
        self.data['timestamp'] = time.time()

    def setMessage(self, data):
        self.sum = None
        self.data['data'] = data

    def getTimeStamp(self):
        if self.data.has_key('timestamp'):
            return self.data['timestamp']
        else:
            return None


def error(message, verbose=False):
    "Log an error message to syslog."

    if verbose:
        print message
        
    priority = syslog.LOG_ERR or syslog.LOG_USER
    syslog.syslog(priority, "Realm Linux Support: %s" % message)


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


def doRPC(method, *params):
    "Return the xmlrpc opject we want."

    for i in range(5):
        try:
            return apply(method, params)
        except xmlrpclib.Error, e:
            error("XMLRPC Error: " + str(e))
        except socket.error, e:
            error("Socket Error: %s" % str(e))
        except socket.sslerror, e:
            error("Socket SSL Error: %s" % str(e))
        except AssertionError, e:
            error("Assertion Error (this is weird): %s" % str(e))
        except httplib.IncompleteRead, e:
            error("HTTP library reported an Incomplete Read error: %s" % str(e))
        except urllib2.HTTPError, e:
            msg = "\nAn HTTP error occurred:\n"
            msg = msg + "URL: %s\n" % e.filename
            msg = msg + "Status Code: %s\n" % e.code
            msg = msg + "Error Message: %s\n" % e.msg
            error(msg)

        if i < 5:
            time.sleep(i*3)
        
    error("Giving up trying XMLRPC")
    print "Error: Could not talk to server at %s" % URL
    sys.exit(1)


def getDepartment():
    try:
        fd = open("/etc/rc.conf.d/HostDept")
        dept = fd.read().strip()
        fd.close()
    except IOError, e:
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
    
    ret = doRPC(server.register, pubKey, getDepartment(), getVersion())
    
    if ret == 0:
        return ret
    elif ret == 1:
        error("Registration failed: Client already registered in database")
    elif ret == 2:
        error("Registration failed: Client not in support database")
    elif ret == 3:
        error("Registration failed: Client did not register within 24 hours")
    else:
        error("Registration failed with return code %s" % ret)
        
    return ret


def getUpdateConf(server):
    "Get the update.conf file"
    
    keypair = getLocalKey()
    pubKey = keypair.exportKey()
    sig = keypair.signString(pubKey)
   
    update = doRPC(server.getEncKeyFile, pubKey, sig)
        
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
        data = doRPC(server.getServerKey)
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

    ret = doRPC(server.checkIn, pubKeyText, sig)
        
    if ret != 0:
        error("Checkin failed with return code %s" % ret)


def doBlessing(server):
    """Administratively bless a client."""

    fqdn = socket.getfqdn()
    
    print "Hostname: %s" % fqdn
    print "The above hostname must match the A record for your IP address."
    print

    try:
        key = ezPyCrypto.key()
        fd = open(publicKey)
        key.importKey(fd.read())
    except Exception, e:
        error("Blessing failed reading public key.  Error: %s" % str(e))
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
        error("Blessing failed writing key file with error: %s" % str(e))
        print "An error occured: %s" % str(e)
        print "You must have permission to create Web-Kickstart configs to"
        print "administratively bless machines."
        sys.exit(10)

    print "Sending XMLRPC request..."
    ret = doRPC(server.bless, getDepartment(), getVersion())

    if ret != 0:
        error("Blessing failed with return code %s" % ret, True)
    else:
        error("Blessing successful")
        print "Blessing successful.  This machine is now a trusted machine"
        print "on NCSU's network."


def runQueue(server):
    """Process the message queue."""
    expire = time.time() - 3600 * 24 * 30 # 30 days ago (time.time() 
                                          # for python 2.2)

    key = getLocalKey()
    pubKeyText = key.exportKey()
    sig = key.signString(pubKeyText)

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

        if m.getTimeStamp() < expire:
            # If the message is 30 days told we aren't interested
            m.remove()
        else:
            queue.append(m)

    for m in queue:
        if m.send(server, pubKeyText, sig):
            m.remove()


def doReport():
    usage = """Realm Linux Management report tool.  Licensed under the 
GNU General Public License.
ncsureport --service <--ok|--fail> --message <file>"""
    parser = optparse.OptionParser(usage)
    parser.add_option("-s", "--service", action="store", default=None,
                     dest="service", help="Message/service type to send.")
    parser.add_option("-o", "--ok", action="store_true", default=None,
                     dest="ok", help="Service is a success.")
    parser.add_option("-f", "--fail", action="store_true", default=None,
                     dest="fail", help="Service is a failure.")
    parser.add_option("-m", "--message", action="store", default=None,
                     dest="message", help="Filename or '-' of message to send.")

    opts, args = parser.parse_args(sys.argv[1:])
    if opts.ok == None and opts.fail == None:
        parser.print_help()
        return

    if opts.service == None or opts.message == None:
        parser.print_help()
        return

    success = opts.ok == True
    if opts.message == "-":
        fd = sys.stdin
    else:
        try:
            fd = open(opts.message)
        except IOError, e:
            print "Count not open file: %s" % opts.message
            return

    m = Message()
    m.setType(opts.service)
    m.setSuccess(success)
    m.setMessage(fd.read())
    try:
        m.save()
    except IOError, e:
        print "There was an error queuing your message: %s" % str(e)
        print "Message will not be sent."

    
def main():
    """This either runs via a cron job to register and checkin
       with the trusted Realm Linux security stuffs or it can be
       called directly via 'ncsubless' to administratively register
       a machine."""

    server = xmlrpclib.ServerProxy(URL)

    if os.path.basename(sys.argv[0]) == "ncsubless":
        # called via ncsubless script
        doBlessing(server)
        return

    if os.path.basename(sys.argv[0]) == "ncsureport":
        doReport()
        return
    
    if os.getuid() != 0:
        print "You are not root.  Insert error message here."
        sys.exit(1)
        
    if not doRPC(server.isRegistered):
        if not os.access("/etc/sysconfig/RLKeys", os.X_OK):
            os.mkdir("/etc/sysconfig/RLKeys", 0755)
        
        if doRegister(server) != 0:
            sys.exit()

    doCheckIn(server)

    if isSupportOn() and not os.access("/etc/update.conf", os.R_OK):
        getUpdateConf(server)

    runQueue(server)


if __name__ == "__main__":
    main()
