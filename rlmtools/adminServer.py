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

from datetime import datetime, timedelta
from resultSet import resultSet

log = logging.getLogger("xmlrpc")

class AdminServer(server.Server):

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
