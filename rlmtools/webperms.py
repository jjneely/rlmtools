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
import sys
import os
import os.path
import time
import cPickle as pickle
import logging
import re

import configDragon

from webcommon import *
from permServer import PermServer
from webServer import WebServer
from ldafs import *

from flask import request, g

# Flask application object
from rlmtools import app

logger = logging.getLogger('xmlrpc')

# Data layer objects
_server = None
_misc = None

def _init_perms():
    global _misc, _server
    _misc = PermServer()
    _server = WebServer()

app.before_first_request(_init_perms)

@app.route("/perms")
def perms_index():
    wmessage = request.args.get("message", "")

    # Readable by any authenticated user
    g.auth.require()

    subMenu = [
                ('Liquid Dragon ACLs',
                 '%s/perms/acl/' % url()),
                ('Realm Linux Departments',
                 '%s/perms/departments' % url()),
                ('Web-Kickstart Directories',
                 '%s/perms/webkickstart' % url()),
                ('RHN Groups',
                 '%s/perms/rhnGroups' % url()),
                ('Puppet Repositories',
                 '%s/perms/bcfg2' % url()),
              ]
    acls = _server.memberOfACL(g.auth.userid)

    return render('perms.index',
                  dict(message=wmessage,
                       subMenu=subMenu,
                       title="Permissions",
                       acls=acls,
                 ))

@app.route("/perms/rhnGroups")
def rhnGroups():
    wmessage = request.args.get("message", "")

    if not isAuthenticated():
        return message("You do not appear to be authenticated.")

    # XXX: Code not done, yet
    if not isADMIN(getAuthZ("root")):
        return message("There is no light in this dragon cave and...oops..."
                "you have just been eaten by a grue.")

    subMenu = [
                ('Liquid Dragon ACLs',
                 '%s/perms/acl/' % url()),
                ('Web-Kickstart Directories',
                 '%s/perms/webkickstart' % url()),
                ('RHN Groups',
                 '%s/perms/rhnGroups' % url()),
                ('Puppet Repositories',
                 '%s/perms/bcfg2' % url()),
              ]

    rhnMap = []
    for g in _misc.getRHNGroups():
        if g['dept_id'] is None:
            if isADMINby('root'):
               rhnMap.append(g)
        elif isADMINby(g['dept_id']):
            rhnMap.append(g)

    rhnMap.sort(cmp=lambda x,y:cmp(x['rhnname'], y['rhnname']))

    return render('perms.rhngroups',
                  dict(message=wmessage,
                       title='RHN Group to Department Map',
                       rhnMap=[ completeRHNGroup(i) for i in rhnMap ],
                       subMenu=subMenu,
                 ))

@app.route("/perms/rhnDetail", methods=["GET", "POST"])
def rhnDetail():
    if request.method == 'POST':
        rg_id = request.form["rg_id"]
        setDept = request.form.get("setDept", None)
        wmessage = request.form.get("message", "")
    else:
        rg_id = request.args["rg_id"]
        setDept = None
        wmessage = request.args.get("message", "")

    if not isAuthenticated():
        return message("You do not appear to be authenticated.")

    # XXX: Code not done, yet
    if not isADMIN(getAuthZ("root")):
        return message("There is no light in this dragon cave and...oops..."
                "you have just been eaten by a grue.")

    subMenu = [
                ('RHN Groups',
                 '%s/perms/rhnGroups' % url()),
              ]

    rg_id = int(rg_id)
    if setDept is not None:
        setDept = int(setDept)
        deptName = _misc.getDeptName(setDept)
        if deptName is None:
            wmessage = "Department ID %s does not exist." % setDept
        else:
            _misc.setRHNGroupDept(rg_id, setDept)
            wmessage = "Department association set to %s" % deptName

    rhnMap = _misc.getRHNGroup(rg_id)
    if rhnMap is None:
        return message("Unknown RHN Group ID %s" % rg_id)

    rhnMap = completeRHNGroup(rhnMap)
    depts = _misc.getAllDepts()
    rhnAdmins = getRHNGroupAdmins(rhnMap['rhnname'])

    ldadmins = []
    ldacls = []
    if rhnMap['dept_id'] is not None:
        # For RHN we want LD admin permissions
        acls = _misc.getDeptACLs(rhnMap['dept_id'])
        for acl in acls:
            p = ""
            if isREAD(acl['perms']):
                p = "read" 
            if isWRITE(acl['perms']):
                p = p and "%s|write"%p or "write"
            if isADMIN(acl['perms']):
                p = p and "%s|admin"%p or "admin"
                for i in _misc.getSysAdmins(acl['acl_id']):
                    if i not in ldadmins:
                        ldadmins.append(i)
            ldacls.append((acl['name'], p))

        tasks = diffAdmins(ldadmins, rhnAdmins)
    else:
        tasks = {}
        rhnAdmins.sort() # Sorted by side effect in if clause

    rhnMap['synced'] = len(tasks) == 0 and 'good' or 'bad'

    return render('perms.rhndetail',
                  dict(message=wmessage,
                       rhnMap=rhnMap,
                       subMenu=subMenu,
                       title="RHN Group Detail",
                       depts=depts,
                       rhnAdmins=rhnAdmins,
                       ldadmins=ldadmins,
                       ldacls=ldacls,
                       tasks=tasks,
                 ))

@app.route("/perms/bcfg2")
def bcfg2(wmessage=""):
    wmessage = request.args.get("message", wmessage)

    # Readable by any authenticated user
    if not isAuthenticated():
        return message("You do not appear to be authenticated.")

    # XXX: Code not done, yet
    if not isADMIN(getAuthZ("root")):
        return message("There is no light in this dragon cave and...oops..."
                "you have just been eaten by a grue.")

    bcfg2Map = _misc.getAllBcfg2Dir()

    subMenu = [
                ('Liquid Dragon ACLs',
                 '%s/perms/acl/' % url()),
                ('Web-Kickstart Directories',
                 '%s/perms/webkickstart' % url()),
                ('RHN Groups',
                 '%s/perms/rhnGroups' % url()),
                ('Puppet Repositories',
                 '%s/perms/bcfg2' % url()),
              ]

    try:
        bcfg2Map = [ completeWKSInfo(i) for i in bcfg2Map ]
    except Exception, e:
        return message("An error occured querying AFS: %s" % str(e))

    return render('perms.bcfg2',
                  dict(message=wmessage,
                       title="Bcfg2 Repositories",
                       subMenu=subMenu,
                       bcfg2Map=bcfg2Map,
                 ))

@app.route("/perms/webkickstart")
def webkickstart(wmessage=""):
    wmessage = request.args.get("message", wmessage)

    # Readable by any authenticated user
    if not isAuthenticated():
        return message("You do not appear to be authenticated.")

    # XXX: Code not done, yet
    if not isADMINby("root"):
        return message("There is no light in this dragon cave and...oops..."
                "you have just been eaten by a grue.")

    webksMap = _misc.getAllWKSDir()

    subMenu = [
                ('Liquid Dragon ACLs',
                 '%s/perms/acl/' % url()),
                ('Web-Kickstart Directories',
                 '%s/perms/webkickstart' % url()),
                ('RHN Groups',
                 '%s/perms/rhnGroups' % url()),
                ('Puppet Repositories',
                 '%s/perms/bcfg2' % url()),
              ]

    try:
        webksMap = [ completeWKSInfo(i) for i in webksMap ]
    except Exception, e:
        return message("An error occured querying AFS: %s" % str(e))

    return render('perms.webkickstart',
                  dict(message=wmessage,
                       title="Web-Kickstart",
                       subMenu=subMenu,
                       webksMap=webksMap,
                 ))

@app.route("/perms/changeWKSDept", methods=["GET", "POST"])
def changeWKSDept():
    if request.method == "POST":
        wkd_id = request.form["wkd_id"]
        setDept = request.form["setDept"]
        wmessage = request.form.get("message", "")
    else:
        wkd_id = request.args["wkd_id"]
        setDept = None
        wmessage = request.args.get("message", "")

    # Readable by any authenticated user
    if not isAuthenticated():
        return message("You do not appear to be authenticated.")

    # XXX: Code not done, yet
    if not isADMIN(getAuthZ("root")):
        return message("There is no light in this dragon cave and...oops..."
                "you have just been eaten by a grue.")

    subMenu = [
                ('Web-Kickstart Directories',
                 '%s/perms/webkickstart' % url()),
              ]

    wkd_id = int(wkd_id)
    webksMap = _misc.getWKSDir(wkd_id)
    depts = _misc.getAllDepts()
    if webksMap is None:
        wmessage = """A Web-Kickstart directory matching ID %s does
                      not exist.  Use the Back button and try your
                      query again.""" % wkd_id
        return message(wmessage)
    if setDept is not None:
        dept_id = int(setDept)
        dept = _misc.getDeptName(dept_id)
        if dept is None:
            wmessage = """Department ID %s was not found.  This 
                          Web-Kickstart directory was not modified.""" \
                                  % dept_id
        else:
            _misc.setWKSDept(wkd_id, dept_id)
            wmessage = """Set department association to %s for
            Web-Kickstart directory %s.""" % (dept, webksMap['path'])
            return webkickstart(wmessage)

    return render('perms.wksdept',
                  dict(message=wmessage,
                       title="Web-Kickstart",
                       subMenu=subMenu,
                       webksMap=completeWKSInfo(webksMap),
                       depts=depts,
                 ))

@app.route("/perms/changeBcfg2Dept", methods=["GET", "POST"])
def changeBcfg2Dept():
    if request.method == "POST":
        br_id = request.form["br_id"]
        setDept = request.form["setDept"]
        wmessage = request.form.get("message", "")
    else:
        br_id = request.args["br_id"]
        setDept = None
        wmessage = request.args.get("message", "")

    # Readable by any authenticated user
    if not isAuthenticated():
        return message("You do not appear to be authenticated.")

    # XXX: Code not done, yet
    if not isADMIN(getAuthZ("root")):
        return message("There is no light in this dragon cave and...oops..."
                "you have just been eaten by a grue.")

    subMenu = [
                ('Puppet Repositories',
                 '%s/perms/bcfg2' % url()),
              ]

    br_id = int(br_id)
    bcfg2Map = _misc.getBcfg2Dir(br_id)
    depts = _misc.getAllDepts()
    if bcfg2Map is None:
        wmessage = """A Bcfg2 repository matching ID %s does
                      not exist.  Use the Back button and try your
                      query again.""" % br_id
        return message(wmessage)
    if setDept is not None:
        dept_id = int(setDept)
        dept = _misc.getDeptName(dept_id)
        if dept is None:
            wmessage = """Department ID %s was not found.  This 
                          Bcfg2 repository was not modified.""" \
                                  % dept_id
        else:
            _misc.setBcfg2Dept(br_id, dept_id)
            wmessage = """Set department association to %s for
            Bcfg2 repository %s.""" % (dept, bcfg2Map['path'])
            return bcfg2(wmessage)

    return render('perms.bcfg2dept',
                  dict(message=wmessage,
                       title="Web-Kickstart",
                       subMenu=subMenu,
                       bcfg2Map=completeWKSInfo(bcfg2Map),
                       depts=depts,
                 ))

@app.route("/perms/modLDACLs", methods=["GET", "POST"])
def modLDACLs():
    if request.method == "POST":
        wkd_id = request.form["wkd_id"]
        setIt = request.form["setIt"]
        wmessage = request.form.get("message", "")
    else:
        wkd_id = request.args["wkd_id"]
        setIt = None
        wmessage = request.args.get("message", "")

    if not isAuthenticated():
        return message("You do not appear to be authenticated.")

    # XXX: Code not done, yet
    if not isADMIN(getAuthZ("root")):
        return message("There is no light in this dragon cave and...oops..."
                "you have just been eaten by a grue.")

    subMenu = [
                ('Web-Kickstart Directories',
                 '%s/perms/webkickstart' % url()),
              ]

    wkd_id = int(wkd_id)
    webksMap = _misc.getWKSDir(wkd_id)
    if webksMap is None:
        wmessage = """A Web-Kickstart directory matching ID %s does
                      not exist.  Use the Back button and try your
                      query again.""" % wkd_id
        return message(wmessage)

    webksMap = completeWKSInfo(webksMap)
    if webksMap['bad_dept']:
        wmessage = """The Web-Kickstart directory %s is not associated
                      with a department.  Setting a department must be
                      completed before setting ACLs.""" % webksMap['path']
        return webkickstart(wmessage)

    webksMap['todo'] = diffPermissions(webksMap['deptACLs'], 
                                       webksMap['pts'])

    if setIt is not None:
        # Do the work
        dept_id = webksMap['dept_id']
        for (acl, (action, value)) in webksMap['todo'].items():
            # XXX We assume the bp cell, that's where WKS lives
            if action == 1:
                _misc.createACL(acl, acl, "bp")
            acl_id = _misc.getACLbyName(acl, "bp")
            if action == 1 or action == 2:
                if acl_id is None:
                    log.warning("modLDACLs: bad ACL %s bp" % acl)
                    continue
                _misc.setPerm(acl_id, dept_id, rLDBitMap[value])
            if action == 3:
                acls = _misc.getPermsForACL(acl_id)
                rmacl = None
                for a in acls:
                    if dept_id == a['dept_id']: 
                        rmacl = a
                        break
                if rmacl is not None:
                    _misc.removePerm(rmacl['aclg_id'])
                else:
                    log.warning("modLDACLs: Couldn't find ACL to delete: %s ^s" % (acl, 'bp'))
        return webkickstart("""RLMTools ACLs for department %s have been set.""" % webksMap['dept'])

    return render('perms.modLDACLs',
                  dict(message=wmessage,
                       title="Web-Kickstart ACL Sync",
                       subMenu=subMenu,
                       webksMap=webksMap,
                 ))

@app.route("/perms/modAFS", methods=["GET", "POST"])
def modAFS():
    if request.method == "POST":
        wkd_id = request.form["wkd_id"]
        setIt = request.form["setIt"]
        wmessage = request.form.get("message", "")
    else:
        wkd_id = request.args["wkd_id"]
        setIt = None
        wmessage = request.args.get("message", "")

    if not isAuthenticated():
        return message("You do not appear to be authenticated.")

    # XXX: Code not done, yet
    if not isADMIN(getAuthZ("root")):
        return message("There is no light in this dragon cave and...oops..."
                "you have just been eaten by a grue.")

    subMenu = [
                ('Web-Kickstart Directories',
                 '%s/perms/webkickstart' % url()),
              ]

    wkd_id = int(wkd_id)
    webksMap = _misc.getWKSDir(wkd_id)
    if webksMap is None:
        wmessage = """A Web-Kickstart directory matching ID %s does
                      not exist.  Use the Back button and try your
                      query again.""" % wkd_id
        return message(wmessage)

    webksMap = completeWKSInfo(webksMap)
    if webksMap['bad_dept']:
        wmessage = """The Web-Kickstart directory %s is not associated
                      with a department.  Setting a department must be
                      completed before setting ACLs.""" % webksMap['path']
        return webkickstart(wmessage)

    webksMap['todo'] = diffPermissions(webksMap['deptACLs'], 
                                       webksMap['pts'],
                                       reverse=True)

    return render('perms.modAFS',
                  dict(message=wmessage,
                       title="Web-Kickstart AFS Sync",
                       subMenu=subMenu,
                       webksMap=webksMap,
                 ))

@app.route("/perms/modBcfg2AFS", methods=["GET", "POST"])   
def modBcfg2AFS():
    if request.method == "POST":
        br_id = request.form["br_id"]
        setIt = request.form["setIt"]
        wmessage = request.form.get("message", "")
    else:
        br_id = request.args["br_id"]
        setIt = None
        wmessage = request.args.get("message", "")

    if not isAuthenticated():
        return message("You do not appear to be authenticated.")

    # XXX: Code not done, yet
    if not isADMIN(getAuthZ("root")):
        return message("There is no light in this dragon cave and...oops..."
                "you have just been eaten by a grue.")

    subMenu = [
                ('Puppet Repositories',
                 '%s/perms/bcfg2' % url()),
              ]

    br_id = int(br_id)
    bcfg2Map = _misc.getBcfg2Dir(br_id)
    if bcfg2Map is None:
        wmessage = """A Bcfg2 repository matching ID %s does
                      not exist.  Use the Back button and try your
                      query again.""" % br_id
        return message(wmessage)

    bcfg2Map = completeWKSInfo(bcfg2Map)  # Yes, right method
    if bcfg2Map['bad_dept']:
        wmessage = """The Bcfg2 repository %s is not associated
                      with a department.  Setting a department must be
                      completed before setting ACLs.""" % bcfg2Map['path']
        return bcfg2(wmessage)

    bcfg2Map['todo'] = diffPermissions(bcfg2Map['deptACLs'], 
                                       bcfg2Map['pts'],
                                       reverse=True)

    return render('perms.modBcfg2AFS',
                  dict(message=wmessage,
                       title="Bcfg2 Repository AFS Sync",
                       subMenu=subMenu,
                       bcfg2Map=bcfg2Map,
                  ))

@app.route("/perms/departments")
def perms_departments():
    def children_of(root_id, depts):
        # Find my children!
        r = []
        for row in depts:
            if row['parent'] == root_id:
                r.append({"name":     row["name"],
                          "dept_id":  row["dept_id"],
                          "children": [],
                         })
        return r
    def recurse(root_id, depts):
        # Build the tree
        children = children_of(root_id, depts)
        if len(children) < 1: return []
        for i in children:
            i["children"] = recurse(i["dept_id"], depts)
        return children

    isREADby("root")

    wmessage = ""
    subMenu = [
                ('Liquid Dragon ACLs',
                 '%s/perms/acl/' % url()),
                ('Realm Linux Departments',
                 '%s/perms/departments' % url()),
                ('Web-Kickstart Directories',
                 '%s/perms/webkickstart' % url()),
                ('RHN Groups',
                 '%s/perms/rhnGroups' % url()),
                ('Puppet Repositories',
                 '%s/perms/bcfg2' % url()),
              ]

    root_id = _misc.getDeptIDNoCreate("root")
    depts = _misc.getAllDepts()

    tree = {"name":     "root",
            "dept_id":  root_id,
            "children": recurse(root_id, depts),
           }


    return render('perms.departments',
                  dict(message=wmessage,
                       title="Departments",
                       subMenu=subMenu,
                       dtree=tree,
                 ))

def diffAdmins(ldAdmins, rhnAdmins):
    """Return a dict of userid => code which is a list of tasks
       that should be done to make the list of rhnAdmins match
       our understanding in LD."""

    # Return values
    tasks = {}

    # Everyone must be sorted
    ldAdmins.sort()
    rhnAdmins.sort()

    # Copies that we can modify
    LD  = [ i for i in ldAdmins ]
    RHN = [ i for i in rhnAdmins ]
    protected = _misc.getRHNProtectedUsers()

    i = 0
    while len(LD) > i:
        if len(RHN) <= i or RHN[i] > LD[i]:
            # Add to RHN
            RHN.insert(i, LD[i])
            tasks[LD[i]] = 2
            i = i + 1
        elif RHN[i] < LD[i]:
            # remove from RHN
            if RHN[i] not in protected:
                tasks[RHN[i]] = 3
            del RHN[i]
        else:
            # equal
            i = i + 1
    while len(RHN) > len(LD):
        if RHN[i] not in protected:
            tasks[RHN[i]] = 3
        del RHN[i]

    return tasks

def diffPermissions(deptACLs, pts, reverse=False):
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
                if not _misc.isACL(AFS[i][0]):
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

def completeWKSInfo(webks):
    # Complete the dict for the perm pages that deal with web-kickstarts
    # webks should be the output from _misc.getWKSDir() or one entry
    # from _misc.getAllWKSDir()

    i = webks.copy()
    i['dept'] = _misc.getDeptName(i['dept_id'])
    i['bad_dept'] = i['dept'] is None

    # Build representation of AFS PTS groups
    i['pts'] = fsla(i['path'])

    # Include ACL information from LD department
    # Look and see if AFS PTS groups match the LD ACLs
    if i['bad_dept']:
        i['deptACLs'] = None
        i['perm_misalignment'] = True
    else:
        i['deptACLs'] = matchACLToAFS(
                _misc.getDeptACLs(i['dept_id']), True)
        misalignment = not equalACLs(i['deptACLs'], i['pts'])

        i['perm_misalignment'] = misalignment

    return i

def completeRHNGroup(rhnMap):
    i = rhnMap.copy()
    i['class'] = i['dept_id'] is None and 'bad' or 'good'
    i['dept'] = _misc.getDeptName(i['dept_id'])

    return i

def getRHNGroupAdmins(group):
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

