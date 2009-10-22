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
import logging

from configDragon import config
from webcommon import *
from adminServer import AdminServer
from rlattributes import RLAttributes

logger = logging.getLogger('xmlrpc')

class Application(AppHelpers, RLAttributes):

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

    def host(self, host_id, importWebKS=None):
        aptr = self._admin.getHostAttrPtr(host_id)
        ikeys = self._admin.getImportantKeys()
        message = ''

        if importWebKS is not None:
            self.importWebKickstart(host_id)

        meta, attributes = self.hostAttrs(host_id)

        if 'meta.imported' not in meta:
            message = "The Web-Kickstart data for this host needs to be imported."
            importTime = "Never"
        else:
            importTime = time.strftime("%a, %d %b %Y %H:%M:%S %Z", \
                                       time.localtime(meta['meta.imported']))
        
        hostname = self._admin.getHostName(host_id)
        subMenu = [ ('%s Status Panel' % short(hostname),
                     '%s/client?host_id=%s' % (url(), host_id))
                  ]

        return self.render('admin.host', dict(
                             host_id=host_id,
                             attr_ptr=aptr,
                             subMenu=subMenu,
                             title=hostname,
                             message=message,
                             attributes=attributes,
                             meta=meta,
                             importTime=importTime,
                             webKickstartKeys=ikeys,
                             ))
    host.exposed = True

    def dept(self, dept_id):
        pass

    def modifyHost(self, host_id, modifyKey, textbox=None,
                   setAttribute=None, reset=None, modify=None):
        if setAttribute == "Submit":
            aptr = self._admin.getHostAttrPtr(host_id)
            self.setAttribute(aptr, modifyKey, textbox)
            # Set the value and redirect to the Host Admin Panel
            return self.host(host_id)
        meta, attributes = self.hostAttrs(host_id)
        attributes.update(meta)
        hostname = self._admin.getHostName(host_id)

        if len(attributes) > 1:
            logger.warning("DB Issues: multiple identical keys for host %s" \
                           % host_id)
        if modifyKey in attributes:
            replaceValue = attributes[modifyKey]
        else:
            replaceValue = None

        subMenu = [ ('%s Admin Panel' % short(hostname),
                     '%s/admin/host?host_id=%s' % (url(), host_id))
                  ]

        return self.render('admin.modifyHost', dict(
                           subMenu=subMenu,
                           message='',
                           title=hostname,
                           host_id=host_id,
                           key=modifyKey,
                           replaceValue=replaceValue,
                           ))
    modifyHost.exposed = True

