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

import xmlrpclib
import optparse
import cherrypy
import sys
import os
import os.path
import time
import cPickle as pickle
import logging
import re

import configDragon

from webcommon import *
from adminServer import AdminServer
from webServer import WebServer
from permServer import PermServer
from ldafs import *

logger = logging.getLogger('xmlrpc')

class Application(AppHelpers):

    def __init__(self):
        AppHelpers.__init__(self)
        self._misc = PermServer()

    def index(self, message=""):
        # Readable by any authenticated user
        if not self.isAuthenticated():
            return self.message("You do not appear to be authenticated.")

        subMenu = [
                    ('Manage ACLs',
                     '%s/perms/acl/' % url()),
                    ('Manage Web-Kickstart Directories',
                     '%s/perms/webkickstart' % url()),
                    ('Manage RHN Groups',
                     '%s/perms/rhnGroups' % url()),
                  ]
        depts = WebServer().getDepartments()
        acls = self._server.memberOfACL(Auth().userid)

        return self.render('perms.index',
                           dict(message=message,
                                depts=depts,
                                subMenu=subMenu,
                                title="Permissions",
                                acls=acls,
                               ))
    index.exposed = True

    def rhnGroups(self, message=""):
        if not self.isAuthenticated():
            return self.message("You do not appear to be authenticated.")

        subMenu = [
                    ('Manage ACLs',
                     '%s/perms/acl/' % url()),
                    ('Manage Web-Kickstart Directories',
                     '%s/perms/webkickstart' % url()),
                    ('Manage RHN Groups',
                     '%s/perms/rhnGroups' % url()),
                  ]

        rhnMap = self._misc.getRHNGroups()

        return self.render('perms.rhngroups',
                dict(message=message,
                     title='RHN Group to Department Map',
                     rhnMap=[ self.completeRHNGroup(i) for i in rhnMap ],
                     subMenu=subMenu,
                    ))
    rhnGroups.exposed = True

    def rhnDetail(self, rg_id, setDept=None, message=""):
        if not self.isAuthenticated():
            return self.message("You do not appear to be authenticated.")

        subMenu = [
                    ('Manage RHN Groups',
                     '%s/perms/rhnGroups' % url()),
                  ]

        rg_id = int(rg_id)
        if setDept is not None:
            setDept = int(setDept)
            deptName = self._misc.getDeptName(setDept)
            if deptName is None:
                message = "Department ID %s does not exist." % setDept
            else:
                self._misc.setRHNGroupDept(rg_id, setDept)
                message = "Department association set to %s" % deptName

        rhnMap = self._misc.getRHNGroup(rg_id)
        if rhnMap is None:
            return self.message("Unknown RHN Group ID %s" % rg_id)

        rhnMap = self.completeRHNGroup(rhnMap)
        depts = self._misc.getAllDepts()
        rhnAdmins = self.getRHNGroupAdmins(rhnMap['rhnname'])

        ldusers = []
        if rhnMap['dept_id'] is not None:
            # For RHN we want LD admin permissions
            acls = self._misc.getDeptACLs(rhnMap['dept_id'])
            for acl in acls:
                if self.isADMIN(acl['perms']):
                    ldusers.extend(self._misc.getSysAdmins(acl['acl_id']))

        return self.render('perms.rhndetail',
                dict(message=message,
                     rhnMap=rhnMap,
                     subMenu=subMenu,
                     title="RHN Group Detail",
                     depts=depts,
                     rhnAdmins=rhnAdmins,
                     ldadmins=ldusers,
                    ))
    rhnDetail.exposed = True

    def webkickstart(self, message=""):
        # Readable by any authenticated user
        if not self.isAuthenticated():
            return self.message("You do not appear to be authenticated.")

        webksMap = self._misc.getAllWKSDir()

        subMenu = [
                    ('Manage ACLs',
                     '%s/perms/acl/' % url()),
                    ('Manage Web-Kickstart Directories',
                     '%s/perms/webkickstart' % url()),
                    ('Manage RHN Groups',
                     '%s/perms/rhnGroups' % url()),
                  ]

        return self.render('perms.webkickstart',
                           dict(message=message,
                                title="Web-Kickstart",
                                subMenu=subMenu,
                                webksMap=[self.completeWKSInfo(i) \
                                          for i in webksMap ],
                               ))
    webkickstart.exposed = True

    def changeWKSDept(self, wkd_id, setDept=None, message=""):
        # Readable by any authenticated user
        if not self.isAuthenticated():
            return self.message("You do not appear to be authenticated.")

        subMenu = [
                    ('Manage Web-Kickstart Directories',
                     '%s/perms/webkickstart' % url()),
                  ]

        wkd_id = int(wkd_id)
        webksMap = self._misc.getWKSDir(wkd_id)
        depts = self._misc.getAllDepts()
        if webksMap is None:
            message = """A Web-Kickstart directory matching ID %s does
                         not exist.  Use the Back button and try your
                         query again.""" % wkd_id
            return self.message(message)
        if setDept is not None:
            dept_id = int(setDept)
            dept = self._misc.getDeptName(dept_id)
            if dept is None:
                message = """Department ID %s was not found.  This 
                             Web-Kickstart directory was not modified.""" \
                                     % dept_id
            else:
                self._misc.setWKSDept(wkd_id, dept_id)
                message = """Set department association to %s for
                Web-Kickstart directory %s.""" % (dept, webksMap['path'])
                return self.webkickstart(message)

        return self.render('perms.wksdept',
                           dict(message=message,
                                title="Web-Kickstart",
                                subMenu=subMenu,
                                webksMap=self.completeWKSInfo(webksMap),
                                depts=depts,
                               ))
    changeWKSDept.exposed = True

    def modLDACLs(self, wkd_id, setIt=None, message=""):
        if not self.isAuthenticated():
            return self.message("You do not appear to be authenticated.")

        subMenu = [
                    ('Manage Web-Kickstart Directories',
                     '%s/perms/webkickstart' % url()),
                  ]

        wkd_id = int(wkd_id)
        webksMap = self._misc.getWKSDir(wkd_id)
        if webksMap is None:
            message = """A Web-Kickstart directory matching ID %s does
                         not exist.  Use the Back button and try your
                         query again.""" % wkd_id
            return self.message(message)

        webksMap = self.completeWKSInfo(webksMap)
        if webksMap['bad_dept']:
            message = """The Web-Kickstart directory %s is not associated
                         with a department.  Setting a department must be
                         completed before setting ACLs.""" % webksMap['path']
            return self.webkickstart(message)

        webksMap['todo'] = self.diffPermissions(webksMap['deptACLs'], 
                                                webksMap['pts'])

        if setIt is not None:
            # Do the work
            dept_id = webksMap['dept_id']
            for (acl, (action, value)) in webksMap['todo'].items():
                # XXX We assume the bp cell, that's where WKS lives
                if action == 1:
                    self._misc.createACL(acl, acl, "bp")
                acl_id = self._misc.getACLbyName(acl, "bp")
                if action == 1 or action == 2:
                    if acl_id is None:
                        log.warning("modLDACLs: bad ACL %s bp" % acl)
                        continue
                    self._misc.setPerm(acl_id, dept_id, rLDBitMap[value])
                if action == 3:
                    acls = self._misc.getPermsForACL(acl_id)
                    rmacl = None
                    for a in acls:
                        if dept_id == a['dept_id']: 
                            rmacl = a
                            break
                    if rmacl is not None:
                        self._misc.removePerm(rmacl['aclg_id'])
                    else:
                        log.warning("modLDACLs: Couldn't find ACL to delete: %s ^s" % (acl, 'bp'))
            return self.webkickstart(message="""RLMTools ACLs for department %s have been set.""" % webksMap['dept'])

        return self.render('perms.modLDACLs',
                           dict(message=message,
                                title="Web-Kickstart ACL Sync",
                                subMenu=subMenu,
                                webksMap=webksMap,
                               ))
    modLDACLs.exposed = True

    def modAFS(self, wkd_id, setIt=None, message=""):
        if not self.isAuthenticated():
            return self.message("You do not appear to be authenticated.")

        subMenu = [
                    ('Manage Web-Kickstart Directories',
                     '%s/perms/webkickstart' % url()),
                  ]

        wkd_id = int(wkd_id)
        webksMap = self._misc.getWKSDir(wkd_id)
        if webksMap is None:
            message = """A Web-Kickstart directory matching ID %s does
                         not exist.  Use the Back button and try your
                         query again.""" % wkd_id
            return self.message(message)

        webksMap = self.completeWKSInfo(webksMap)
        if webksMap['bad_dept']:
            message = """The Web-Kickstart directory %s is not associated
                         with a department.  Setting a department must be
                         completed before setting ACLs.""" % webksMap['path']
            return self.webkickstart(message)

        webksMap['todo'] = self.diffPermissions(webksMap['deptACLs'], 
                                                webksMap['pts'],
                                                reverse=True)

        if False:
            # Do the work
            dept_id = webksMap['dept_id']
            for (acl, (action, value)) in webksMap['todo'].items():
                # XXX We assume the bp cell, that's where WKS lives
                if action == 1:
                    self._misc.createACL(acl, acl, "bp")
                acl_id = self._misc.getACLbyName(acl, "bp")
                if action == 1 or action == 2:
                    if acl_id is None:
                        log.warning("modLDACLs: bad ACL %s bp" % acl)
                        continue
                    self._misc.setPerm(acl_id, dept_id, rLDBitMap[value])
                if action == 3:
                    acls = self._misc.getPermsForACL(acl_id)
                    rmacl = None
                    for a in acls:
                        if dept_id == a['dept_id']: 
                            rmacl = a
                            break
                    if rmacl is not None:
                        self._misc.removePerm(rmacl['aclg_id'])
                    else:
                        log.warning("modLDACLs: Couldn't find ACL to delete: %s ^s" % (acl, 'bp'))
            return self.webkickstart(message="""RLMTools ACLs for department %s have been set.""" % webksMap['dept'])

        return self.render('perms.modAFS',
                           dict(message=message,
                                title="Web-Kickstart AFS Sync",
                                subMenu=subMenu,
                                webksMap=webksMap,
                               ))
    modAFS.exposed = True
    
    def diffPermissions(self, deptACLs, pts, reverse=False):
        """Return a dict of ACL -> (code, data) that indicates what
           actions need to be performed to change the deptACLs to 
           match AFS.  If reverse is True the dict will indicate what
           needs to be done to AFS to match LD."""
        # There are some caveats here that make this algorythm 
        # assume WKD directories in the BP cell

        # Return dict
        tasks = {}

        # Translated deptACLs into the same format as the PTS tuples
        LD = [ LDtoAFS(i) for i in deptACLs ]
        AFS = [ i for i in pts ] # weak copy

        # Sort everybody
        LD.sort(cmp=lambda x,y: cmp(x[0], y[0]))
        AFS.sort(cmp=lambda x,y: cmp(x[0], y[0]))

        print "LD ACLs: " + str(LD)
        print "AFS PTS: " + str(AFS)
        i = 0
        while len(AFS) > i:
            if len(LD) > i:
                print "Comparing: %s, %s" % (str(LD[i]), str(AFS[i]))
            else:
                print "Comparing: %s, %s" % ("(EMPTY)", str(AFS[i]))
            if len(LD) <= i or LD[i][0] > AFS[i][0]:
                # Add ACL to LD or remove from AFS
                if len(LD) > i:
                    print "X: %s > %s" % (LD[i][0], AFS[i][0])
                if reverse:
                    tasks[AFS[i][0]] = (3, None)
                    del AFS[i]
                else:
                    if not self._misc.isACL(AFS[i][0]):
                        tasks[AFS[i][0]] = (1, AFSpermLD(AFS[i][1]))
                    else:
                        tasks[AFS[i][0]] = (2, AFSpermLD(AFS[i][1]))
                    LD.insert(i, AFS[i])
                    i = i + 1
            elif LD[i][0] < AFS[i][0]:
                # del from LD or add to AFS
                print "X: %s < %s" % (LD[i][0], AFS[i][0])
                if reverse:
                    tasks[LD[i][0]] = (2, LDpermAFS(LD[i][1]))
                    AFS.insert(i, LD[i])
                    i = i + 1
                else:
                    tasks[LD[i][0]] = (3, None)
                    del LD[i]
            else: # equal
                # check permission
                print "X: %s == %s" % (LD[i][0], AFS[i][0])
                print "A: %s =? %s" % (LD[i][1], AFS[i][1])
                if not equalPerm(LD[i][1], AFS[i][1]):
                    if reverse:
                        print "X:   Setting %s to %s" % (AFS[i][0], LDpermAFS(LD[i][1]))
                        tasks[AFS[i][0]] = (2, LDpermAFS(LD[i][1]))
                    else:
                        print "X:   Setting %s to %s" % (LD[i][0], AFS[i][1])
                        tasks[LD[i][0]] = (2, AFS[i][1])
                i = i + 1

        while len(LD) > len(AFS):
            if reverse:
                print "X: adding %s %s" %(LD[i][0], LDpermAFS(LD[i][1]))
                tasks[LD[i][0]] = (2, LDpermAFS(LD[i][1]))  
                AFS.insert(i, LD[i])
                i = i + 1
            else:
                tasks[LD[i][0]] = (3, None)
                del LD[i]

        # Extra special rules
        if 'installer:common' in tasks and \
                tasks['installer:common'][0] in [1, 2]:
            del tasks['installer:common']
        if 'linux' in tasks and tasks['linux'][0] == 3:
            del tasks['linux']
        if 'linux' in tasks and tasks['linux'][0] == 2:
            tasks['linux'] = (2, 'admin')

        return tasks

    def completeWKSInfo(self, webks):
        # Complete the dict for the perm pages that deal with web-kickstarts
        # webks should be the output from _misc.getWKSDir() or one entry
        # from _misc.getAllWKSDir()

        i = webks.copy()
        i['dept'] = self._misc.getDeptName(i['dept_id'])
        i['bad_dept'] = i['dept'] is None

        # Build representation of AFS PTS groups
        i['pts'] = fsla(i['path'])

        # Include ACL information from LD department
        # Look and see if AFS PTS groups match the LD ACLs
        if i['bad_dept']:
            i['deptACLs'] = None
            i['perm_misalignment'] = True
            i['show_actions'] = False
        else:
            i['deptACLs'] = matchACLToAFS(
                    self._misc.getDeptACLs(i['dept_id']), True)
            misalignment = not equalACLs(i['deptACLs'], i['pts'])

            i['perm_misalignment'] = misalignment

        return i

    def completeRHNGroup(self, rhnMap):
        i = rhnMap.copy()
        i['class'] = i['dept_id'] is None and 'bad' or 'good'
        i['dept'] = self._misc.getDeptName(i['dept_id'])

        return i

    def getRHNGroupAdmins(self, group):
        # group is a string that matches the RHN group name
        config = configDragon.config
        server = xmlrpclib.ServerProxy(config.rhnurl)

        try:
            session = server.auth.login(config.rhnuser, config.rhnpasswd, 30)
            ret = server.systemgroup.listAdministrators(session, group)
        except Exception, e:
            print "RHN Exception: %s" % str(e)
            ret = None

        if ret is None: return None
        return [ i['login'] for i in ret if i['enabled'] ]

