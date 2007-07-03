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

from mod_python import apache

log = logging.getLogger("xmlrpc")

__API__ = ['hello',
           'register',
           'checkIn',
           'bless',
           'message',
           'initHost',

           'getServerKey',
           'getEncKeyFile',
           'getActivationKey',

           'isRegistered',
           'isSupported',
          ]


def hello():
    return "Hello World"


def getHostName():
    """Digs out the hostname from the headers.  This identifies who we
       say we are."""
    
    ip = req.get_remote_host(apache.REMOTE_NOLOOKUP)
    addr = socket.gethostbyaddr(ip)

    return addr[0]


def getServerKey(apiVersion):
    """Return the Server's public key"""
    
    srv = server.Server(apiVersion, getHostName())
    ret = srv.getPublicKey()
    return ret
    

def register(apiVersion, publicKey, dept, version):
    """Workstation requests registration.  Check DB and register host as
       appropiate.  A false return code means that registration failed."""
    
    s = server.Server(apiVersion, getHostName())
    ret = s.register(publicKey, dept, version)
    return ret


def bless(apiVersion, dept, version):
    """Administratively bless a workstation."""

    s = server.Server(apiVersion, getHostName())
    ret = s.bless(dept, version)
    return ret


def message(apiVersion, publicKey, sig, dict):
    """Log a message from a client."""
    s = server.Server(apiVersion, getHostName())
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
       
    s = server.Server(apiVersion, fqdn)
    if not s.verifySecret(secret):
        log.warning("initHost() called with bad secret")
        return 1

    return s.initHost(fqdn, support=1)
    
    
def isRegistered(apiVersion, pubKey=None, sig=None):
    """Returns True if client by this name is registered."""

    s = server.Server(apiVersion, getHostName())
    ret = s.isRegistered(pubKey, sig)

    if ret == None:
        return False
    elif ret == '':
        # Web-Kickstarted but not completely registered
        return False
    else:
        return True


def isSupported(apiVersion):
    "Returns True if the client meets requirments for support."

    s = server.Server(apiVersion, getHostName())
    return s.isSupported()


def checkIn(apiVersion, publicKey, sig):
    """Workstation checking in.  Update status in DB."""
    
    s = server.Server(apiVersion, getHostName())
    ret = s.checkIn(publicKey, sig)
    return ret


def getActivationKey(apiVersion, publicKey, sig):
    "Return the RHN activation key for this host."

    s = server.Server(apiVersion, getHostName())
    ret = s.getActivationKey(publicKey, sig)
    return ret


def getEncKeyFile(apiVersion, publicKey, sig):
    """Returns an ecrypted string containing what should go in /etc/update.conf
       on the workstation."""
       
    s = server.Server(apiVersion, getHostName())
    ret = s.getEncKeyFile(publicKey, sig)
    return ret

