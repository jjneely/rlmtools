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

import sys
import pickle

from client import Message

ServiceType = "usagelog"

def main():
    """Create a message from pam_ncsu_access's session usage report
       and send that to the central glue server."""

    if len(sys.argv) != 3:
        print "Usage: %s <userid> <session time in seconds>" % sys.argv[0]
        sys.exit(1)

    if len(sys.argv[1]) <= 8:
        userid = sys.argv[1]
    else:
        print "Invalid format for userid: %s" % sys.argv[1]
        sys.exit(1)
    try:
        session = int(sys.argv[2])
    except ValueError:
        print "Invalud format for seconds: %s" % sys.argv[2]
        sys.exit(1)

    data = {'userid': userid, 'time': session}
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

