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

    def getHostAttrPtr(self, host_id): 
        return self._admin.getHostAttrPtr(host_id)

    def getDeptAttrPtr(self, dept_id):
        return self._admin.getDeptAttrPtr(dept_id)

    def importWebKickstart(self, host_id):
        "Store the WebKickstart and important attributes in the database."

        aptr = self._admin.getHostAttrPtr(host_id)
        akeys = self._admin.getAttrKeys(aptr)
        ikeys = self._admin.getImportantKeys()
        webks = LibWebKickstart()
        data = webks.getEverything(self._admin.getHostName(host_id))

        if data is None:
            return False

        # Store the entire parsed contents for future reference and a timestamp
        self._admin.removeAttributeByKey(aptr, 'meta.parsed')
        self._admin.removeAttributeByKey(aptr, 'meta.imported')
        blob = pickle.dumps(data)
        self._admin.setAttribute(aptr, 'meta.parsed', PicType, blob)
        self._admin.setAttribute(aptr, 'meta.imported', FloatType, 
                                 str(time.time()))

        for key, map in ikeys:
            if map is None:
                map = key    # Allow remmapping of variable/attr names
            if key in data and map in akeys:
                self._admin.removeAttributeByKey(aptr, map)
            if key in data:
                blob = pickle.dumps(data[key])
                self._admin.setAttribute(aptr, map, PicType, blob)
            # XXX: This just blocks inhairitance...why?    
            #else:
            #    self._admin.setAttribute(aptr, map, NoneType, None)

        return True

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

    def deptAttrs(self, dept_id, meta={}, attrs={}, markInhairited=False):
        ptr = self._admin.getDeptAttrPtr(dept_id)
        dbattrs = self._admin.getAllAttributes(ptr)
        m, a = self.parseAttrs(dbattrs)
        newKeys = a.keys() + m.keys()
        oldKeys = meta.keys() + attrs.keys()
        m.update(meta)
        a.update(attrs)

        if markInhairited:
            # Track keys that are inhairited
            if 'meta.inhairited' in m:
                inhairited = m['meta.inhairited']
            else:
                inhairited = []

            for k in newKeys:
                # Have we already found an inhairited key?
                if k in inhairited: continue
                # This key is not inhairited if its found lower in the tree
                if k in oldKeys: continue
                # OK: This key is inhairited and we've not found it before
                inhairited.append(k)
            m['meta.inhairited'] = inhairited
        else:
            m['meta.inhairited'] = []

        parent = self._admin.getDeptParentID(int(dept_id))
        if parent is not None:
            return self.deptAttrs(parent, m, a, markInhairited=True)
        else:
            return m, a

    def inhairitedAttrs(self, host_id):
        """Return a dict of attributes inhairited from departments."""

        dept_id = self._admin.getHostDept(host_id)
        return self.deptAttrs(dept_id, {}, {}, markInhairited=True)

    def hostAttrs(self, host_id):
        ptr = self._admin.getHostAttrPtr(host_id)
        dbattrs = self._admin.getAllAttributes(ptr)

        meta, attributes = self.inhairitedAttrs(host_id)
        m, a = self.parseAttrs(dbattrs)

        for key in meta['meta.inhairited']:
            if key in a:
                # We have a local version of this key that 
                # overrides the inharited
                meta['meta.inhairited'].remove(key)

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

    def removeAllHostAttrs(self, host_id):
        aptr = self._admin.getHostAttrPtr(host_id)
        self._admin.removeAllAttributes(aptr)

    def removeAllDeptAttrs(self, dept_id):
        aptr = self._admin.getDeptAttrPtr(dept_id)
        self._admin.removeAllAttributes(aptr)

    def removeAttributeByKey(self, attr_ptr, key):
        return self._admin.removeAttributeByKey(attr_ptr, key)

