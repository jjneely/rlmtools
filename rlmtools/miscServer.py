#!/usr/bin/python
#
# RealmLinux Manager -- Main server object
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

class MiscServer(server.Server):

    def deleteClient(self, host_id):
        """Removes a client from the database."""
        log.warning("Removing client from database: %s" \
                    % self.getHostName(host_id))
        q1 = """delete from realmlinux where host_id = %s"""
        q2 = """delete from lastheard where host_id = %s"""
        q3 = """delete from status where host_id = %s"""
        q4 = """delete from hostkeys where host_id = %s"""

        self.cursor.execute(q1, (host_id,))
        self.cursor.execute(q2, (host_id,))
        self.cursor.execute(q3, (host_id,))
        self.cursor.execute(q4, (host_id,))
        self.conn.commit()

    def cleanDB(self, days=31):
        """Removes status events older than the variable days and removes
           clients that have not checked in in variable days."""

        q1 = """select host_id from lastheard where 
                `timestamp` < %s and `timestamp` > '0000-00-00 00:00:00'"""
        q2 = """delete from status where received < %s"""
        q3 = """select host_id from realmlinux where 
                recvdkey = 0 and installdate < %s"""
        q4 = """select service_id from service where
                  name != 'login' and name != 'logout'"""

        date = datetime.today() - timedelta(days)

        self.cursor.execute(q1, (date,))
        result = resultSet(self.cursor).dump()
        for client in result: self.deleteClient(client['host_id'])

        self.cursor.execute(q3, (date,))
        result = resultSet(self.cursor).dump()
        for client in result: self.deleteClient(client['host_id'])

        self.cursor.execute(q2, (date,))
        self.conn.commit()

