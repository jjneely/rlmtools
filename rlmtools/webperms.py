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
from rlattributes import RLAttributes

logger = logging.getLogger('xmlrpc')

class Application(AppHelpers, RLAttributes):

    def __init__(self):
        AppHelpers.__init__(self)
        self._admin = AdminServer()

    def index(self, message=""):
        # Readable by any authenticated user
        if not self.isAuthenticated():
            return self.message("You do not appear to be authenticated.")

        subMenu = [
                    ('Manage ACLs',
                     '%s/admin/aclGroups' % url()),
                  ]
        depts = WebServer().getDepartments()
        a = Auth()
        acls = self._server.memberOfACL(a.userid)

        return self.render('perms.index',
                           dict(message=message,
                                depts=depts,
                                subMenu=subMenu,
                                title="Administration",
                                fullname=a.getName(),
                                acls=acls,
                                userid=a.userid,
                               ))
    index.exposed = True

