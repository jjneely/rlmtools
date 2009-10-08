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
        blob = self.conn.escape_string(blob)
        key = self.conn.escape_string(key)
        
        self.cursor.execute(q1, (key, typeblob, blob))
        self.cursor.execute(q2)
        id = self.cursor.fetchone()[0]
        return id

    def associateAttribute(self, attr_ptr, attr_id):
        """Associate an attribute ID with an attribute pointer (and therefore
           a host or a dept."""

        q = "insert into attrgroups (attr_ptr, attr_id) values (%s, %s)"

        self.cursor.execute(q, (attr_ptr, attr_id))

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

    def getAttributes(self, attr_ptr, key):
        "Return a list of attributes for the pointer group matching key"

        q = """select a.attr_id, a.data, a.atype, a.akey from 
                   attributes as a, attrgroups as b where
               b.attr_id = a.attr_id and
               a.akey = %s and
               b.attr_ptr = %s"""

        self.cursor.execute(q, (key, attr_ptr))
        return resultSet(self.cursor).dump()

    def removeAttribute(self, attr_ptr, attr_id):
        "Remove the association of an attribute from a attr_ptr group"

        q1 = "delete from attrgroups where attr_ptr = %s and attr_id = %s"
        q2 = "delete from attributes where attr_id = %s"
        self.cursor.execute(q1, (attr_ptr, attr_id))
        self.cursor.execute(q2, (attr_id,))
        self.conn.commit()

    def getAttrKeys(self, attr_ptr):
        "Return a list of the keys an attr pointer references."

        q = """select distinct a.akey from attributes as a, attrgroups as b where
               a.attr_id = b.attr_id and
               b.attr_ptr = %s"""

        self.cursor.execute(q, (attr_ptr,))
        result = resultSet(self.cursor)
        return [ r['akey'] for r in result ]

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
