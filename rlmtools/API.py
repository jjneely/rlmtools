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
import apiServer as server

from mod_python import apache

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


def getServerKey():
    """Return the Server's public key"""
    
    srv = server.Server(getHostName())
    ret = srv.getPublicKey()
    return ret
    

def register(publicKey, dept, version):
    """Workstation requests registration.  Check DB and register host as
       appropiate.  A false return code means that registration failed."""
    
    s = server.Server(getHostName())
    ret = s.register(publicKey, dept, version)
    return ret


def bless(dept, version):
    """Administratively bless a workstation."""

    s = server.Server(getHostName())
    ret = s.bless(dept, version)
    return ret


def message(publicKey, sig, dict):
    """Log a message from a client."""
    s = server.Server(getHostName())
    if not s.verifyClient(publicKey, sig):
        return 1

    ret = s.setServiceStatus(dict['type'],
                             dict['success'], 
                             dict['timestamp'],
                             dict['data'])
    return ret


def initHost(secret, fqdn):
    """API call for Web-Kickstart to initialize a host in the database.
       Protected by the knowing of a secret."""
       
    s = server.Server(fqdn)
    return s.initHost(secret, fqdn)
    
    
def isRegistered(pubKey=None, sig=None):
    """Returns True if client by this name is registered."""

    s = server.Server(getHostName())
    ret = s.isRegistered(pubKey, sig)

    if ret == None:
        return False
    elif ret == '':
        # Web-Kickstarted but not completely registered
        return False
    else:
        return True


def isSupported():
    "Returns True if the client meets requirments for support."

    s = server.Server(getHostName())
    return s.isSupported()


def checkIn(publicKey, sig):
    """Workstation checking in.  Update status in DB."""
    
    s = server.Server(getHostName())
    ret = s.checkIn(publicKey, sig)
    return ret


def getActivationKey(publicKey, sig):
    "Return the RHN activation key for this host."

    s = server.Server(getHostName())
    ret = s.getActivationKey(publicKey, sig)
    return ret


def getEncKeyFile(publicKey, sig):
    """Returns an ecrypted string containing what should go in /etc/update.conf
       on the workstation."""
       
    s = server.Server(getHostName())
    ret = s.getEncKeyFile(publicKey, sig)
    return ret

