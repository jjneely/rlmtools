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

    def host(self, host_id, importWebKS=None):
        dept_id = self._admin.getHostDept(host_id)
        deptname = self._admin.getDeptName(dept_id)
        if not self.isADMIN(self.getAuthZ(dept_id)):
            return self.message("You need %s level admin access to view "
                                "host attributes." % deptname)

        ikeys = self._admin.getImportantKeys()
        message = ''

        if importWebKS is not None:
            if not self.isWRITE(self.getAuthZ(dept_id)):
                return self.message("You need %s level write access to set "
                                "attributes." % deptname)
            try:
                if not self.importWebKickstart(host_id):
                    message="Error Importing Web-Kickstart Configuration"
            except Exception, e:
                message = "Exception Importing Web-Kickstart: %s" % str(e)

        meta, attributes = self.hostAttrs(host_id)

        # Don't display encrypt secrets fully
        regex = re.compile(r"([-a-zA-Z0-9]+) ([a-zA-Z0-9]+)")
        for a in ['root', 'users']:
            if a in attributes and isinstance(attributes[a], str):
                match = regex.match(attributes[a])
                if match is None: continue
                attributes[a] = "%s ...%s [Secret Obscured]" % \
                        (match.group(1), match.group(2)[:6])

        if 'meta.imported' not in meta:
            if message == "":
                message = "The Web-Kickstart data for this host needs to be imported."
            importTime = "Never"
        else:
            importTime = time.strftime("%a, %d %b %Y %H:%M:%S %Z", \
                                       time.localtime(meta['meta.imported']))
        
        hostname = self._admin.getHostName(host_id)
        subMenu = [ ('Host Status: %s' % short(hostname),
                     '%s/client?host_id=%s' % (url(), host_id)),
                    ('Department Status: %s' % deptname,
                     '%s/dept?dept_id=%s' % (url(), dept_id)),
                    ('Manage Department Attributes: %s' % deptname,
                     '%s/admin/dept?dept_id=%s' % (url(), dept_id)),
                  ]

        return self.render('admin.host', dict(
                             host_id=host_id,
                             subMenu=subMenu,
                             title='Host Admin Panel',
                             hostname=hostname,
                             deptname=deptname,
                             message=message,
                             attributes=attributes,
                             meta=meta,
                             importTime=importTime,
                             webKickstartKeys=ikeys,
                             ))
    host.exposed = True

    def dept(self, dept_id):
        deptname = self._admin.getDeptName(int(dept_id))
        if not self.isADMIN(self.getAuthZ(dept_id)):
            return self.message("You need %s level admin access to view "
                                "department attributes." % deptname)

        message = ''

        meta, attributes = self.deptAttrs(dept_id)

        deptname = self._admin.getDeptName(dept_id)
        subMenu = [ ('Deptartment Status: %s' % deptname,
                     '%s/dept?dept_id=%s' % (url(), dept_id))
                  ]

        return self.render('admin.dept', dict(
                             dept_id=dept_id,
                             deptname=deptname,
                             subMenu=subMenu,
                             title='Manage Department Attributes',
                             message=message,
                             attributes=attributes,
                             meta=meta,
                             ))
    dept.exposed = True

    def deleteHostAttr(self, modifyKey, host_id=None,
                       submit=None, aptr=None, callback=None):
        if submit is not None:
            if callback is None:
                return self.message(
                        "Interal application fault in deleteHostAttr()")
            host_id = int(callback)
        dept_id = self._admin.getHostDept(int(host_id))
        deptname = self._admin.getDeptName(dept_id)
        hostname = self._admin.getHostName(int(host_id))
        aptr = self._admin.getHostAttrPtr(int(host_id))

        if not self.isWRITE(self.getAuthZ(dept_id)):
            return self.message("You need %s level write access to remove "
                                    "attributes." % deptname)

        if submit is not None:
            self.removeAttributeByKey(aptr, modifyKey)
            # To reuse the template we stuck this in 'callback'
            return self.host(host_id)

        subMenu = [ ('Manage Host Attributes: %s' % short(hostname),
                     '%s/admin/host?host_id=%s' % (url(), int(host_id)))
                  ]

        meta, attributes = self.hostAttrs(host_id)
        if modifyKey not in attributes:
            return self.message("%s is not an attribute of %s" \
                                % (modifyKey, hostname))

        if modifyKey in ['root', 'users']:
            value = "[Secret Obscured]"
        else:
            value = attributes[modifyKey]
        return self.render('admin.delattr', dict(
                           subMenu=subMenu,
                           title=hostname,
                           key=modifyKey,
                           value=value,
                           message="",
                           callback=host_id,
                           call="deleteHostAttr",
                           ))
    deleteHostAttr.exposed = True

    def deleteDeptAttr(self, modifyKey, dept_id=None,
                       submit=None, aptr=None, callback=None):
        if submit is not None:
            if callback is None:
                return self.message(
                        "Interal application fault in deleteDeptAttr()")
            dept_id = int(callback)
        deptname = self._admin.getDeptName(int(dept_id))
        aptr = self._admin.getDeptAttrPtr(int(dept_id))

        if not self.isWRITE(self.getAuthZ(dept_id)):
            return self.message("You need %s level write access to remove "
                                    "attributes." % deptname)

        if submit is not None:
            self.removeAttributeByKey(aptr, modifyKey)
            # To reuse the template we stuck this in 'callback'
            return self.dept(int(dept_id))

        subMenu = [ ('Manage Department Attributes: %s' % deptname,
                     '%s/admin/dept?dept_id=%s' % (url(), int(dept_id)))
                  ]

        meta, attributes = self.deptAttrs(dept_id)
        if modifyKey not in attributes:
            return self.message("%s is not an attribute of %s" \
                                % (modifyKey, deptname))

        return self.render('admin.delattr', dict(
                           subMenu=subMenu,
                           title=deptname,
                           key=modifyKey,
                           value=attributes[modifyKey],
                           message="",
                           callback=dept_id,
                           call="deleteDeptAttr",
                           ))
    deleteDeptAttr.exposed = True

    def modifyHost(self, host_id, modifyKey, textbox=None,
                   setAttribute=None, reset=None, delete=None, modify=None):
        # XXX: check for altering meta. keys??
        dept_id = self._admin.getHostDept(int(host_id))
        deptname = self._admin.getDeptName(dept_id)

        if setAttribute == "Submit":
            if not self.isWRITE(self.getAuthZ(dept_id)):
                return self.message("You need %s level write access to set "
                                    "attributes." % deptname)
            aptr = self._admin.getHostAttrPtr(host_id)
            self.setAttribute(aptr, modifyKey, textbox)
            # Set the value and redirect to the Host Admin Panel
            return self.host(host_id)

        meta, attributes = self.hostAttrs(host_id)
        attributes.update(meta)
        hostname = self._admin.getHostName(host_id)

        if delete == "Delete":
            if 'meta.inhairited' in meta:
                if modifyKey in meta['meta.inhairited']:
                    return self.message(
                            "The attribute %s is inhairited from a higher "
                            "order department.  It cannot be deleted from "
                            "this host: %s" % (modifyKey, hostname))

            return self.deleteHostAttr(modifyKey, host_id)

        if not self.isADMIN(self.getAuthZ(dept_id)):
            return self.message("You need %s level admin access to view "
                                "host attributes." % deptname)

        replaceValue = None
        if reset == "Reset":
            if 'meta.parsed' in attributes and \
                    modifyKey in attributes['meta.parsed']:
                replaceValue = \
                    self.stringifyWebKS(attributes['meta.parsed'][modifyKey])
            else:
                m, a = self.inhairitedAttrs(host_id)
                a.update(m)
                if modifyKey in a:
                    replaceValue = a[modifyKey]

        elif modifyKey in attributes:
            replaceValue = attributes[modifyKey]

        subMenu = [ ('Manage Host Attributes: %s' % short(hostname),
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

    def modifyDept(self, dept_id, modifyKey, textbox=None,
                   setAttribute=None, reset=None, delete=None, modify=None):
        # XXX: check for altering meta. keys??
        deptname = self._admin.getDeptName(int(dept_id))

        if setAttribute == "Submit":
            if not self.isWRITE(self.getAuthZ(dept_id)):
                return self.message("You need %s level write access to set "
                                    "attributes." % deptname)
            aptr = self._admin.getDeptAttrPtr(dept_id)
            self.setAttribute(aptr, modifyKey, textbox)
            # Set the value and redirect to the Dept Admin Panel
            return self.dept(dept_id)

        if not self.isADMIN(self.getAuthZ(dept_id)):
            return self.message("You need %s level admin access to view "
                                "attributes." % deptname)

        meta, attributes = self.deptAttrs(dept_id)
        attributes.update(meta)
        deptname = self._admin.getDeptName(dept_id)

        if delete == "Delete":
            if 'meta.inhairited' in meta:
                if modifyKey in meta['meta.inhairited']:
                    return self.message(
                            "The attribute %s is inhairited from a higher "
                            "order department.  It cannot be deleted from "
                            "this department: %s" % (modifyKey, deptname))

            return self.deleteDeptAttr(modifyKey, int(dept_id))

        replaceValue = None
        if reset == "Reset":
            parent = self._admin.getDeptParentID(int(dept_id))
            if parent is not None:
                m, a = self.deptAttrs(parent)
                a.update(m)
                if modifyKey in a:
                    replaceValue = a[modifyKey]

        elif modifyKey in attributes:
            replaceValue = attributes[modifyKey]

        subMenu = [ ('Manage Department Attributes: %s' % deptname,
                     '%s/admin/dept?dept_id=%s' % (url(), dept_id))
                  ]

        return self.render('admin.modifyDept', dict(
                           subMenu=subMenu,
                           message='',
                           title='Modify Attribute',
                           deptname=deptname,
                           dept_id=dept_id,
                           key=modifyKey,
                           replaceValue=replaceValue,
                           ))
    modifyDept.exposed = True

