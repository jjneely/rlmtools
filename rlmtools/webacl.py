# webacl.py -- Manage RLMTools ACLs
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
import sys
import os
import os.path
import time
import cPickle as pickle
import logging
import re

from configDragon import config
from webcommon import *
from permServer import PermServer
from webServer import WebServer
from rlattributes import RLAttributes

from flask import request

# Flask Application object
from rlmtools import app

# Data layer objects
_admin = None
_server = None

logger = logging.getLogger('xmlrpc')

def _init_webperms():
    global _admin, _server
    _admin = PermServer()
    _server = WebServer()

app.before_first_request(_init_webperms)

@app.route("/perms/acl/")  #XXX: Fix the extra / in the templates?
def perms_acl_index():
    # Readable by any authenticated user
    if not isREAD(getAuthZ("root")):
        return message("You need root level read access to view "
                       "ACLs.")

    ptsgroups = _admin.getPTSGroups()

    subMenu = [
                ('Manage ACLs',
                 '%s/perms/acl/' % url()),
                ('Manage Web-Kickstart Directories',
                 '%s/perms/webkickstart' % url()),
              ]

    return render('acl.index', 
                  dict(ptsgroups=ptsgroups,
                       title="Manage ACLs",
                       subMenu=subMenu,
                 ))

@app.route("/perms/acl/newACL")
def newACL():
    cell = request.args["cell"]
    ptsGroup = request.args["ptsGroup"]
    aclName = request.args["aclName"]

    # You need admin access to mess with ACLs
    if not isADMIN(getAuthZ("root")):
        return message("You need root level admin access to modify "
                       "ACLs.")

    if "" in [cell.strip(), ptsGroup.strip(), aclName.strip()]:
        return message("All fields are required.  Not creating an ACL without complete data.")
    _admin.createACL(aclName, ptsGroup, cell)
    return perms_acl_index()

@app.route("/perms/acl/removeACL")
def removeACL():
    consent = request.args.get("consent", None)
    acl_id = request.args["acl_id"]

    if not isADMIN(getAuthZ("root")):
        return message("You need root level admin access to modify "
                       "ACLs.")

    if consent == "yes":
        _admin.removeACL(acl_id)
        return perms_acl_index()
    if consent == "no":
        return perms_acl_index()

    acl = _admin.getACL(int(acl_id))
    return render('acl.remove', 
                  dict(
                       title="Delete ACL",
                       aclname=acl['name'],
                       acl_id=acl_id,
                 ))

@app.route("/perms/acl/permissions")
def permissions():
    acl_id = request.args["acl_id"]

    if not isREAD(getAuthZ("root")):
        return message("You need root level read access to view "
                       "ACLs.")

    subMenu = [
                ('Manage ACLs',
                 '%s/perms/acl' % url()),
              ]

    acl = _admin.getACL(int(acl_id))
    depts = _admin.getPermsForACL(int(acl_id))
    users = _admin.getSysAdmins(acl_id)

    for i in depts:
        i['write'] = isWRITE(i['perms'])
        i['read']  = isREAD(i['perms'])
        i['admin'] = isADMIN(i['perms'])

    return render('acl.mod', 
                  dict(
                       deptlist=_admin.getAllDepts(),
                       users=users,
                       acl_id=acl_id,
                       title="ACL Permissions",
                       aclname=acl['name'],
                       depts=depts,
                       subMenu=subMenu,
                 ))

@app.route("/perms/acl/addPerm")
def addPerm():
    dept_id = request.args["dept_id"]
    acl_id  = request.args["acl_id"]
    read    = request.args.get("read", None)
    write   = request.args.get("write", None)
    admin   = request.args.get("admin", None)

    if not isADMIN(getAuthZ("root")):
        return message("You need root level admin access to modify "
                       "ACLs.")

    dept_id = int(dept_id)
    acl_id = int(acl_id)
    perms = _admin.getPermsForACL(acl_id)

    for i in perms:
        # See if we are modifying an existing permission
        if i['dept_id'] == dept_id:
            _admin.removePerm(i['aclg_id'])

    field = 0
    if read == "True":
        field = field | READ
    if write == "True":
        field = field | WRITE
    if admin == "True":
        field = field | ADMIN

    _admin.setPerm(acl_id, dept_id, field)

    return permissions()  # method requires acl_id in GET args

@app.route("/perms/acl/removePerm")
def removePerm():
    acl_id = request.args["acl_id"]
    aclg_id = request.args["aclg_id"]

    if not isADMIN(getAuthZ("root")):
        return message("You need root level admin access to modify "
                       "ACLs.")

    _admin.removePerm(int(aclg_id))
    return permissions() # again, requires acl_id

