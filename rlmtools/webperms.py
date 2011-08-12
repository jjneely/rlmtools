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
from permServer import PermServer
from ldafs import *

logger = logging.getLogger('xmlrpc')

class Application(AppHelpers):

    def __init__(self):
        AppHelpers.__init__(self)
        self._misc = PermServer()

    def index(self, message=""):
        # Readable by any authenticated user
        if not self.isAuthenticated():
            return self.message("You do not appear to be authenticated.")

        subMenu = [
                    ('Manage ACLs',
                     '%s/perms/acl/' % url()),
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
        webksMap = self._misc.getAllWKSDir()

        subMenu = [
                    ('Manage ACLs',
                     '%s/perms/acl/' % url()),
                    ('Manage Web-Kickstart Directories',
                     '%s/perms/webkickstart' % url()),
                  ]

        return self.render('perms.webkickstart',
                           dict(message=message,
                                title="Web-Kickstart",
                                userid=a.userid,
                                subMenu=subMenu,
                                webksMap=[self.completeWKSInfo(i) \
                                          for i in webksMap ],
                               ))
    webkickstart.exposed = True

    def changeWKSDept(self, wkd_id, setDept=None, message=""):
        # Readable by any authenticated user
        if not self.isAuthenticated():
            return self.message("You do not appear to be authenticated.")

        subMenu = [
                    ('Manage Web-Kickstart Directories',
                     '%s/perms/webkickstart' % url()),
                  ]

        a = Auth()
        wkd_id = int(wkd_id)
        webksMap = self._misc.getWKSDir(wkd_id)
        depts = self._misc.getAllDepts()
        if webksMap is None:
            message = """A Web-Kickstart directory matching ID %s does
                         not exist.  Use the Back button and try your
                         query again.""" % wkd_id
            return self.message(message)
        if setDept is not None:
            dept_id = int(setDept)
            dept = self._misc.getDeptName(dept_id)
            if dept is None:
                message = """Department ID %s was not found.  This 
                             Web-Kickstart directory was not modified.""" \
                                     % dept_id
            else:
                self._misc.setWKSDept(wkd_id, dept_id)
                message = """Set department association to %s for
                Web-Kickstart directory %s.""" % (dept, webksMap['path'])
                return self.webkickstart(message)

        return self.render('perms.wksdept',
                           dict(message=message,
                                title="Web-Kickstart",
                                subMenu=subMenu,
                                userid=a.userid,
                                webksMap=self.completeWKSInfo(webksMap),
                                depts=depts,
                               ))
    changeWKSDept.exposed = True

    def completeWKSInfo(self, webks):
        # Complete the dict for the perm pages that deal with web-kickstarts
        # webks should be the output from _misc.getWKSDir() or one entry
        # from _misc.getAllWKSDir()

        i = webks.copy()
        i['dept'] = self._misc.getDeptName(i['dept_id'])
        i['bad_dept'] = i['dept'] is None

        # Build representation of AFS PTS groups
        i['pts'] = fsla(i['path'])

        # Include ACL information from LD department
        # Look and see if AFS PTS groups match the LD ACLs
        if i['bad_dept']:
            i['deptACLs'] = None
            i['perm_misalignment'] = True
            i['show_actions'] = False
        else:
            i['deptACLs'] = matchACLToAFS(
                    self._misc.getDeptACLs(i['dept_id']), True)
            misalignment = not equalACLs(i['pts'], i['deptACLs'], True)

            i['perm_misalignment'] = misalignment

        return i

