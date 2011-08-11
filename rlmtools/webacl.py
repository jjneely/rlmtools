# webacl.py -- Manage RLMTools ACLs
#
# Copyright, 2009 Jack Neely <jjneely@ncsu.edu>
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
from rlattributes import RLAttributes

logger = logging.getLogger('xmlrpc')

class Application(AppHelpers, RLAttributes):

    def __init__(self):
        AppHelpers.__init__(self)
        self._admin = AdminServer()

    def index(self):
        # Readable by any authenticated user
        if not self.isREAD(self.getAuthZ("root")):
            return self.message("You need root level read access to view "
                                "ACLs.")

        ptsgroups = self._admin.getPTSGroups()

        return self.render('acl.index', 
                           dict(ptsgroups=ptsgroups,
                                title="Manage ACLs",
                               ))
    index.exposed = True

    def newACL(self, cell, ptsGroup, aclName):
        # You need admin access to mess with ACLs
        if not self.isADMIN(self.getAuthZ("root")):
            return self.message("You need root level admin access to modify "
                                "ACLs.")

        self._admin.createACL(aclName, ptsGroup, cell)
        return self.index()
    newACL.exposed = True

    def removeACL(self, acl_id, consent=None):
        if not self.isADMIN(self.getAuthZ("root")):
            return self.message("You need root level admin access to modify "
                                "ACLs.")

        if consent == "yes":
            self._admin.removeACL(acl_id)
            return self.index()
        if consent == "no":
            return self.index()

        acl = self._admin.getACL(int(acl_id))
        return self.render('acl.remove', dict(
            title="Delete ACL",
            aclname=acl['name'],
            acl_id=acl_id,
            ))
    removeACL.exposed = True

    def permissions(self, acl_id):
        if not self.isREAD(self.getAuthZ("root")):
            return self.message("You need root level read access to view "
                                "ACLs.")

        subMenu = [
                    ('Manage ACLs',
                     '%s/perms/acl' % url()),
                  ]

        acl = self._admin.getACL(int(acl_id))
        depts = self._admin.getPermsForACL(int(acl_id))
        users = self._admin.getSysAdmins(acl_id)

        for i in depts:
            i['write'] = self.isWRITE(i['perms'])
            i['read'] = self.isREAD(i['perms'])
            i['admin'] = self.isADMIN(i['perms'])

        return self.render('acl.mod', dict(
            deptlist=self._admin.getAllDepts(),
            users=users,
            acl_id=acl_id,
            title="ACL Permissions",
            aclname=acl['name'],
            depts=depts,
            subMenu=subMenu,
            ))
    permissions.exposed = True

    def addPerm(self, dept_id, acl_id, read=None, write=None, admin=None):
        if not self.isADMIN(self.getAuthZ("root")):
            return self.message("You need root level admin access to modify "
                                "ACLs.")

        dept_id = int(dept_id)
        acl_id = int(acl_id)
        perms = self._admin.getPermsForACL(acl_id)

        for i in perms:
            # See if we are modifying an existing permission
            if i['dept_id'] == dept_id:
                self._admin.removePerm(i['aclg_id'])

        field = 0
        if read == "True":
            field = field | self.READ
        if write == "True":
            field = field | self.WRITE
        if admin == "True":
            field = field | self.ADMIN

        self._admin.setPerm(acl_id, dept_id, field)

        return self.permissions(acl_id)
    addPerm.exposed = True

    def removePerm(self, acl_id, aclg_id):
        if not self.isADMIN(self.getAuthZ("root")):
            return self.message("You need root level admin access to modify "
                                "ACLs.")

        self._admin.removePerm(int(aclg_id))
        return self.permissions(int(acl_id))
    removePerm.exposed = True

