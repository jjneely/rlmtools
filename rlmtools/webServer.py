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
import base64
import pickle
import server

from datetime import datetime, timedelta
from resultSet import resultSet
from configDragon import config

log = logging.getLogger("xmlrpc")

class WebServer(server.Server):

    def getStatusDetail(self, status_id):
        """Return historical information regarding this clients status."""
        
        q = """select serv.name, s.timestamp, s.success, s.data,
                      s.received, r.hostname, r.host_id
               from status as s, service as serv, realmlinux as r 
               where r.host_id = s.host_id and
                     serv.service_id = s.service_id and
                     s.st_id = %s"""
    
        self.cursor.execute(q, (status_id,))
        result = resultSet(self.cursor).dump()
    
        return result[0]

    def getDepartments(self):
        q1 = """select dept.name, dept.dept_id,
                    count(support = 1 or null) as supported, 
                    count(support = 0 or null) as unsupported 
                from dept left join realmlinux on 
                    dept.dept_id = realmlinux.dept_id
                    and realmlinux.recvdkey = 1
                group by dept.name;"""

        self.cursor.execute(q1)
        return resultSet(self.cursor).dump()

    def getNoUpdates(self):
        # Need to run q3 and substract q2
        q2 = """select distinct status.host_id, realmlinux.hostname
                from status, service, realmlinux
                where service.service_id = status.service_id
                   and realmlinux.host_id = status.host_id
                   and service.name = 'updates'
                   and status.success = 1 
                   and TO_DAYS(status.timestamp) >= TO_DAYS(NOW()) - 7"""
        q3 = """select realmlinux.host_id, realmlinux.hostname, 
                   dept.name as deptname
                from realmlinux, dept
                where dept.dept_id = realmlinux.dept_id
                   and realmlinux.recvdkey = 1"""

        self.cursor.execute(q3)
        result = resultSet(self.cursor).dump()
        hash = {}

        for row in result:
            hash[row['hostname']] = row

        self.cursor.execute(q2)
        result2 = resultSet(self.cursor).dump()

        for row in result2:
            try:
                del hash[row['hostname']]
            except KeyError:
                pass

        # This method of gathering the data prevents the database
        # from sorting for us
        keys = hash.keys()
        keys.sort(lambda x,y: cmp(x.lower(), y.lower()))

        return map(hash.get, keys)

    def getProblemList(self):
        q  = """select status.host_id, realmlinux.hostname, 
                   dept.name as deptname
                from realmlinux, dept, status, 
                   ( select host_id, service_id as sid, 
                        max(`timestamp`) as maxdate 
                     from status group by host_id, service_id ) as foo
                where status.host_id = foo.host_id 
                   and status.service_id = foo.sid
                   and status.timestamp = foo.maxdate 
                   and status.success=0
                   and status.host_id = realmlinux.host_id
                   and realmlinux.dept_id = dept.dept_id
                order by deptname asc"""

        self.cursor.execute(q)
        return resultSet(self.cursor).dump()

    def getClientList(self, dept_id):
        q1 = """select r.hostname, r.host_id, r.support, r.installdate,
                l.timestamp as lastcheck
                from realmlinux as r, lastheard as l
                where r.dept_id = %s and r.recvdkey = 1 and
                r.host_id = l.host_id
                order by r.hostname"""

        q2 = """select status.host_id, service.name, 
                   status.success, status.timestamp
                from service, status,
                ( select status.host_id, 
                         status.service_id as sid, 
                         max(status.timestamp) as maxdate 
                  from status, realmlinux
                  where realmlinux.host_id = status.host_id
                     and realmlinux.dept_id = %s
                  group by status.host_id, status.service_id
                ) as current
                where current.sid = status.service_id and
                service.service_id = status.service_id and
                status.timestamp = current.maxdate and
                status.host_id = current.host_id"""

        self.cursor.execute(q1, (dept_id,))
        result = resultSet(self.cursor).dump()

        # I'm going to reference the data in result via a hash
        hash = {}

        for row in result:
            hash[row['host_id']] = row

        self.cursor.execute(q2, (dept_id,))
        status = resultSet(self.cursor).dump()

        for row in status:
            service = row['name']
            stime = "%s_time" % service
            hash[row['host_id']][service] = row['success']
            hash[row['host_id']][stime] = row['timestamp']

        return result

    def getClientDetail(self, host_id, history_days=30):
        # returns a dict of: hostname, installdate, recvdkey, support, 
        #    dept, version, lastcheck, status
        # status is a list of dicts: service, timestamp, success, data
        q1 = """select r.hostname, r.installdate, r.recvdkey, r.support,
                       d.name as dept, r.dept_id, r.version
                from realmlinux as r, dept as d
                where d.dept_id = r.dept_id and r.host_id = %s"""
        q2 = """select `timestamp` as lastcheck from lastheard where
                host_id = %s"""
        q3 = """select service.name as service, status.timestamp, 
                       status.success, status.data, status.st_id,
                       status.received
                from service, status
                where service.service_id = status.service_id and
                      status.host_id = %s and 
                      TO_DAYS(status.timestamp) > TO_DAYS(NOW()) - %s
                order by status.received desc, status.timestamp desc"""

        self.cursor.execute(q1, (host_id,))
        result1 = resultSet(self.cursor).dump()[0]  # This is one row

        self.cursor.execute(q2, (host_id,))
        if self.cursor.rowcount > 0:
            result2 = self.cursor.fetchone()[0]
        else:
            result2 = None

        self.cursor.execute(q3, (host_id, history_days))
        result3 = resultSet(self.cursor).dump()

        result1['lastcheck'] = result2
        result1['status'] = result3
        return result1

    def getTotalClients(self):
        """Returns a tuple with the number of supported, non-supported, 
           and clients that have not registered."""

        q1 = "select count(*) from realmlinux where support = 1 and recvdkey=1"
        q2 = "select count(*) from realmlinux where support = 0 and recvdkey=1"
        q3 = "select count(*) from realmlinux where recvdkey = 0"
        q4 = "select count(*) from dept"
        # q5 select the number of hosts with problems
        q5 = """select count(*) from status, 
                   ( select host_id, service_id as sid, 
                        max(`timestamp`) as maxdate 
                     from status group by host_id, service_id ) as foo
                where status.host_id = foo.host_id 
                   and status.service_id = foo.sid
                   and status.timestamp = foo.maxdate 
                   and status.success=0"""
        # The number of hosts not updating
        q6 = """select count(*) from realmlinux where recvdkey = 1"""
        q7 = """select count(distinct status.host_id) from status, service 
                where service.service_id = status.service_id 
                    and service.name = 'updates' 
                    and status.success = 1 
                    and TO_DAYS(status.timestamp) >= TO_DAYS(NOW()) - 7"""

        ret = {}
        self.cursor.execute(q1)
        ret['supported'] = self.cursor.fetchone()[0]
        
        self.cursor.execute(q2)
        ret['unsupported'] = self.cursor.fetchone()[0]

        self.cursor.execute(q3)
        ret['unregistered'] = self.cursor.fetchone()[0]

        self.cursor.execute(q4)
        ret['departments'] = self.cursor.fetchone()[0]

        self.cursor.execute(q5)
        ret['problems'] = self.cursor.fetchone()[0]

        self.cursor.execute(q6)
        total = self.cursor.fetchone()[0]
        self.cursor.execute(q7)
        goodUpdates = self.cursor.fetchone()[0]
        ret['noupdates'] = total - goodUpdates

        return ret

    def getNotRegistered(self):
        """Returns information about clients that have not registered."""

        q = """select host_id, hostname, support from realmlinux where
                  recvdkey = 0 order by hostname asc"""

        self.cursor.execute(q)
        return resultSet(self.cursor).dump()

    def getActiveClients(self, hours=6):
        """Returns the number of clients heard from in the last hours hours."""

        q = """select count(host_id) from lastheard where
               `timestamp` > %s"""
        date = datetime.today() - timedelta(hours=hours)

        self.cursor.execute(q, (date,))
        return self.cursor.fetchone()[0]

