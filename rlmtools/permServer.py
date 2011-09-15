#!/usr/bin/python
#
# RealmLinux Manager -- Main server object
# Copyright (C) 2011 NC State University
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
import logging
import server

import afs.pts
from afs._util import AFSException

from resultSet import resultSet

log = logging.getLogger("xmlrpc")

class PermServer(server.Server):

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
            #pts = self.getPTS(row['pts'], row['cell'])

            try:
                ptsdb = afs.pts.PTS(cell=row['cell'])
                group = ptsdb.getEntry(row['pts'])
                pts = [ e.name for e in group.members ]
            except AFSException, e:
                print "AFS API Blew up: %s" % str(e)
            pts.sort()
            #print "New list    : %s" % str(pts)

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

    def insertWebKSDir(self, path, dept_id):
        # Check if a row representing thiw webks dir exists.
        # If not we insert it with dept_id as a guess of which department
        # it maps too.
        # Otherwise we ignore the request and assume the DB has the
        # correct information.

        q1 = """select wkd_id from webkickstartdirs where path = %s"""
        q2 = """insert into webkickstartdirs (path, dept_id)
                    values (%s, %s)"""

        self.cursor.execute(q1, (path, ))
        if self.cursor.rowcount > 1:
            log.warning("Database inconsistancy in webkickstartdirs table")
            log.warning("   Duplicate paths: %s" % path)
            return
        if self.cursor.rowcount == 1: return

        self.cursor.execute(q2, (path, dept_id))
        self.conn.commit()

    def cleanWebKSDirs(self, paths):
        """paths is a list of known current Web-Kickstart directories in
           the absolute form.  Any directory in the database that's not in
           this list will be removed to prune old directories."""

        q1 = """delete from webkickstartdirs where wkd_id = %s"""
        table = self.getAllWKSDir()
        if len(paths) < 1: return
        if len(table) < 1: return

        # Make a dict for quick compares
        d = {}
        commit = False
        for i in table: d[i['path']] = i['wkd_id']
        for i in d.keys():
            if i not in paths:
                self.cursor.execute(q1, (d[i],))
                if not commit: commit = True

        if commit:
            self.conn.commit()

    def getAllWKSDir(self):
        q = """select * from webkickstartdirs"""
        self.cursor.execute(q)
        return resultSet(self.cursor).dump()

    def getWKSDir(self, wkd_id):
        q = """select * from webkickstartdirs where wkd_id = %s"""
        self.cursor.execute(q, (wkd_id,))
        ret = resultSet(self.cursor)
        if ret.rowcount() == 0:
            return None
        
        return ret.dump()[0]

    def setWKSDept(self, wkd_id, dept_id):
        """Set the associated department on a Web-Kickstart directory entry"""

        q = """update webkickstartdirs set dept_id = %s where wkd_id = %s"""
        self.cursor.execute(q, (dept_id, wkd_id))
        self.conn.commit()

    def getDeptACLs(self, dept_id):
        """Return a list of dicts containing the ACLs that affect the given
           department."""

        q = """select acls.name, acls.pts, acls.acl_id, aclgroups.perms 
               from acls, aclgroups where
               acls.acl_id = aclgroups.acl_id and
               aclgroups.dept_id = %s"""

        d = dept_id
        ret = {}

        # This looping construct deals with inherited permissions
        while d is not None:
            self.cursor.execute(q, (d,))
            for row in resultSet(self.cursor):
                if row['acl_id'] in ret:
                    ret[row['acl_id']]['perms'] = \
                            ret[row['acl_id']]['perms'] | row['perms']
                else:
                    ret[row['acl_id']] = row.copy()
            d = self.getDeptParentID(d)

        keys = ret.keys()
        keys.sort()
        return [ ret[i] for i in keys ]

    def createACL(self, name, pts, cell):
        "Create a PTS based ACL"
        q = "insert into acls (name, pts, cell) values (%s, %s, %s)"
        self.cursor.execute(q, (name, pts, cell))
        self.conn.commit()

    def removeACL(self, acl_id):
        "Wipe her out, Scotty!"
        q1 = "delete from acls where acl_id = %s"
        q2 = "delete from sysadmins where acl_id = %s"
        q3 = "delete from aclgroups where acl_id = %s"

        self.cursor.execute(q1, (acl_id,))
        self.cursor.execute(q2, (acl_id,))
        self.cursor.execute(q3, (acl_id,))
        self.conn.commit()

    def getACL(self, acl_id):
        "Return basic information about an ACL"
        q = "select name, pts, cell from acls where acl_id = %s"
        self.cursor.execute(q, (acl_id,))
        return resultSet(self.cursor).dump()[0]

    def getACLbyName(self, pts, cell):
        "Return the acl_id or None that matches the given ACL"
        q = "select acl_id from acls where pts = %s and cell = %s"
        self.cursor.execute(q, (pts, cell))
        if self.cursor.rowcount > 0:
            return self.cursor.fetchone()[0]
        else:
            return None

    def isACL(self, acl):
        "Return True if acl exists"
        q = "select acl_id from acls where pts = %s"
        self.cursor.execute(q, (acl,))
        return self.cursor.rowcount > 0

    def getPTSGroups(self):
        """Returns a list of dicts"""

        q = "select acl_id, name, pts, cell from acls order by pts"
        self.cursor.execute(q)
        return resultSet(self.cursor).dump()

    def getSysAdmins(self, acl_id):
        q = """select distinct userid, sysadmin_id from sysadmins 
               where acl_id = %s order by userid"""

        self.cursor.execute(q, (acl_id,))
        result = resultSet(self.cursor)
        return [ row['userid'] for row in result ]

    def getPermsForACL(self, acl_id):
        q = """select d.dept_id, d.name, a.perms, a.aclg_id 
               from dept as d, aclgroups as a
               where d.dept_id = a.dept_id and
               a.acl_id = %s"""

        self.cursor.execute(q, (acl_id,))
        return resultSet(self.cursor).dump()

    def setPerm(self, acl_id, dept_id, bitfield):
        "Add permissions to an ACL group"
        q = "insert into aclgroups (acl_id, dept_id, perms) values (%s, %s, %s)"
        self.cursor.execute(q, (acl_id, dept_id, bitfield))
        self.conn.commit()

    def removePerm(self, aclg_id):
        q = "delete from aclgroups where aclg_id = %s"
        self.cursor.execute(q, (aclg_id,))
        self.conn.commit()

    def setRHNGroupDept(self, rg_id, dept_id):
        "Set the department <=> RHN Group mapping."
        q = """update rhngroups set dept_id = %s where rg_id = %s"""
        self.cursor.execute(q, (dept_id, rg_id))
        self.conn.commit()

    def getRHNGroups(self):
        "Return a list of dicts of all RHN groups known to LD."""

        q = """select rhnname, rhng_id, dept_id, rg_id from rhngroups"""
        self.cursor.execute(q)
        return resultSet(self.cursor).dump()

    def getRHNGroup(self, rg_id):
        "Return a dict of an RHN group from the LD DB"
        q = """select * from rhngroups where rg_id = %s"""
        self.cursor.execute(q, (rg_id,))
        if self.cursor.rowcount == 0:
            return None
        return resultSet(self.cursor).dump()[0]

    def insertRHNGroup(self, rhnname, rhng_id, dept_id):
        "Insert a new RHN group into the LD DB"
        q = """insert into rhngroups (rhnname, rhng_id, dept_id) values
               (%s, %s, %s)"""

        self.cursor.execute(q, (rhnname, rhng_id, dept_id))
        self.conn.commit()

    def rmRHNGroup(self, rg_id):
        q = """delete from rhngroups where rg_id = %s"""
        self.cursor.execute(q, (rg_id,))
        self.conn.commit()

    def getRHNProtectedUsers(self):
        """Return a list of protected RHN users that are not to be
           deleted, removed, or altered.  This list also includes
           RHN OrgAdmins who we treat a little differently in
           determining ACLs for RHN Groups."""

        q = """select userid from rhnprotectedusers order by userid"""
        self.cursor.execute(q)
        result = resultSet(self.cursor)
        return [ r['userid'] for r in result ]

    def addRHNProtectedUser(self, userid):
        q = """insert into rhnprotectedusers (userid) values (%s)"""
        self.cursor.execute(q, (userid,))
        self.conn.commit()

    def getBcfg2Dir(self, br_id):
        q = """select * from bcfg2repos where br_id = %s"""
        self.cursor.execute(q, (br_id,))
        ret = resultSet(self.cursor)
        if ret.rowcount() == 0:
            return None
        
        return ret.dump()[0]

    def getAllBcfg2Dir(self):
        q = """select * from bcfg2repos"""
        self.cursor.execute(q)
        return resultSet(self.cursor).dump()

    def setBcfg2Dept(self, br_id, dept_id):
        q = """update bcfg2repos set dept_id = %s where br_id = %s"""
        self.cursor.execute(q, (dept_id, br_id))
        self.conn.commit()

    def insertBcfg2Dir(self, path, dept_id):
        q1 = """select br_id from bcfg2repos where path = %s"""
        q2 = """insert into bcfg2repos (path, dept_id)
                    values (%s, %s)"""

        self.cursor.execute(q1, (path, ))
        if self.cursor.rowcount > 1:
            log.warning("Database inconsistancy in bcfg2repos table")
            log.warning("   Duplicate paths: %s" % path)
            return
        if self.cursor.rowcount == 1: return

        self.cursor.execute(q2, (path, dept_id))
        self.conn.commit()

    def cleanBcfg2Dirs(self, paths):
        q1 = """delete from bcfg2repos where br_id = %s"""
        table = self.getAllBcfg2Dir()
        if len(paths) < 1: return
        if len(table) < 1: return

        # Make a dict for quick compares
        d = {}
        commit = False
        for i in table: d[i['path']] = i['br_id']
        for i in d.keys():
            if i not in paths:
                self.cursor.execute(q1, (d[i],))
                if not commit: commit = True

        if commit:
            self.conn.commit()


