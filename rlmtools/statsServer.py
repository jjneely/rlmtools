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

    def getActiveClients(self, hours=6):
        """Returns the number of clients heard from in the last hours hours."""

        q = """select count(host_id) from lastheard where
               `timestamp` > %s"""
        date = datetime.today() - timedelta(hours=hours)

        self.cursor.execute(q, (date,))
        return self.cursor.fetchone()[0]

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

    def getVersions(self):
        """Returns a table of version to number of clients."""

        q = """select version, count(*) as count from realmlinux
               group by version"""

        self.cursor.execute(q)
        return resultSet(self.cursor).dump()

    def getDSID(self, name):
        """Return the ds_id for this name.  We raise an error if the
           name doesn't exist."""

        q = """select ds_id from dstype where name = %s"""
        self.cursor.execute(q, (name,))
        if self.cursor.rowcount == 0:
            raise StandardError("DS Type %s does not exist." % name)

        return self.cursor.fetchone()[0]

    def getDepartments(self):
        """Return a list of departments."""
        q = "select name from dept order by name asc"
        self.cursor.execute(q)
        r = resultSet(self.cursor)

        return [ row['name'] for row in r ]

    def getRRALocations(self, dstype, host_id=None, label=None, dept=None):
        """Return list of file locations.  host_id and label may
           be None."""
        q1 = """select path, label, host_id from rrdlocation 
                where ds_id = %s """
        q2 = """select rrdlocation.path, rrdlocation.label, 
                   realmlinux.host_id 
                from rrdlocation, dept, realmlinux 
                where realmlinux.host_id = rrdlocation.host_id 
                   and realmlinux.dept_id = dept.dept_id
                   and rrdlocation.ds_id = %s
                   and dept.name = %s"""
        extra = ""

        if dstype == None:
            raise StandardError("getRRALocations() requires a dstype")
        if host_id != None:
            extra = " and rrdlocation.host_id = %s"
        if label != None:
            extra = extra + " and rrdlocation.label = %s"

        if dept != None:
            q = q2 + extra
        else:
            q = q1 + extra
       
        if isinstance(dstype, str):
            ds_id = self.getDSID(dstype)
        else:
            ds_id = dstype

        tup = filter(lambda b: b != None, [ds_id, dept, host_id, label])
        self.cursor.execute(q, tup)
        return resultSet(self.cursor).dump()

    def setRRALocation(self, dstype, host_id, label, path):
        """Set a RRA location in the db.  host_id xor label can be
           None."""
        q1 = """select loc_id from rrdlocation where
                path = %s and ds_id = %s"""
        q2 = """insert into rrdlocation (ds_id, host_id, label, path)
                values (%s, %s, %s, %s)"""

        if isinstance(dstype, str):
            ds_id = self.getDSID(dstype)
        else:
            ds_id = dstype

        self.cursor.execute(q1, (path, ds_id))
        if self.cursor.rowcount > 0:
            log.warning("Attempted insert of duplicate RRD path")
            log.warning("ds_id: %s\nhost_id: %s\nlabel: %s\npath: %s" % \
                        (ds_id, host_id, label, path))
            raise StandardError("Attempted insert of duplicate RRD path.")

        self.cursor.execute(q2, (ds_id, host_id, label, path))
        self.conn.commit()

    def getSyncStates(self):
        """Returns a list of dicts contianing 'host_id' and 'timestamp'
           keys representing the latest sync state for the host."""

        q = """select rrdqueue.host_id, max(rrdqueue.timestamp) as timestamp
               from rrdqueue, dstype
               where dstype.ds_id = rrdqueue.ds_id
                  and dstype.name = 'usagesync'
               group by host_id"""

        self.cursor.execute(q)
        return resultSet(self.cursor).dump()

    def clearUsageEvents(self, host_id, timestamp):
        """Removes all usage and sync events from the rrdqueue table that
           have a timestamp equal to or before the given datetime object
           timestamp."""

        q = """delete from rrdqueue 
               where ds_id = %s and host_id = %s and `timestamp` <= %s"""

        usage_id = self.getDSID('usage')
        sync_id = self.getDSID('usagesync')

        self.cursor.execute(q, (usage_id, host_id, timestamp))
        self.cursor.execute(q, (sync_id, host_id, timestamp))
        self.conn.commit()

    def getUsageEvents(self, host_id, timestamp):
        """Return all the usage events for a host before or equal to
           the given timestamp."""

        q = """select rrdqueue.timestamp, rrdqueue.data as length
               from rrdqueue, dstype
               where dstype.ds_id = rrdqueue.ds_id
               and dstype.name = 'usage'
               and rrdqueue.host_id = %s
               and rrdqueue.timestamp <= %s"""

        self.cursor.execute(q, (host_id, timestamp))
        return resultSet(self.cursor).dump()

