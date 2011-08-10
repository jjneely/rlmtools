# webadmin.py - Admin pages for RLMTools
#
# Copyright 2011 NC State University
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

import optparse
import cherrypy
import sys
import os
import os.path
import time
import cPickle as pickle
import logging
import re

from configDragon import config
from webcommon import *
from adminServer import AdminServer
from webServer import WebServer
from miscServer import MiscServer

logger = logging.getLogger('xmlrpc')

class Application(AppHelpers):

    def __init__(self):
        AppHelpers.__init__(self)
        self._misc = MiscServer()

    def index(self, message=""):
        # Readable by any authenticated user
        if not self.isAuthenticated():
            return self.message("You do not appear to be authenticated.")

        subMenu = [
                    ('Manage ACLs',
                     '%s/admin/aclGroups' % url()),
                    ('Manage Web-Kickstart Directories',
                     '%s/perms/webkickstart' % url()),
                  ]
        depts = WebServer().getDepartments()
        a = Auth()
        acls = self._server.memberOfACL(a.userid)

        return self.render('perms.index',
                           dict(message=message,
                                depts=depts,
                                subMenu=subMenu,
                                title="Permissions",
                                fullname=a.getName(),
                                acls=acls,
                                userid=a.userid,
                               ))
    index.exposed = True

    def webkickstart(self, message=""):
        # Readable by any authenticated user
        if not self.isAuthenticated():
            return self.message("You do not appear to be authenticated.")

        a = Auth()
        webksMap = self._misc.getAllWebKSDir()

        # Map AFS permissions to our admin/write/read scheme
        rights = {'l':       'look',
                  'rl':      'read',
                  'rlidwk':  'write',
                  'rlidwka': 'admin' }
        for i in webksMap:
            i['pts'] = []
            i['dept'] = self._misc.getDeptName(i['dept_id'])
            i['bad_dept'] = i['dept'] is None

            # Build representation of AFS PTS groups
            ptsacls = fsla(i['path'])
            for pts, perms in ptsacls:
                if pts == 'system:administrators' or pts.startswith('admin:'):
                    continue
                if perms in rights:
                    i['pts'].append((pts, rights[perms]))
                else:
                    i['pts'].append((pts, 'other'))

            # Include ACL information from LD department
            # Look and see if AFS PTS groups match the LD ACLs
            if i['bad_dept']:
                i['deptACLs'] = None
                i['perm_misalignment'] = True
                i['show_actions'] = False
            else:
                i['deptACLs'] = []
                deptACLs = self._misc.getDeptACLs(i['dept_id'])
                misalignment = False
                for j in deptACLs:
                    if not (self.isADMIN(j['perms']) or \
                            self.isWRITE(j['perms'])):
                        # LD READ access does not equate to AFS WKS READ
                        # access.  We remove this ACL from consideration
                        continue

                    # When we only have read access in AFS and admin access
                    # in LD -- this is correct.  As well as admin/admin
                    if self.isADMIN(j['perms']):
                        if not ((j['pts'], 'admin') in i['pts'] or
                                (j['pts'], 'write') in i['pts']):
                            misalignment = True
                    else:
                        if (j['pts'], self.mapPermBits(j['perms'])) not in i['pts']:
                            misalignment = True

                    i['deptACLs'].append((j['name'], j['pts'],
                                          self.mapPermBits(j['perms']) ))

                # Do we have the same number of ACLs in both lists now?
                if len(i['deptACLs']) != len(i['pts']):
                    misalignment = True

                i['perm_misalignment'] = misalignment
                i['show_actions'] = misalignment

        return self.render('perms.webkickstart',
                           dict(message=message,
                                title="Web-Kickstart",
                                userid=a.userid,
                                webksMap=webksMap,
                               ))
    webkickstart.exposed = True


