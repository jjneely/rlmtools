#!/usr/bin/python
#
# RealmLinux Manager -- Main server object
# Copyright (C) 2003 - 2011 NC State University
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
import re
import sys
import logging
import server

from datetime import datetime, timedelta
from resultSet import resultSet
from rlattributes import RLAttributes

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
        q5 = """update history set host_id = NULL where host_id = %s"""

        self.cursor.execute(q1, (host_id,))
        self.cursor.execute(q2, (host_id,))
        self.cursor.execute(q3, (host_id,))
        self.cursor.execute(q4, (host_id,))
        self.cursor.execute(q5, (host_id,))
        self.conn.commit()

    def cleanDB(self, days=31):
        """Removes status events older than the variable days and removes
           clients that have not checked in in variable days."""

        q1 = """select host_id from lastheard where 
                `timestamp` < %s and `timestamp` > '0000-00-00 00:00:00'"""
        q2 = """delete from status where received < %s"""
        q3 = """select host_id from realmlinux where 
                recvdkey = 0 and installdate < %s"""

        self.rla = RLAttributes()
        date = datetime.today() - timedelta(days)

        self.cursor.execute(q1, (date,))
        result = resultSet(self.cursor).dump()
        for client in result: 
            self.rla.removeAllHostAttrs(client['host_id'])
            self.deleteClient(client['host_id'])

        self.cursor.execute(q3, (date,))
        result = resultSet(self.cursor).dump()
        for client in result: self.deleteClient(client['host_id'])

        self.cursor.execute(q2, (date,))
        self.conn.commit()

    def getSysAdmins(self, acl_id):
        q = """select userid, sysadmin_id from sysadmins 
               where acl_id = %s order by userid asc"""

        self.cursor.execute(q, (acl_id,))
        result = resultSet(self.cursor)
        ret = []
        for row in result:
            ret.append((row['userid'], row['sysadmin_id']))
        return ret

    def getPTS(self, pts, cell):
        sentry = re.compile(r'^[a-z][a-z0-9_\-]{1,7}$')  # matches NCSU userids
        cmd = "/usr/bin/pts mem %s -c %s -noauth" % (pts, cell)
        ids = []
        #print "Executing: %s" % cmd
        fd = os.popen(cmd, 'r')
        blob = fd.readlines()
        ret = fd.close()
        #print blob

        if ret is not None:
            # Some sort of OS Error
            log.error("'%s' failed with return code %s" % (cmd, ret))
            return None

        if len(blob) == 0:
            # No data?  Something Bad happened
            return None
        if len(blob) == 1:
            # PTS group is empty
            return []
        for line in blob[1:]:   # First line is header, toss it
            user = line.strip()
            if user == "": 
                continue
            if sentry.match(user):
                ids.append(user)
            else:
                sys.stderr.write("Got bad data from PTS command.  User = %s\n"\
                                 % user)
                log.error("Got bad data from PTS command.  User = %s" % user)
                return None
        
        ids.sort()
        return ids

    def watchPTS(self):
        """Sync database with AFS PTS groups that we watch."""

        q1 = "select acl_id, pts, cell from acls"
        q2 = "delete from sysadmins where sysadmin_id = %s"
        q3 = "insert into sysadmins (acl_id, userid) values(%s, %s)"
        self.cursor.execute(q1)
        result = resultSet(self.cursor).dump()

        # ACQUIRE LOCK
        log.info("Running PTS watcher, locking sysadmins table")
        self.cursor.execute("lock tables sysadmins write")
        for row in result:
            #print "Working on ACL: %s" % str(row)
            current = self.getSysAdmins(row['acl_id'])
            #print "Current list: %s" % str(current)
            pts = self.getPTS(row['pts'], row['cell'])
            #print "New list    : %s" % str(pts)
            if pts is None:
                # Error...bad PTS data...check logs
                continue

            i = 0
            while i < len(pts):
                if len(current) <= i or current[i][0] > pts[i]:
                    self.cursor.execute(q3, (row['acl_id'], pts[i]))
                    # Keep our index numbers intact
                    current.insert(i, (pts[i], None)) 
                    i = i + 1
                elif current[i][0] < pts[i]:
                    self.cursor.execute(q2, (current[i][1],))
                    del current[i]            # Keep our index numbers intact
                elif current[i][0] == pts[i]:
                    i = i + 1
            while len(current) > len(pts):
                self.cursor.execute(q2, (current[i][1],))
                del current[i]                # Keep our index numbers intact

        self.cursor.execute("unlock tables")
        log.info("PTS watcher complete")
        self.conn.commit()

