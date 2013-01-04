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

from flask import request, abort

# Flask application object
from rlmtools import app

logger = logging.getLogger('xmlrpc')

# Data Layer objects
_server = None
_admin = None
_rla = None

def _admin_init():
    global _server, _admin, _rla
    _server = WebServer()
    _admin = AdminServer()
    _rla = RLAttributes()

app.before_first_request(_admin_init)

@app.route("/admin/host", methods=["GET", "POST"])
def host(host_id=None):
    if request.method == "POST":
        # Other methods call us from their POST actions.
        host_id = request.form.get("host_id", host_id)
        importWebKS = request.form.get("importWebKS", None)
    else:
        host_id = request.args["host_id"]
        importWebKS = None

    if host_id is None:
        abort(400)

    dept_id = _admin.getHostDept(host_id)
    deptname = _admin.getDeptName(dept_id)
    isADMINby(dept_id)

    ikeys = _admin.getImportantKeys()
    wmessage = ''

    if importWebKS is not None:
        if not isWRITE(getAuthZ(dept_id)):
            return message("You need %s level write access to set "
                           "attributes." % deptname)
        try:
            if not _rla.importWebKickstart(host_id):
                wmessage="Error Importing Web-Kickstart Configuration"
        except Exception, e:
            wmessage = "Exception Importing Web-Kickstart: %s" % str(e)

    meta, attributes = _rla.hostAttrs(host_id)

    # Don't display encrypt secrets fully
    regex = re.compile(r"([-a-zA-Z0-9]+) ([a-zA-Z0-9]+)")
    for a in ['root', 'users']:
        if a in attributes and isinstance(attributes[a], str):
            match = regex.match(attributes[a])
            if match is None: continue
            attributes[a] = "%s ...%s [Secret Obscured]" % \
                    (match.group(1), match.group(2)[:6])

    if 'meta.imported' not in meta:
        if wmessage == "":
            wmessage = "The Web-Kickstart data for this host needs to be imported."
        importTime = "Never"
    else:
        importTime = time.strftime("%a, %d %b %Y %H:%M:%S %Z", \
                                   time.localtime(meta['meta.imported']))
    
    hostname = _admin.getHostName(host_id)
    subMenu = [ ('Host Status: %s' % short(hostname),
                 '%s/client?host_id=%s' % (url(), host_id)),
                ('Department Status: %s' % deptname,
                 '%s/dept?dept_id=%s' % (url(), dept_id)),
                ('Manage Department Attributes: %s' % deptname,
                 '%s/admin/dept?dept_id=%s' % (url(), dept_id)),
              ]

    return render('admin.host', 
                  dict(
                       host_id=host_id,
                       subMenu=subMenu,
                       title='Manage Host Attributes',
                       hostname=hostname,
                       deptname=deptname,
                       message=wmessage,
                       attributes=attributes,
                       meta=meta,
                       importTime=importTime,
                       webKickstartKeys=ikeys,
                 ))

@app.route("/admin/dept")
def admin_dept(dept_id=None):
    dept_id = request.args.get("dept_id", dept_id)

    if dept_id is None:
        abort(400)

    deptname = _admin.getDeptName(int(dept_id))
    isADMINby(dept_id)

    wmessage = ''

    meta, attributes = _rla.deptAttrs(dept_id)

    subMenu = [ ('Deptartment Status: %s' % deptname,
                 '%s/dept?dept_id=%s' % (url(), dept_id))
              ]

    return render('admin.dept', 
                  dict(
                       dept_id=dept_id,
                       deptname=deptname,
                       subMenu=subMenu,
                       title='Manage Department Attributes',
                       message=wmessage,
                       attributes=attributes,
                       meta=meta,
                 ))

@app.route("/admin/deleteHostAttr", methods=["POST"])
def deleteHostAttr(modifyKey=None, host_id=None):

    modifyKey = request.form.get("modifyKey", modifyKey)
    host_id = request.form.get("host_id", host_id)
    submit = request.form.get("submit", None)
    aptr = request.form.get("aptr", None)
    callback = request.form.get("callback", None)

    if submit is not None:
        if callback is None:
            return message(
                    "Interal application fault in deleteHostAttr()")
        host_id = int(callback)
    dept_id = _admin.getHostDept(int(host_id))
    deptname = _admin.getDeptName(dept_id)
    hostname = _admin.getHostName(int(host_id))
    aptr = _admin.getHostAttrPtr(int(host_id))

    isWRITEby(dept_id)

    if submit is not None:
        _rla.removeAttributeByKey(aptr, modifyKey)
        # To reuse the template we stuck this in 'callback'
        return host(host_id) # XXX: needs host_id

    subMenu = [ ('Manage Host Attributes: %s' % short(hostname),
                 '%s/admin/host?host_id=%s' % (url(), int(host_id)))
              ]

    meta, attributes = _rla.hostAttrs(host_id)
    if modifyKey not in attributes:
        return message("%s is not an attribute of %s" \
                       % (modifyKey, hostname))

    if modifyKey in ['root', 'users']:
        value = "[Secret Obscured]"
    else:
        value = attributes[modifyKey]
    return render('admin.delattr', 
                  dict(
                       subMenu=subMenu,
                       title=hostname,
                       key=modifyKey,
                       value=value,
                       message="",
                       callback=host_id,
                       call="deleteHostAttr",
                 ))

@app.route("/admin/deleteDeptAttr", methods=["POST"])
def deleteDeptAttr(modifyKey=None, dept_id=None):
    modifyKey = request.form.get("modifyKey", modifyKey)
    dept_id = request.form.get("dept_id", dept_id)
    submit = request.form.get("submit", None)
    aptr = request.form.get("aptr", None)
    callback = request.form.get("callback", None)

    if submit is not None:
        if callback is None:
            return message("Interal application fault in deleteDeptAttr()")
        dept_id = int(callback)
    deptname = _admin.getDeptName(int(dept_id))
    aptr = _admin.getDeptAttrPtr(int(dept_id))

    isWRITEby(dept_id)

    if submit is not None:
        _rla.removeAttributeByKey(aptr, modifyKey)
        # To reuse the template we stuck this in 'callback'
        return admin_dept(int(dept_id))

    subMenu = [ ('Manage Department Attributes: %s' % deptname,
                 '%s/admin/dept?dept_id=%s' % (url(), int(dept_id)))
              ]

    meta, attributes = _rla.deptAttrs(dept_id)
    if modifyKey not in attributes:
        return message("%s is not an attribute of %s" \
                            % (modifyKey, deptname))

    return render('admin.delattr', 
                  dict(
                       subMenu=subMenu,
                       title=deptname,
                       key=modifyKey,
                       value=attributes[modifyKey],
                       message="",
                       callback=dept_id,
                       call="deleteDeptAttr",
                 ))


@app.route("/admin/modifyHost", methods=["POST"])
def modifyHost():
    host_id = request.form["host_id"]
    modifyKey = request.form["modifyKey"]
    textbox = request.form.get("textbox", None)
    setAttribute = request.form.get("setAttribute", None)
    reset = request.form.get("reset", None)
    delete = request.form.get("delete", None)
    modify = request.form.get("modify", None)

    # XXX: check for altering meta. keys??
    dept_id = _admin.getHostDept(int(host_id))
    deptname = _admin.getDeptName(dept_id)

    if setAttribute == "Submit":
        isWRITEby(dept_id)
        aptr = _admin.getHostAttrPtr(host_id)
        _rla.setAttribute(aptr, modifyKey, textbox)
        # Set the value and redirect to the Host Admin Panel
        return host()  # Uses host_id

    meta, attributes = _rla.hostAttrs(host_id)
    attributes.update(meta)
    hostname = _admin.getHostName(host_id)

    if delete == "Delete":
        isWRITEby(dept_id)
        if 'meta.inhairited' in meta:
            if modifyKey in meta['meta.inhairited']:
                return message(
                        "The attribute %s is inhairited from a higher "
                        "order department.  It cannot be deleted from "
                        "this host: %s" % (modifyKey, hostname))

        return deleteHostAttr(modifyKey, host_id)

    isADMINby(dept_id)   # XXX: WRITE to edit, but ADMIN to read???

    replaceValue = None
    if reset == "Reset":
        if 'meta.parsed' in attributes and \
                modifyKey in attributes['meta.parsed']:
            replaceValue = \
                _rla.stringifyWebKS(attributes['meta.parsed'][modifyKey])
        else:
            m, a = _rla.inhairitedAttrs(host_id)
            a.update(m)
            if modifyKey in a:
                replaceValue = a[modifyKey]

    elif modifyKey in attributes:
        replaceValue = attributes[modifyKey]

    subMenu = [ ('Manage Host Attributes: %s' % short(hostname),
                 '%s/admin/host?host_id=%s' % (url(), host_id))
              ]

    return render('admin.modifyHost', 
                  dict(
                       subMenu=subMenu,
                       message='',
                       title=hostname,
                       host_id=host_id,
                       key=modifyKey,
                       replaceValue=replaceValue,
                 ))

@app.route("/admin/modifyDept", methods=["POST"])
def modifyDept():
    dept_id = request.form["dept_id"]
    modifyKey = request.form["modifyKey"]
    textbox = request.form.get("textbox", None)
    setAttribute = request.form.get("setAttribute", None)
    reset = request.form.get("reset", None)
    delete = request.form.get("delete", None)
    modify = request.form.get("modify", None)

    # XXX: check for altering meta. keys??
    deptname = _admin.getDeptName(int(dept_id))

    if setAttribute == "Submit":
        isWRITEby(dept_id)
        aptr = _admin.getDeptAttrPtr(dept_id)
        _rla.setAttribute(aptr, modifyKey, textbox)
        # Set the value and redirect to the Dept Admin Panel
        return admin_dept(dept_id)

    isADMINby(dept_id)  # XXX: WRITE to edit, ADMIN to read???

    meta, attributes = _rla.deptAttrs(dept_id)
    attributes.update(meta)
    deptname = _admin.getDeptName(dept_id)

    if delete == "Delete":
        if 'meta.inhairited' in meta:
            if modifyKey in meta['meta.inhairited']:
                return message(
                        "The attribute %s is inhairited from a higher "
                        "order department.  It cannot be deleted from "
                        "this department: %s" % (modifyKey, deptname))

        return deleteDeptAttr(modifyKey, int(dept_id))

    replaceValue = None
    if reset == "Reset":
        parent = _admin.getDeptParentID(int(dept_id))
        if parent is not None:
            m, a = _rla.deptAttrs(parent)
            a.update(m)
            if modifyKey in a:
                replaceValue = a[modifyKey]

    elif modifyKey in attributes:
        replaceValue = attributes[modifyKey]

    subMenu = [ ('Manage Department Attributes: %s' % deptname,
                 '%s/admin/dept?dept_id=%s' % (url(), dept_id))
              ]

    return render('admin.modifyDept', 
                  dict(
                       subMenu=subMenu,
                       message='',
                       title='Modify Attribute',
                       deptname=deptname,
                       dept_id=dept_id,
                       key=modifyKey,
                       replaceValue=replaceValue,
                 ))


