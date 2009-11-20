#!/usr/bin/python
#
# adminServer.py - SQL functions for admin tools in RLMTools
# Copyright (C) 2009 NC State University
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

from resultSet import resultSet

log = logging.getLogger("xmlrpc")

# Attribute API Notes:
#   To get/store an attribute on a dept or host call
#      getHostPtr() or getDeptPtr() to get the reference pointer
#      Next, call getAttributes(ptr, type) where type is a app defined int
#         This will return a list
#      Call setAttribute(ptr, type, blob) to store
#   To remove call removeAttribute(ptr, id) where the id is the attr_id field
#      returned by getAttributes and references the actual attribute blob.

class AdminServer(server.Server):

    def newAttrPtr(self):
        "Create a new attribute pointer and return it."

        q1 = "insert into attrpointer () values ()"
        q2 = "select LAST_INSERT_ID()"

        self.cursor.execute(q1)
        self.cursor.execute(q2)
        ptr = self.cursor.fetchone()[0]
        return ptr

    def storeAttrBlob(self, key, typeblob, blob):
        "Store and return the ID for this data"

        q1 = "insert into attributes (akey, atype, data) values (%s, %s, %s)"
        q2 = "select LAST_INSERT_ID()"

        if type(blob) != type(""):
            blob = str(blob)
        
        self.cursor.execute(q1, (key, typeblob, blob))
        self.cursor.execute(q2)
        id = self.cursor.fetchone()[0]
        return id

    def associateAttribute(self, attr_ptr, attr_id):
        """Associate an attribute ID with an attribute pointer (and therefore
           a host or a dept."""

        q = "insert into attrgroups (attr_ptr, attr_id) values (%s, %s)"

        self.cursor.execute(q, (attr_ptr, attr_id))

    def isHostAttrPtr(self, ptr):
        q = "select host_id from realmlinux where attr_ptr = %s"
        self.cursor.execute(q, (ptr,))
        r = resultSet(self.cursor)
        return r.rowcount() > 0

    def getHostAttrPtr(self, host_id):
        q1 = "select attr_ptr from realmlinux where host_id = %s"
        q2 = "update realmlinux set attr_ptr = %s where host_id = %s"
        self.cursor.execute(q1, (host_id,))
        ptr = self.cursor.fetchone()[0]

        if ptr is None:
            ptr = self.newAttrPtr()
            self.cursor.execute(q2, (ptr, host_id))
            self.conn.commit()

        return ptr

    def getDeptAttrPtr(self, dept_id):
        q1 = "select attr_ptr from dept where dept_id = %s"
        q2 = "update dept set attr_ptr = %s where dept_id = %s"
        self.cursor.execute(q1, (dept_id,))
        ptr = self.cursor.fetchone()[0]

        if ptr is None:
            ptr = self.newAttrPtr()
            self.cursor.execute(q2, (ptr, dept_id))
            self.conn.commit()

        return ptr

    def setAttribute(self, attr_ptr, akey, atype, blob):
        "Store an attribute linked to an attribute group"

        id = self.storeAttrBlob(akey, atype, blob)
        self.associateAttribute(attr_ptr, id)
        self.conn.commit()

    def getAllAttributes(self, attr_ptr):
        q = """select a.attr_id, a.data, a.atype, a.akey from
               attributes as a, attrgroups as b where
               b.attr_id = a.attr_id and
               b.attr_ptr = %s"""

        self.cursor.execute(q, (attr_ptr,))
        return resultSet(self.cursor).dump()

    def getAttributes(self, attr_ptr, key):
        "Return a list of attributes for the pointer group matching key"

        q = """select a.attr_id, a.data, a.atype, a.akey from 
                   attributes as a, attrgroups as b where
               b.attr_id = a.attr_id and
               a.akey = %s and
               b.attr_ptr = %s"""

        self.cursor.execute(q, (key, attr_ptr))
        return resultSet(self.cursor).dump()

    def removeAttributeByKey(self, attr_ptr, key):
        q = """select a.attr_id from attributes as a, attrgroups as b where
               b.attr_id = a.attr_id and
               a.akey = %s and
               b.attr_ptr = %s"""

        self.cursor.execute(q, (key, attr_ptr))
        result = resultSet(self.cursor).dump()
        for row in result:
            self.removeAttribute(attr_ptr, row['attr_id'])

    def removeAttribute(self, attr_ptr, attr_id):
        "Remove the association of an attribute from a attr_ptr group"

        q1 = "delete from attrgroups where attr_ptr = %s and attr_id = %s"
        q2 = "delete from attributes where attr_id = %s"
        self.cursor.execute(q1, (attr_ptr, attr_id))
        self.cursor.execute(q2, (attr_id,))
        self.conn.commit()

    def removeAllAttributes(self, attr_ptr):
        "Remove all attributes associated with this pointer"
        q1 = "select attr_id from attrgroups where attr_ptr = %s"
        q2 = "delete from attrgroups where attr_ptr = %s"
        q3 = "delete from attributes where attr_id = %s"

        self.cursor.execute(q1, (attr_ptr,))
        result = resultSet(self.cursor).dump()
        for row in result:
            self.cursor.execute(q3, (row['attr_id']))

        self.cursor.execute(q2, (attr_ptr,))
        self.conn.commit()

    def getAttrKeys(self, attr_ptr):
        "Return a list of the keys an attr pointer references."

        q = """select distinct a.akey from attributes as a, attrgroups as b where
               a.attr_id = b.attr_id and
               b.attr_ptr = %s"""

        self.cursor.execute(q, (attr_ptr,))
        result = resultSet(self.cursor)
        return [ r['akey'] for r in result ]

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

    def getPTSGroups(self):
        """Returns a list of dicts"""

        q = "select acl_id, name, pts, cell from acls"
        self.cursor.execute(q)
        return resultSet(self.cursor).dump()

    def getSysAdmins(self, acl_id):
        q = """select distinct userid, sysadmin_id from sysadmins 
               where acl_id = %s order by userid"""

        self.cursor.execute(q, (acl_id,))
        result = resultSet(self.cursor)
        return [ row['userid'] for row in result ]

    def getImportantKeys(self):
        q = "select keyword from webkickstartkeys"
        self.cursor.execute(q)
        result = resultSet(self.cursor)

        return [ row['keyword'] for row in result ]
