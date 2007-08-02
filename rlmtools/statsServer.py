#!/usr/bin/python
#
# RealmLinux Manager -- Statistics and History
# Copyright (C) 2003, 2005, 2006, 2007 NC State University
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
import logging
import server

from datetime import datetime, timedelta
from resultSet import resultSet

log = logging.getLogger("xmlrpc")

class StatsServer(server.Server):

    def count(self, q):
        """Run the given query assuming that it returns one integer as
           'select count(*)...' and return the integer.  Returns None on
           failure."""

        self.cursor.execute(q)
        if self.cursor.rowcount > 0:
            return self.cursor.fetchone()[0]
        else:
            return None

    def getTotal(self):
        "Return total number of clients."

        return self.count("select count(*) from realmlinux")

    def getSupported(self):
        "Return number of supported clients."
        q = "select count(*) from realmlinux where support = 1 and recvdkey = 1"
        return self.count(q)

    def getUnsupported(self):
        "Return number of unsupported clients."
        q = "select count(*) from realmlinux where support = 0 and recvdkey = 1"
        return self.count(q)

    def getWebKickstarting(self):
        "Number of clients currently installing."
        q = "select count(*) from realmlinux where recvdkey = 0"
        return self.count(q)

    def getProblems(self):
        "Number of clients reporting problems."
        q  = """select count(*) from status, 
                   ( select host_id, service_id as sid, 
                        max(`timestamp`) as maxdate 
                     from status group by host_id, service_id ) as foo
                where status.host_id = foo.host_id 
                   and status.service_id = foo.sid
                   and status.timestamp = foo.maxdate 
                   and status.success=0"""
        return self.count(q)

    def getNotUpdating(self):
        "Number of clients not updating."
        q1 = """select count(*) from realmlinux where recvdkey = 1"""
        q2 = """select count(distinct status.host_id) from status, service 
                where service.service_id = status.service_id 
                    and service.name = 'updates' 
                    and status.success = 1 
                    and TO_DAYS(status.timestamp) >= TO_DAYS(NOW()) - 7"""
        return self.count(q1) - self.count(q2)

