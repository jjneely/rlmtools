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

import re
import os
import sys
import logging
import server

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
            current = self.getSysAdminsAndIDs(row['acl_id'])
            #print "Current list: %s" % str(current)
            pts = self.getPTS(row['pts'], row['cell'])
            #print "New list    : %s" % str(pts)
            if pts is None:
                log.warning("getPTS(%s, %s) returned None" \
                        % (row['pts'], row['cell']))
                sys.stderr.write("getPTS(%s, %s) returned None\n" \
                        % (row['pts'], row['cell']))
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
                ids.append(user.strip().lower())
            else:
                sys.stderr.write("Got bad data from PTS command.  User = %s\n"\
                                 % user)
                log.error("Got bad data from PTS command.  User = %s" % user)
                return None
        
        ids.sort()
        return ids

    def getSysAdminsAndIDs(self, acl_id):
        q = """select userid, sysadmin_id from sysadmins 
               where acl_id = %s order by userid asc"""

        self.cursor.execute(q, (acl_id,))
        result = resultSet(self.cursor)
        ret = []
        for row in result:
            ret.append((row['userid'], row['sysadmin_id']))
        return ret

    def removeDept(self, dept_id):
        "Remove/delete the given department."
        q = "delete from dept where dept_id = %s"
        self.cursor.execute(q, (dept_id,))
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

    def getWKSID(self, path):
        """Return the wkd_id of a web-kickstart directory that has the 
           path equal to the given path."""
        q = "select wkd_id from webkickstartdirs where path = %s"
        self.cursor.execute(q, (path,))
        ret = resultSet(self.cursor)
        if ret.rowcount() == 0:
            return None
        return ret['wkd_id']

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

    def getWKSDept(self, dept_id):
        """Return all WKDs associated with the given department."""
        
        q = """select * from webkickstartdirs where dept_id = %s"""
        self.cursor.execute(q, (dept_id))
        ret = resultSet(self.cursor)
        if ret.rowcount() == 0:
            return None
        else:
            return ret.dump()

    def setWKSDept(self, wkd_id, dept_id):
        """Set the associated department on a Web-Kickstart directory entry"""

        q = """update webkickstartdirs set dept_id = %s where wkd_id = %s"""
        self.cursor.execute(q, (dept_id, wkd_id))
        self.conn.commit()

    def removeDeptACLs(self, dept_id):
        """Remove all ACLs that are directly associated with the given
           dept_id from the department.  This does not remove the ACLs
           just their association with the department."""

        q = """delete from aclgroups where dept_id = %s"""
        self.cursor.execute(q, (dept_id,))
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

    def getRHNGroupsDept(self, dept_id):
        """Return all RHN groups associated with the given department."""
        q = """ select * from rhngroups where dept_id = %s"""
        self.cursor.execute(q, (dept_id,))
        ret = resultSet(self.cursor)
        if ret.rowcount() == 0:
            return None
        else:
            return ret.dump()

    def setRHNGroupDept(self, rg_id, dept_id):
        "Set the department <=> RHN Group mapping."
        q = """update rhngroups set dept_id = %s where rg_id = %s"""
        self.cursor.execute(q, (dept_id, rg_id))
        self.conn.commit()

    def getRHNGroups(self):
        "Return a list of dicts of all RHN groups known to LD."""

        q = """select * from rhngroups"""
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

    def updateLicenseCount(self, rhng_id, count):
        """Update the license usage count for the RHN group defined by
           rhng_id."""

        q = "update rhngroups set licenses = %s where rhng_id = %s"
        self.cursor.execute(q, (count, rhng_id))
        self.conn.commit()

    def getPuppetDept(self, dept_id):
        """Return all Puppet repos associated with the given department."""
        q = """select * from puppetrepos where dept_id = %s"""
        self.cursor.execute(q, (dept_id,))
        ret = resultSet(self.cursor)
        if ret.rowcount() == 0:
            return None
        else:
            return ret.dump()

    def getPuppetID(self, path):
        """Return the p_id of a puppet repository that has the path equal
           to the given path."""
        q = "select p_id from puppetrepos where path = %s"
        self.cursor.execute(q, (path,))
        ret = resultSet(self.cursor)
        if ret.rowcount() == 0:
            return None
        return ret['p_id']

    def getPuppetDir(self, p_id):
        q = """select * from puppetrepos where p_id = %s"""
        self.cursor.execute(q, (p_id,))
        ret = resultSet(self.cursor)
        if ret.rowcount() == 0:
            return None
        
        return ret.dump()[0]

    def getAllPuppetDir(self):
        q = """select * from puppetrepos"""
        self.cursor.execute(q)
        return resultSet(self.cursor).dump()

    def setPuppetDept(self, p_id, dept_id):
        q = """update puppetrepos set dept_id = %s where p_id = %s"""
        self.cursor.execute(q, (dept_id, p_id))
        self.conn.commit()

    def insertPuppetDir(self, path, dept_id):
        q1 = """select p_id from puppetrepos where path = %s"""
        q2 = """insert into puppetrepos (path, dept_id)
                    values (%s, %s)"""

        self.cursor.execute(q1, (path, ))
        if self.cursor.rowcount > 1:
            log.warning("Database inconsistancy in puppetrepos table")
            log.warning("   Duplicate paths: %s" % path)
            return
        if self.cursor.rowcount == 1: return

        self.cursor.execute(q2, (path, dept_id))
        self.conn.commit()

    def cleanPuppetDirs(self, paths):
        q1 = """delete from puppetrepos where p_id = %s"""
        table = self.getAllPuppetDir()
        if len(paths) < 1: return
        if len(table) < 1: return

        # Make a dict for quick compares
        d = {}
        commit = False
        for i in table: d[i['path']] = i['p_id']
        for i in d.keys():
            if i not in paths:
                self.cursor.execute(q1, (d[i],))
                if not commit: commit = True

        if commit:
            self.conn.commit()


