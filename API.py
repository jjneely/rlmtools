##     RealmLinux Manager XMLRPC Exposed API
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

# Defines list of functions that are exported via the XML-RPC server.
# You can import modules in this file and then list the module name
# in this list.  That module will then need a __APT list of the functions
# and/or modules that it exposes.

import server

__API = ['hello',
         'register',
         'declineSupport',
         'getServerKey',
         'checkIn',
         'getServerKey',
         'getEncKeyFile']

def hello():
    return "Hello World"


def getHostName():
    """Digs out the hostname from the headers.  This identifies who we
       say we are."""
       
    return req.headers_in['Host']


def getServerKey():
    """Return the Server's public key"""
    
    return server.getFile(server.pubKeyFile)
    

def register(publicKey, dept, version):
    """Workstation requests registration.  Check DB and register host as
       appropiate.  A false return code means that registration failed."""
    
    s = server.Server(getHostName())
    return s.register(publicKey, dept, version)


#def declineSupport():
#    """Workstation has declined support.  Modify DB as appropiate."""
#    
#    s = server.Server(getHostName())
#    s.declineSupport()


def checkIn(publicKey, sig):
    """Workstation checking in.  Update status in DB."""
    
    s = server.Server(getHostName())
    s.checkIn(publicKey, sig)


def getEncKeyFile(publicKey, sig):
    """Returns an ecrypted string containing what should go in /etc/update.conf
       on the workstation."""
       
    s = server.Server(getHostName())
    return s.getEncKeyFile(publicKey, sig)

