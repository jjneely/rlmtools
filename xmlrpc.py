#!/usr/bin/python
#
# RealmLinux Manager -- client code
# Copyright (C) 2004 - 2007 NC State University
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

import socket
import httplib
import urllib2
import xmlrpclib

from errors import error

apiVersion = 1

def doRPC(method, *params):
    "Return the xmlrpc opject we want."

    # Apply API versioning
    params = list(params)
    params.insert(0, apiVersion)

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


