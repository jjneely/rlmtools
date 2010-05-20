##     RealmLinux Manager XMLRPC Exposed API
##     Copyright (C) 2003 - 2005 NC State University
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

# Defines list of functions that are exported via the XML-RPC server.
# You can import modules in this file and then list the module name
# in this list.  That module will then need a __APT list of the functions
# and/or modules that it exposes.

import socket
import logging
import apiServer as server

from xmlrpclib import Fault

try:
    from mod_python import apache
except ImportError:
    # Not running under mod_python -- testing harness
    apache = None
    import cherrypy

log = logging.getLogger("xmlrpc")

__API__ = ['hello',
           'register',
           'checkIn',
           'bless',
           'message',
           'updateRHNSystemID',
           'getAddress',

           'initHost',
           'setDeptBcfg2',
           'getDeptBcfg2',
           'loadWebKickstart',
           'dumpClients',

           'getServerKey',
           'getEncKeyFile',
           'getActivationKey',

           'isRegistered',
           'isSupported',

           'convertApi_1',
          ]


def hello(apiVersion):
    return "Hello World"


def getAddress(apiVersion):
    """Return the ip/fqdn address pair of the calling client.  This is
       the address as viewed from the RLMTools server."""

    if apache is not None:
        ip = req.get_remote_host(apache.REMOTE_NOLOOKUP)
    else:
        # Part of cherrypy test harness
        try:
            ip = cherrypy.request.remote.ip
        except AttributeError:
            ip = cherrypy.request.remote_addr

    try:
        addr = socket.gethostbyaddr(ip)
    except socket.herror, e:
        if e[0] == 0:
            # No error...IP does not resolve
            log.warning("Request from %s which does not resolve" % ip)
            addr = [ip]
        else:
            log.error("HELP! socket.gethostbyaddr(%s) blew up with: %s" \
                    % (ip, e))
            raise

    return ip, addr[0]

def getHostName():
    """Digs out the hostname from the headers.  This identifies who we
       say we are."""
    
    return getAddress(1)[1]


def getServerKey(apiVersion, uuid=None):
    """Return the Server's public key"""
    
    srv = server.Server(apiVersion, getHostName(), uuid)
    ret = srv.getPublicKey()
    return ret
    

def register(apiVersion, publicKey, dept, version, uuid=None, rhnid=None):
    """Workstation requests registration.  Check DB and register host as
       appropiate.  A false return code means that registration failed."""
    
    s = server.Server(apiVersion, getHostName(), uuid)
    ret = s.register(publicKey, dept, version, rhnid)
    return ret


def bless(apiVersion, dept, version, uuid=None, rhnid=None):
    """Administratively bless a workstation."""

    s = server.Server(apiVersion, getHostName(), uuid)
    ret = s.bless(dept, version, rhnid)
    return ret

def resetHostname(apiVersion, uuid, sig):
    s = server.Server(apiVersion, getHostName(), uuid)

    if apiVersion < 2:
        # This function doesn't exist on apiVersions < 2
        return 1
    if not s.verifyClient(uuid, sig):
        return 1

    return s.resetHostname()

def message(apiVersion, publicKey, sig, dict):
    """Log a message from a client."""
    if apiVersion == 0:
        s = server.Server(apiVersion, getHostName())
    else:
        s = server.Server(apiVersion, getHostName(), uuid=publicKey)

    if not s.verifyClient(publicKey, sig):
        return 1

    ret = s.setServiceStatus(dict['type'],
                             dict['success'], 
                             dict['timestamp'],
                             dict['data'])
    return ret


def initHost(apiVersion, secret, fqdn):
    """API call for Web-Kickstart to initialize a host in the database.
       Protected by the knowing of a secret."""
    
    if apiVersion > 0:
        # Supply a fake UUID, its never used with initHost()
        s = server.Server(apiVersion, fqdn, uuid="foobarbaz")
    else:
        s = server.Server(apiVersion, fqdn)

    if not s.verifySecret(secret):
        log.warning("initHost() called with bad secret")
        return 1

    s.initHost(fqdn, support=1)  # returns host_id
    return 0


def setDeptBcfg2(apiVersion, secret, deptName, bcfg2args, url):
    """Set the bcfg2.init, bcfg2.url attributes for the given department name.
       You need the admin secret to do so."""

    if apiVersion < 2:
        # This function doesn't exist on apiVersions < 2
        raise Fault(1, "Method 'setDeptBcfg2' does not exist at this "
                       "API version")
    s = server.Server(apiVersion, "fqdn", "uuid")
    if not s.verifySecret(secret):
        log.warning("setDeptBcfg2() called with bad secret")
        return 1

    return s.setDeptBcfg2(deptName, bcfg2args, url)


def getDeptBcfg2(apiVersion, dept):
    """Return the command string needed to setup Bcfg2 the first time
       based on department.  If the string contains %(password)s
       then a password will be required from the user.  This function
       will never provide passwords although bcfg2 repos can be
       password-less."""
    
    if apiVersion < 2:
        # This function doesn't exist on apiVersions < 2
        raise Fault(1, "Method 'getDeptBcfg2' does not exist at this "
                       "API version")

    s = server.Server(apiVersion, "fqdn", "uuid")
    return s.getDeptBcfg2(dept)


def loadWebKickstart(apiVersion, secret, uuid):
    """(re-)load the Web-Kickstart data into this hosts attributes"""

    if apiVersion < 2:
        # This function doesn't exist on apiVersions < 2
        raise Fault(1, "Method 'loadWebKickstart' does not exist at this "
                       "API version")

    s = server.Server(apiVersion, "fqdn", uuid)
    if not s.verifySecret(secret):
        log.warning("loadWebKickstart() called with bad secret")
        return 1

    return s.loadWebKickstart()

def dumpClients(apiVersion, secret):
    """Return a list of dicts for each host"""

    if apiVersion < 2:
        # This function doesn't exist on apiVersions < 2
        raise Fault(1, "Method 'dumpClients' does not exist at this "
                       "API version")

    s = server.Server(apiVersion, "fqdn", "uuid")
    if not s.verifySecret(secret):
        log.warning("dumpClients() called with bad secret")
        return 1

    return s.dumpClients()

def isRegistered(apiVersion, pubKey=None, sig=None):
    """Returns True if client by this name is registered."""

    if apiVersion == 0:
        s = server.Server(apiVersion, getHostName())
    else:
        s = server.Server(apiVersion, getHostName(), uuid=pubKey)

    ret = s.isRegistered(pubKey, sig)

    if ret == None:
        return False
    elif ret == '':
        # Web-Kickstarted but not completely registered
        return False
    else:
        return True


def isSupported(apiVersion, uuid=None):
    "Returns True if the client meets requirments for support."

    if apiVersion == 0:
        s = server.Server(apiVersion, getHostName())
    else:
        s = server.Server(apiVersion, getHostName(), uuid)

    return s.isSupported()


def checkIn(apiVersion, publicKey, sig):
    """Workstation checking in.  Update status in DB."""
    
    if apiVersion == 0:
        s = server.Server(apiVersion, getHostName())
    else:
        s = server.Server(apiVersion, getHostName(), uuid=publicKey)

    ret = s.checkIn(publicKey, sig)
    return ret


def getActivationKey(apiVersion, publicKey, sig):
    "Return the RHN activation key for this host."

    if apiVersion == 0:
        s = server.Server(apiVersion, getHostName())
    else:
        s = server.Server(apiVersion, getHostName(), uuid=publicKey)

    ret = s.getActivationKey(publicKey, sig)
    if ret is None:
        return ""
    else:
        return ret


def getEncKeyFile(apiVersion, publicKey, sig):
    """Returns an ecrypted string containing what should go in /etc/update.conf
       on the workstation."""
       
    if apiVersion == 0:
        s = server.Server(apiVersion, getHostName())
    else:
        s = server.Server(apiVersion, getHostName(), uuid=publicKey)
    
    ret = s.getEncKeyFile(publicKey, sig)
    return ret

def convertApi_1(apiVersion, uuid, rhnid, publicKey, sig):
    """Converts an API version 0 client to API version 1 and links the
       new UUID with this public key.

       apiVersion - Must be > 0
       uuid - The UUID of the client
       rhnid - The RHN ID of the client.  -1 indicates no ID
       publicKey - The public key of the client
       sig - The signature of the uuid text
    """

    s = server.Server(apiVersion, getHostName(), uuid)
    return s.convertApi_1(publicKey, uuid, rhnid, sig)

def updateRHNSystemID(apiVersion, uuid, sig, rhnid):
    """Update the clients RHN ID."""

    s = server.Server(apiVersion, getHostName(), uuid)
    if not s.verifyClient(uuid, sig):
        return 1

    return s.updateRHNSystemID(rhnid)

