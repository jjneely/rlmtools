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

    def index(self, message=""):
        depts = WebServer().getDepartments()
        return self.render('admin.index', 
                           dict(message=message,
                                depts=depts,
                               ))
    index.exposed = True

    def aclGroups(self, cell=None, ptsGroup=None, aclName=None):
        if cell is not None and ptsGroup is not None and aclName is not None:
            self._admin.createACL(aclName, ptsGroup, cell)

        ptsgroups = self._admin.getPTSGroups()
        #for pts in ptsgroups:
        #    pts['ids'] = self._admin.getSysAdmins(pts['acl_id'])

        return self.render('admin.aclgroups', 
                           dict(ptsgroups=ptsgroups))
    aclGroups.exposed = True

    def host(self, host_id, importWebKS=None):
        #aptr = self._admin.getHostAttrPtr(host_id)
        ikeys = self._admin.getImportantKeys()
        message = ''

        if importWebKS is not None:
            if not self.importWebKickstart(host_id):
                message="Error Importing Web-Kickstart Configuration"

        meta, attributes = self.hostAttrs(host_id)

        if 'meta.imported' not in meta:
            if message == "":
                message = "The Web-Kickstart data for this host needs to be imported."
            importTime = "Never"
        else:
            importTime = time.strftime("%a, %d %b %Y %H:%M:%S %Z", \
                                       time.localtime(meta['meta.imported']))
        
        hostname = self._admin.getHostName(host_id)
        dept_id = self._admin.getHostDept(host_id)
        deptname = self._admin.getDeptName(dept_id)
        subMenu = [ ('%s Status Panel' % short(hostname),
                     '%s/client?host_id=%s' % (url(), host_id)),
                    ('%s Status Panel' % deptname,
                     '%s/dept?dept_id=%s' % (url(), dept_id)),
                    ('%s Admin Panel' % deptname,
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
        message = ''

        meta, attributes = self.deptAttrs(dept_id)

        deptname = self._admin.getDeptName(dept_id)
        subMenu = [ ('%s Status Panel' % deptname,
                     '%s/dept?dept_id=%s' % (url(), dept_id))
                  ]

        return self.render('admin.dept', dict(
                             dept_id=dept_id,
                             deptname=deptname,
                             subMenu=subMenu,
                             title='Department Admin Panel',
                             message=message,
                             attributes=attributes,
                             meta=meta,
                             ))
    dept.exposed = True

    def modifyHost(self, host_id, modifyKey, textbox=None,
                   setAttribute=None, reset=None, modify=None):
        # XXX: check for altering meta. keys??
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

    def modifyDept(self, dept_id, modifyKey, textbox=None,
                   setAttribute=None, reset=None, modify=None):
        # XXX: check for altering meta. keys??
        if setAttribute == "Submit":
            aptr = self._admin.getDeptAttrPtr(dept_id)
            self.setAttribute(aptr, modifyKey, textbox)
            # Set the value and redirect to the Dept Admin Panel
            return self.dept(dept_id)
        meta, attributes = self.deptAttrs(dept_id)
        attributes.update(meta)
        deptname = self._admin.getDeptName(dept_id)

        if len(attributes) > 1:
            logger.warning("DB Issues: multiple identical keys for dept %s" \
                           % dept_id)

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

        subMenu = [ ('%s Admin Panel' % deptname,
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

    def createDept(self, textBox, options=[]):
        # Create a remedy request and return some goodness
        regex = "^[-a-z0-9]+$"
        print textBox
        print re.search(regex, textBox)

        if textBox.strip() == "" or re.search(regex, textBox) is None:
            return self.index("Illegal department name.  Must match %s" % regex)
        else:
            # this creates the dept in the DB
            id = self._admin.getDeptID(textBox)

        o = {}
        for i in ['afscron', 'webks', 'bcfg2', 'admins']:
            if i in options:
                o[i] = True
            else:
                o[i] = False

        fd = os.popen("/usr/sbin/sendmail -t", 'w')
        fd.write("From: nobody@ncsu.edu\n")  # XXX: Needs to be the auth'd user
        fd.write("To: linux@help.ncsu.edu\n")  
        fd.write("Subject: Create LD Department\n\n")
        
        fd.write("User %s has requested the creation of RLMT Department %s.\n" \
                 % ('nobody', textBox))
        fd.write("This department has been given ID %s\n\n" % id)
        fd.write("Create AFS Cron directories:\t%s\n" % o['afscron'])
        fd.write("Create Web-Kickstart Directory:\t%s\n" % o['webks'])
        fd.write("Create Bcfg2 repository:\t%s\n" % o['bcfg2'])
        fd.write("Create Root password / admin list:\t%s\n\n" % o['admins'])
        fd.close()

        return self.index("You department %s has been requested." % textBox)
    createDept.exposed = True
    
