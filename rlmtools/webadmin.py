# webadmin.py - Admin pages for RLMTools
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

from configDragon import config
from webcommon import *
from adminServer import AdminServer

class Application(AppHelpers):

    def __init__(self):
        AppHelpers.__init__(self)
        self._admin = AdminServer()

    def index(self):
        ptsgroups = self._admin.getPTSGroups()
        for pts in ptsgroups:
            pts['ids'] = self._admin.getSysAdmins(pts['acl_id'])

        return self.render('admin.index', 
                           dict(ptsgroups=ptsgroups))
    index.exposed = True



