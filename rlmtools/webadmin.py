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
import time
import cPickle as pickle

from configDragon import config
from webcommon import *
from adminServer import AdminServer

PicType = 0
StrType = 1

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

    def host(self, host_id, importWebKS=False):
        message = ''
        aptr = self._admin.getHostAttrPtr(host_id)
        attrs = self._admin.getAllAttributes(aptr)

        attributes = {}
        for row in attrs:
            if row['atype'] == PicType:
                blob = pickle.dumps(row['data'])
            else:
                blob = row['data']
            attributes[row['akey']] = blob

        if 'meta.imported' not in attributes:
            message = "The Web-Kickstart data for this host needs to be imported."
    
        return self.render('admin.host', dict(
                             host_id=host_id,
                             title=self._admin.getHostName(host_id),
                             message=message,
                             attributes=attributes,
                             ))
    host.exposed = True

    def dept(self, dept_id):
        pass
