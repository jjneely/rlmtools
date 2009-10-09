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

PicType = 0
StrType = 1
NoneType = 2

logger = logging.getLogger('xmlrpc')

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

    def importWebKickstart(self, host_id):
        "Store the WebKickstart and important attributes in the database."
        from webKickstart.libwebks import LibWebKickstart

        aptr = self._admin.getHostAttrPtr(host_id)
        akeys = self._admin.getAttrKeys(aptr)
        ikeys = self._admin.getImportantKeys()
        webks = LibWebKickstart()
        data = webks.getEverything(self._admin.getHostName(host_id))

        # Store the entire parsed contents for future reference and a timestamp
        self._admin.removeAttributeByKey(aptr, 'meta.parsed')
        self._admin.removeAttributeByKey(aptr, 'meta.imported')
        blob = pickle.dumps(data)
        self._admin.setAttribute(aptr, 'meta.parsed', PicType, blob)
        self._admin.setAttribute(aptr, 'meta.imported', StrType, str(time.time()))

        for key in ikeys:
            if key in akeys:
                self._admin.removeAttributeByKey(aptr, key)
            if key in data:
                blob = pickle.dumps(data[key])
                self._admin.setAttribute(aptr, key, PicType, blob)
            else:
                self._admin.setAttribute(aptr, key, NoneType, None)

    def stringifyWebKS(self, table):
        return '\n'.join([ ' '.join(i) for i in table ])

    def parseAttrs(self, aptr):
        attrs = self._admin.getAllAttributes(aptr)
        attributes = {}
        meta = {}
        for row in attrs:
            if row['atype'] == PicType:
                try:
                    blob = self.stringifyWebKS(pickle.loads(row['data']))
                except EOFError:
                    logger.warning("EOFError reading pickle for host_id %s key %s"\
                                   % (host_id, row['akey']))
                    blob = "Error reading database."
            elif row['atype'] == NoneType:
                blob = None
            else:
                blob = row['data']

            if row['akey'].startswith('meta.'):
                meta[row['akey']] = blob
            else:
                attributes[row['akey']] = blob

        return meta, attributes

    def host(self, host_id, importWebKS=None):
        ikeys = self._admin.getImportantKeys()
        message = ''
        aptr = self._admin.getHostAttrPtr(host_id)

        if importWebKS is not None:
            self.importWebKickstart(host_id)

        meta, attributes = self.parseAttrs(aptr)

        if 'meta.imported' not in meta:
            message = "The Web-Kickstart data for this host needs to be imported."
        
        hostname = self._admin.getHostName(host_id)
        subMenu = [ ('Host: %s' % short(hostname),
                     '%s/client?host_id=%s' % (url(), host_id))
                  ]

        return self.render('admin.host', dict(
                             host_id=host_id,
                             subMenu=subMenu,
                             title=hostname,
                             message=message,
                             attributes=attributes,
                             webKickstartKeys=ikeys,
                             ))
    host.exposed = True

    def dept(self, dept_id):
        pass
