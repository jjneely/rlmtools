#!/usr/bin/python
#
# usagelog.py - Report usage statistics to central server
# Copyright (C) 2007 NC State University
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

import os
import sys
import pickle
import optparse
import clientconf

from client import Message
from constants import defaultConfFiles

ServiceType = "usagelog"

def isSafe():
    """Return true if there are no other realm users logged in to the
       system."""

    # The database needs a sync check to know when its safe to populate
    # the RRDs as they must be populated sequentially.

    pipe = os.popen("/usr/bin/who")
    blob = pipe.read()
    pipe.close()

    if blob.strip() == "":
        return True
    else:
        return False

def main():
    """Create a message from pam_ncsu_access's session usage report
       and send that to the central glue server."""

    parser = optparse.OptionParser()
    parser.add_option("-C", "--configfile", action="store",
                      default=defaultConfFiles,
                      dest="configfile",
                      help="Configuration file")

    (options, args) = parser.parse_args()

    URL = clientconf.initConfig(options.configfile)

    if len(args) != 2:
        print "Usage: %s <userid> <session time in seconds>" % sys.argv[0]
        sys.exit(1)

    if len(args[0]) <= 8:
        userid = args[0]
    else:
        print "Invalid format for userid: %s" % args[0]
        sys.exit(1)
    try:
        session = int(args[1])
    except ValueError:
        print "Invalud format for seconds: %s" % args[1]
        sys.exit(1)

    data = {'userid': userid, 'time': session, 'sync':isSafe()}
    blob = pickle.dumps(data)

    m = Message()
    m.setType(ServiceType)
    m.setSuccess(True)
    m.setMessage(blob)
    try:
        m.save()
    except (OSError, IOError), e:
        print "There was an error queuing the message."
        print str(e)
        sys.exit(2)

if __name__ == "__main__":
    main()

