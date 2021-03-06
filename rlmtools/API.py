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

from rlmtools import app

from flask import request, g
from flaskext.xmlrpc import Fault, XMLRPCHandler

handler = XMLRPCHandler("__API__", introspection=False)
handler.connect(app, "/api/xmlrpc")

log = logging.getLogger("xmlrpc")

__API__ = ['hello',
           'register',
           'checkIn',
           'bless',
           'message',
           'updateRHNSystemID',
           'getAddress',
           'signCert',

           'initHost',
           'setDeptBcfg2',
           'getBcfg2Bootstrap',
           'loadWebKickstart',
           'dumpClients',

           'getServerKey',
           'getEncKeyFile',
           'getActivationKey',

           'isRegistered',
           'isSupported',
          ]

# Helper decorator -- Log exceptions -- all of them
def trap(func):
    def exception_trap(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception, e:
            log.exception("An exception occured in the XML-RPC handler.")
            
            # Let the normal python/Flask error handlers do their job
            raise

    # The handler.register decorator is above us, pass the __name__ through
    exception_trap.__name__ = func.__name__
    return exception_trap

# Helper function, not exposed to the XML-RPC interface
def getHostName():
    """Digs out the hostname from the headers.  This identifies who we
       say we are."""
    
    return g.fqdn

@handler.register
@trap
def hello(apiVersion):
    return "Hello World"

@handler.register
@trap
def getAddress(apiVersion):
    """Return the ip/fqdn address pair of the calling client.  This is
       the address as viewed from the RLMTools server."""

    # We use this a lot so its done once for each call via webcommon.py
    return g.ip, g.fqdn

@handler.register
@trap
def getServerKey(apiVersion, uuid=None):
    """Return the Server's public key"""
    
    srv = server.Server(apiVersion, getHostName(), uuid)
    ret = srv.getPublicKey()
    return ret
    
@handler.register
@trap
def register(apiVersion, publicKey, dept, version, uuid=None, rhnid=None,
             sid=None):
    """Workstation requests registration.  Check DB and register host as
       appropiate.  A false return code means that registration failed."""
    
    s = server.Server(apiVersion, getHostName(), uuid)
    ret = s.register(publicKey, dept, version, rhnid, sid)
    return ret

@handler.register
@trap
def bless(apiVersion, dept, version, uuid=None, rhnid=None):
    """Administratively bless a workstation."""

    s = server.Server(apiVersion, getHostName(), uuid)
    ret = s.bless(dept, version, rhnid)
    return ret

@handler.register
@trap
def signCert(apiVersion, uuid, sig, fingerprint):
    """Request Puppet Certificate for this host be signed."""

    if apiVersion < 2:
        # This function doesn't exist on apiVersions < 2
        raise Fault(1, "Method 'signCert' does not exist at this "
                       "API version")

    s = server.Server(apiVersion, getHostName(), uuid)
    if not s.verifyClient(uuid, sig):
        # Auth failed
        return 1

    return s.signCert(fingerprint)

@handler.register
@trap
def resetHostname(apiVersion, uuid, sig):
    s = server.Server(apiVersion, getHostName(), uuid)

    if apiVersion < 2:
        # This function doesn't exist on apiVersions < 2
        return 1
    if not s.verifyClient(uuid, sig):
        return 1

    return s.resetHostname()

@handler.register
@trap
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

@handler.register
@trap
def initHost(apiVersion, secret, fqdn, dept="ncsu"):
    """API call for Web-Kickstart to initialize a host in the database.
       Protected by the knowing of a secret."""
    
    if apiVersion > 0:
        # Supply a fake UUID, its never used with initHost()
        s = server.Server(apiVersion, fqdn, uuid="foobarbaz")
    else:
        s = server.Server(apiVersion, fqdn)

    if not s.verifySecret(secret):
        log.warning("initHost() called with bad secret")
        if apiVersion < 2: return 1
        else: return (1, "")

    hid, sid = s.initHost(fqdn, support=1, dept=dept)
    if apiVersion < 2:
        return 0
    else:
        return (0, sid)

@handler.register
@trap
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

@handler.register
@trap
def getBcfg2Bootstrap(apiVersion, uuid, sig):
    """Registered machines can request their Bcfg2 bootstrap information"""
        
    if apiVersion < 2:
        # This function doesn't exist on apiVersions < 2
        raise Fault(1, "Method 'getBcfg2Bootstrap' does not exist at this "
                       "API version")
        
    s = server.Server(apiVersion, getHostName(), uuid)
    if not s.verifyClient(uuid, sig):
        return (1, {})

    return s.getBcfg2Bootstrap()

@handler.register
@trap
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

@handler.register
@trap
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

@handler.register
@trap
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

@handler.register
@trap
def isSupported(apiVersion, uuid=None):
    "Returns True if the client meets requirments for support."

    if apiVersion == 0:
        s = server.Server(apiVersion, getHostName())
    else:
        s = server.Server(apiVersion, getHostName(), uuid)

    return s.isSupported()

@handler.register
@trap
def checkIn(apiVersion, publicKey, sig, dept=None):
    """Workstation checking in.  Update status in DB."""

    if apiVersion < 2 and dept is not None:
        raise Fault(1, "checkIn() has only 3 arguments at apiVersion %s" \
                    % apiVersion)
    if apiVersion >= 2 and dept is None:
        raise Fault(1, "checkIn() has only 4 arguments at apiVersion %s" \
                    % apiVersion)
    
    if apiVersion == 0:
        s = server.Server(apiVersion, getHostName())
    else:
        s = server.Server(apiVersion, getHostName(), uuid=publicKey)

    if apiVersion < 2:
        ret = s.checkIn(publicKey, sig)
    else:
        ret = s.checkIn(publicKey, sig, dept)

    return ret

@handler.register
@trap
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

@handler.register
@trap
def getEncKeyFile(apiVersion, publicKey, sig):
    """Returns an ecrypted string containing what should go in /etc/update.conf
       on the workstation."""
       
    if apiVersion == 0:
        s = server.Server(apiVersion, getHostName())
    else:
        s = server.Server(apiVersion, getHostName(), uuid=publicKey)
    
    ret = s.getEncKeyFile(publicKey, sig)
    return ret

@handler.register
@trap
def updateRHNSystemID(apiVersion, uuid, sig, rhnid):
    """Update the clients RHN ID."""

    s = server.Server(apiVersion, getHostName(), uuid)
    if not s.verifyClient(uuid, sig):
        return 1

    return s.updateRHNSystemID(rhnid)

