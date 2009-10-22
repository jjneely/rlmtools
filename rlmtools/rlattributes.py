# rlattributes.py - Interface for dealing with host/dept attributes
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

import sys
import os
import os.path
import time
import cPickle as pickle
import logging

from webKickstart.libwebks import LibWebKickstart
from adminServer import AdminServer

PicType = 0
StrType = 1
NoneType = 2
FloatType = 3

logger = logging.getLogger('xmlrpc')

class RLAttributes(object):

    def __init__(self):
        self._admin = AdminServer()

    def importWebKickstart(self, host_id):
        "Store the WebKickstart and important attributes in the database."

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
        self._admin.setAttribute(aptr, 'meta.imported', FloatType, 
                                 str(time.time()))

        for key in ikeys:
            if key in akeys:
                self._admin.removeAttributeByKey(aptr, key)
            if data is not None and key in data:
                blob = pickle.dumps(data[key])
                self._admin.setAttribute(aptr, key, PicType, blob)
            else:
                self._admin.setAttribute(aptr, key, NoneType, None)

    def stringifyWebKS(self, table):
        # If this looks like webKickstart data, morph it into normal data
        if type(table) == type([]) and len(table) > 0 and \
                type(table[0]) == type([]):
            return '\n'.join([ ' '.join(i) for i in table ])
        else:
            return table

    def parseAttrs(self, dbattrs):
        attributes = {}
        meta = {}
        for row in dbattrs:
            if row['atype'] == PicType:
                try:
                    blob = self.stringifyWebKS(pickle.loads(row['data']))
                except EOFError:
                    logger.warning("EOFError reading pickle for host_id %s key %s"\
                                   % (host_id, row['akey']))
                    blob = "Error reading database."
            elif row['atype'] == NoneType:
                blob = None
            elif row['atype'] == FloatType:
                blob = float(row['data'])
            else:
                blob = row['data']

            if row['akey'].startswith('meta.'):
                meta[row['akey']] = blob
            else:
                attributes[row['akey']] = blob

        return meta, attributes

    def inhairitedAttrs(self, host_id):
        """Return a dict of attributes inhairited from departments."""

        def rHelper(dept_id, meta, attrs):
            ptr = self._admin.getDeptAttrPtr(dept_id)
            dbattrs = self._admin.getAllAttributes(ptr)
            m, a = self.parseAttrs(dbattrs)
            newKeys = a.keys() + m.keys()
            m.update(meta)
            a.update(attrs)

            # Track keys that are inhairited
            if 'meta.inhairited' in m:
                inhairited = m['meta.inhairited']
            else:
                inhairited = []

            for k in newKeys:
                if k in inhairited: continue
                inhairited.append(k)
            m['meta.inhairited'] = inhairited

            parent = self._admin.getDeptParentID(dept_id)
            if parent is not None:
                return rHelper(parent, m, a)
            else:
                return m, a

        dept_id = self._admin.getHostDept(host_id)
        return rHelper(dept_id, {}, {})

    def hostAttrs(self, host_id):
        ptr = self._admin.getHostAttrPtr(host_id)
        dbattrs = self._admin.getAllAttributes(ptr)

        meta, attributes = self.inhairitedAttrs(host_id)
        m, a = self.parseAttrs(dbattrs)
        meta.update(m)
        attributes.update(a)
        return meta, attributes

    def getHostAttr(self, host_id, key):
        m, a = self.hostAttrs(host_id)
        if key in m:
            return m[ke]
        elif key in a:
            return a[key]
        else:
            return None

    def setAttribute(self, attr_ptr, key, value):
        attrs = self._admin.getAttributes(attr_ptr, key)
        for row in attrs:
            if row['akey'] == key:
                self._admin.removeAttributeByKey(attr_ptr, key)
        
        if type(value) == type(0.1):
            t = FloatType
            blob = str(value)
        elif type(value) == type(1):
            t = IntType
            blob = str(value)
        elif value is None:
            t = NoneType
            blob = ""
        elif type(value) == type(""):
            t = StrType
            blob = value
        else:
            t = PicType
            blob = pickle.dumps(value)

        self._admin.setAttribute(attr_ptr, key, t, blob)

    def setHostAttribute(self, host_id, key, value):
        aptr = self._admin.getHostAttrPtr(host_id)
        return self.setAttribute(aptr, key, value)

