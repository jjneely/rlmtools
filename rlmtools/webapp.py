#!/usr/bin/python

# webapp.py - The CherryPy based web app
# Copyright 2006 - 2012 NC State University
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

import sys
import os.path
import datetime
import optparse

from flask import g, request, send_from_directory, redirect
from flaskext.genshi import Genshi, render_response

import rrdconstants

from webcommon import *
from constants import defaultConfFiles

import configDragon
import webks
import webadmin
import webperms
import webacl
import puppet
import webServer
import miscServer

# Flash Application object
from rlmtools import app

# Pointer to our DB layer object
_server = None
# Pointer to our configuration object
config = None
# Where our RRD graphs live
graphDir = None

def _init_webapp():
    global _server, config, graphDir
    config = configDragon.config
    _server = webServer.WebServer()
    graphDir = os.path.abspath(os.path.join(config.rrd_dir, 'graphs'))

#    AppHelpers.__init__(self, **kwargs)
#
#    # Sub directories in the webapp attach here
#    self.webKickstart = webks.Application()
#    self.webKickstart.exposed = True
#
#    self.admin = webadmin.Application()
#    self.admin.exposed = True
#
#    self.perms = webperms.Application()
#    self.perms.exposed = True
#
#    self.perms.acl = webacl.Application()
#    self.perms.acl.exposed = True

# Register our initilization method
app.before_first_request(_init_webapp)

# Handle the graphs/ URL path -- this is similar to the 
# Flask.send_static_file() function.
# XXX: In production our web server should do this for us
@app.route("/static/graphs/<path:filename>")
def graphs(filename):
    cache_timeout = app.get_send_file_max_age(filename)

    return send_from_directory(graphDir, filename,
                               cache_timeout=cache_timeout)

# AuthN/AuthZ Notes:
#   To force the user be to autheNticated just call
#
#     g.auth.require()
#   
#   That's the Auth class for the specific user/request.  To check
#   that the user is authoriZed for a specific department level
#   you can call any of:
#
#     isREADby(dept)
#     isWRITEby(dept)
#     isADMINby(dept)
#
#   These functions also call g.auth.require() and force the authentication
#   step.  These functions do not return if the user is not authN'd/authZ'd.
#   They call Flask's abort() method and return an HTTP error.

@app.route("/")
def index():
    g.auth.require()

    totals = _server.getTotalClients()
    active = _server.getActiveClients()
    departments = _server.getDepartments()
    graphs = []
    domainTable = [('master', 'Liquid Dragon Totals'),
                   ('problems', 'Liquid Dragon Problem Clients'),
                  ]

    for domain, t in domainTable:
        image = "%s-3d.png" % domain
        path = os.path.join(graphDir, image)
        if os.path.exists(path):
            img = os.path.join(url(), '/static/graphs/', image)
            href = '%s/showGraph?title=%s&domain=%s' % (url(), t, domain)
        else:
            img = ""
            href = ""

        graphs.append( {'url':img, 'domain':domain,
                        'href':href, 'title':t} )

    for dept in departments:
        dept['url'] = "%s/dept?dept_id=%s" % (url(),
                                              dept['dept_id'])
    return render('index', 
                     dict(departments=departments,
                          graphs=graphs,
                          active=active,
                          totals=totals))

@app.route("/versionIndex")
def versionIndex():
    isREADby("root")
    version = request.args["version"]

    # See also dept()
    services = ['updates', 'client'] # Services that affect client status
    clients = _server.getVersionPile(version)
    days7 = datetime.timedelta(7)
    today = datetime.datetime.today()
    pile = {}

    for client in clients:
        client['status'] = True
        client['url'] = "%s/client?host_id=%s" % (url(),
                                                  client['host_id'])

        if client['lastcheck'] < today - days7:
            client['status'] = False

        if client['lastcheck'] < client['installdate']:
            client['status'] = False

        for service in services:
            key = "%s_time" % service
            if not client.has_key(service) or client[key] < today - days7:
                client['status'] = False
                break
            if not client[service]:
                client['status'] = False

        if pile.has_key(client['deptname']):
            pile[client['deptname']].append(client)
        else:
            pile[client['deptname']] = [client]
    
    departments = pile.keys()
    departments.sort(lambda x,y: cmp(x.lower(), y.lower()))

    return render('versionindex', 
                  dict(departments=departments,
                       clients=pile,
                       count=len(clients),
                       version=version))

def _checkClient(client):
    # Figure out if the client is RED or GREEN by setting
    # cDict['status'] to False or True respectively
    services = ['updates', 'client'] # Services that affect client status

    if client['lastcheck'] is None:
        client['status'] = False
        return client

    client['status'] = True

    # Build datetime objects once per request
    if getattr(g, "today", None) is None:
        g.today = datetime.datetime.today()
    if getattr(g, "days7", None) is None:
        g.days7 = datetime.timedelta(7)

    if client['lastcheck'] < g.today - g.days7:
        client['status'] = False

    if client['lastcheck'] < client['installdate']:
        client['status'] = False

    for service in services:
        key = "%s_time" % service
        if not client.has_key(service) or \
           client[key] < g.today - g.days7:
            client['status'] = False
            break
        if not client[service]:
            client['status'] = False

    # Optional services that can turn a client red
    services = ['bcfg2', 'puppet']
    for service in services:
        if client.has_key(service) and not client[service]:
            client['status'] = False

    return client

@app.route("/dept")
def dept():
    isREADby("root")
    dept_id = request.args["dept_id"]

    subMenu = [ ('Manage Department Attributes',
                 '%s/admin/dept?dept_id=%s' % (url(), dept_id)),
              ]

    clients = _server.getClientList(int(dept_id))
    support = []
    nosupport = []

    for client in clients:
        client['url'] = "%s/client?host_id=%s" % (url(),
                                                  client['host_id'])

        # Calculate status
        _checkClient(client)

        if client['support']:
            support.append(client)
        else:
            nosupport.append(client)

    return render('dept', dict(support=support, 
                     nosupport=nosupport, 
                     department=_server.getDeptName(int(dept_id)),
                     subMenu=subMenu,
                     dept_id=dept_id,
                     title="Department Listing"))

@app.route("/client/<hostname>")
@app.route("/client")
def client(hostname=None, host_id=None, wmessage=""):
    isREADby("root")
    if hostname is not None:
        host_id = _server.getHostID(hostname)
    else:
        host_id = request.args.get("host_id", host_id)
    if host_id is None: abort(400)

    days7 = datetime.timedelta(7)
    today = datetime.datetime.today()
    detail = _server.getClientDetail(int(host_id))
    if "hostname" not in detail:
        # Bad host ID
        g.error = "host_id '%s' not found" % host_id
        abort(400)

    detail['puppet'] = puppet.findPuppetInventory(detail['uuid']) is not None
    detail['warnUpdate'] = False
    detail['lastcheck_good'] = detail['lastcheck'] != None and \
                               detail['lastcheck'] > today - days7 and \
                               detail['lastcheck'] > detail['installdate']
    status = {}
    if detail['recvdkey'] == 1:
        backlinks = [
                     ('Manage Host Attributes',
                      '%s/admin/host?host_id=%s' % (url(), host_id)),
                     ('Version: %s' % detail['version'],
                      '%s/versionIndex?version=%s' % (url(), 
                                                      detail['version'])),
                     ('Deptartment Status: %s' % detail['dept'],
                      "%s/dept?dept_id=%s" % (url(), detail['dept_id'])),
                     ]
    else:
        backlinks = [
                     ('Manage Host Attributes',
                      '%s/admin/host?host_id=%s' % (url(), host_id)),
                ]

    for row in detail['status']:
        row['url'] = "%s/status?status_id=%s" % (url(),
                                                 row['st_id'])
        if row['data'] == None:
            summary = "No data available..."
        else:
            summary = row['data'].strip().replace('\n', ' ')
            if len(summary) > 20:
                summary = summary[0:21] + "..."
        row['summary'] = summary

        if row['service'] == 'updates' and not status.has_key('updates'):
            if row['timestamp'] < today - days7:
                detail['warnUpdate'] = True

        if status.has_key(row['service']):
            row['class'] = "neutral"
        elif row['success']:
            status[row['service']] = True
            row['class'] = "good"
        else:
            status[row['service']] = False
            row['class'] = "bad"

    # Did we find an updates status at all?
    if not status.has_key('updates') and \
       detail['installdate'] < today - days7:
        detail['warnUpdate'] = True

    return render('client',
                  dict(client=detail, 
                       status=detail['status'],
                       subMenu=backlinks,
                       title="Host Status",
                       deptlist=_server.getDeptNames(),
                       message=wmessage,
                 ))

@app.route("/changeDept", methods=['POST'])
def changeDept():
    newdept = request.form["newdept"]
    try:
        host_id = int(request.form["host_id"])
    except:
        abort(400)
    olddept_id = _server.getHostDept(host_id)
    newdept_id = _server.getDeptIDNoCreate(newdept)
    if newdept_id is None:
        g.error = "Invalid department name '%'" % newdept
        abort(400)
    if olddept_id is None:
        g.error = "Invalid department ID '%s'" % olddept_id
        abort(400)

    isADMINby(olddept_id)
    isADMINby(newdept_id)

    if newdept_id == olddept_id:
        m = "New department is the same as the old department. " \
            "No change made."
        return client(host_id=host_id, wmessage=m)

    _server.setHostDept(host_id, newdept_id)
    m = "Department membership changed."
    return client(host_id=host_id, wmessage=m)

@app.route("/deleteClient", methods=['POST'])
def deleteClient():
    days7 = datetime.timedelta(7)
    today = datetime.datetime.today()
    try:
        host_id = int(request.form["host_id"])
        confirmed = request.form.get("confirmed", "False") == "True"
    except:
        abort(400)

    dept_id = _server.getHostDept(host_id)
    if dept_id is None:
        abort(400)

    isADMINby(dept_id)

    if confirmed:
        _misc = miscServer.MiscServer()
        _misc.deleteClient(host_id)
        return redirect("%s/dept?dept_id=%s" % (url(), dept_id))
    else:
        detail = _server.getClientDetail(host_id)
        detail['puppet'] = puppet.findPuppetInventory(detail['uuid']) \
                is not None
        detail['lastcheck_good'] = detail['lastcheck'] != None and \
                                   detail['lastcheck'] > today - days7 and \
                                   detail['lastcheck'] > detail['installdate']
        m = "Are you sure you want to permanently remove this host profile?"
        return render('deleteclient', dict(
                      client=detail,
                      message=m,
                      title="Delete Host Profile",
                     ))

@app.route("/client/inventory/<hostname>")
def client_inventory(hostname):
    host_id = _server.getHostID(hostname)
    if host_id is None: abort(400)

    dept_id = _server.getHostDept(host_id)
    isADMINby(dept_id)

    uuid = _server.getUUID(host_id)
    if uuid is None:
        # This host should exist if we are here, help?
        log.warning("Host ID %s does not have a UUID??" % host_id)
        g.error = "Host ID %s does not have a UUID, DB inconsistancy." \
                % host_id
        abort(500)
    inv = puppet.findPuppetInventory(uuid)

    subMenu = [ ("Host Status: %s" % short(hostname),
                 "%s/client/%s" % (url(), hostname) ),
              ]

    return render('client.inv', dict(
                                   title="Inventory",
                                   message="",
                                   hostname=hostname,
                                   data=inv,
                                   subMenu=subMenu,
                 ))

@app.route("/client/reports/<hostname>")
def client_reports(hostname):
    host_id = _server.getHostID(hostname)
    if host_id is None: abort(400)

    dept_id = _server.getHostDept(host_id)
    isADMINby(dept_id)

    uuid = _server.getUUID(host_id)
    if uuid is None:
        # This host should exist if we are here, help?
        log.warning("Host ID %s does not have a UUID??" % host_id)
        g.error = "Host ID %s does not have a UUID, DB inconsistancy." \
                % host_id
        abort(500)
    reports = puppet.findPuppetReports(uuid)
    if reports is None:
        display = None
    else:
        display = []
        for i in reports:
            ts = puppet.getTimestamp(i)
            if ts is not None:
                id = ts.strftime("%Y%m%d%H%M")
                local = puppet.localPuppetDate(ts)
                display.append({"id": id, "time": local})
        # Reverse order sort
        display.sort(cmp=lambda x,y: cmp(y['id'], x['id']))
    
    subMenu = [ ("Host Status: %s" % short(hostname),
                 "%s/client/%s" % (url(), hostname) ),
              ]

    return render('client.reports', dict(
                                         title="Puppet Run Reports",
                                         message="",
                                         hostname=hostname,
                                         data=display,
                                         subMenu=subMenu,
                 ))

@app.route("/client/reports/<hostname>/<preport>")
def client_report_show(hostname, preport):
    host_id = _server.getHostID(hostname)
    if host_id is None: abort(400)

    dept_id = _server.getHostDept(host_id)
    isADMINby(dept_id)

    uuid = _server.getUUID(host_id)
    if uuid is None:
        # This host should exist if we are here, help?
        log.warning("Host ID %s does not have a UUID??" % host_id)
        g.error = "Host ID %s does not have a UUID, DB inconsistancy." \
                % host_id
        abort(500)
    reports = puppet.findPuppetReports(uuid)
    filename = ""
    
    for i in reports:
        if preport in i:
            filename = i
    
    if filename == "":
        data = None
        timestamp = "unknown"
    else:
        data = puppet.readPuppetReport(filename)
        ts = puppet.getTimestamp(filename)
        timestamp = puppet.localPuppetDate(ts)


    subMenu = [ ("Host Status: %s" % short(hostname),
                 "%s/client/%s" % (url(), hostname) ),
                ("Puppet Reports",
                 "%s/client/reports/%s" % (url(), hostname) ),
              ]

    return render('client.reportshow', dict(
                                         title="Puppet Run Report",
                                         message="",
                                         hostname=hostname,
                                         data=data,
                                         timestamp=timestamp,
                                         subMenu=subMenu,
                 ))

@app.route("/status")
def status():
    isREADby("root")
    status_id = request.args["status_id"]

    status = _server.getStatusDetail(int(status_id))
    backlinks = [
            ('Deptartment Status: %s' % status['dept'],
             "%s/dept?dept_id=%s" % (url(), status['dept_id'])),
            ('Host Status: %s' % short(status['hostname']),
             "%s/client?host_id=%s" % (url(), status['host_id'])),
                ]

    if status['data'] == None or status['data'] == "":
        status['data'] = "No data available."
        status['data_class'] = "neutral"
    elif status['success']:
        status['data_class'] = "good"
    else:
        status['data_class'] = "bad"

    return render('status', dict(status=status, subMenu=backlinks))
    
@app.route("/notregistered") 
def notregistered():
    isREADby("root")

    clients = _server.getNotRegistered()
    support = []
    nosupport = []

    for client in clients:
        client['status'] = False # Because we aren't registered
        client['url'] = "%s/client?host_id=%s" % (url(),
                                                  client['host_id'])
        if client['support'] == 1:
            support.append(client)
        else:
            nosupport.append(client)

    return render('notregistered',
                  dict(support=support,
                       nosupport=nosupport,
                       department="Not Registered")
                 )

@app.route("/problems")
def problems():
    isREADby("root")

    clients = _server.getProblemList()
    data = {}

    for client in clients:
        host = {}
        host['hostname'] = client['hostname']
        host['url'] = "%s/client?host_id=%s" % (url(), client['host_id'])
        if data.has_key(client['deptname']):
            data[client['deptname']].append(host)
        else:
            data[client['deptname']] = [host]
    
    return render('problems', dict( clients=data ) )

@app.route("/noupdates")
def noupdates():
    isREADby("root")

    clients = _server.getNoUpdates()
    data = {}

    for client in clients:
        host = {}
        host['hostname'] = client['hostname']
        host['url'] = "%s/client?host_id=%s" % (url(), client['host_id'])
        if data.has_key(client['deptname']):
            data[client['deptname']].append(host)
        else:
            data[client['deptname']] = [host]
    
    departments = data.keys()
    departments.sort(lambda x,y: cmp(x.lower(), y.lower()))
    return render('noupdates',
                  dict( clients=data,
                        departments=departments )
                 )

@app.route("/versionList")
def versionList():
    isREADby("root")

    versions = _server.getVersionList()
    graphs = []
    image = "versions-3d.png"
    path = os.path.join(config.rrd_dir, 'graphs', image)

    if os.path.exists(path):
        graphs.append( dict(
                 domain='versions',
                 url="%s/static/graphs/%s" % (url(), image),
                 href="%s/showGraph?title=%s&domain=%s" % \
                         (url(), "Version Statistics", "versions")))
    else:
        graphs.append( dict(
                 domain='versions',
                 url="",
                 href=""))

    return render('versionlist',
                  dict( versions=versions,
                        graphs=graphs ))

@app.route("/showGraph")
def showGraph():
    isREADby("root")
    title = request.args["title"]
    domain = request.args["domain"]

    graphs = []
    for zone in rrdconstants.timeZones:
        d = {}
        if zone.endswith('d'):
            d['summary'] = "%s day view." % zone[:-1]
        elif zone.endswith('w'):
            d['summary'] = "%s week view." % zone[:-1]
        else:
            d['summary'] = zone

        image = "%s-%s.png" % (domain, zone)
        path = os.path.join(config.rrd_dir, 'graphs', image)
        if not os.path.exists(path):
            u = ""
        else:
            u = "%s/static/graphs/%s" % (url(), image)

        d['url'] = u
        graphs.append(d)

    return render('graphs',
                  dict( title=title, graphs=graphs )
                 )

@app.route("/usage")
def usage():
    isREADby("root")

    depts = _server.getDeptNames()
    graphs = []

    image = "usage-1w.png"
    path = os.path.join(config.rrd_dir, 'graphs', image)
    if os.path.exists(path):
        d = dict(summary="Total Usage Statistics:",
                 url="%s/static/graphs/%s" % (url(), image),
                 href="%s/showGraph?title=%s&domain=%s" % \
                         (url(), "Total Usage Statistics", "usage"))
    else:
        d = dict(summary="Total Usage Statistics", url="", href="")

    graphs.append(d)
    for dept in depts:
        d = {}
        summary = "%s:" % dept
        dom = "usage@%s" % dept
        image = "%s-1w.png" % dom
        path = os.path.join(config.rrd_dir, 'graphs', image)
        if not os.path.exists(path):
            u = ""
            href = ""
        else:
            u = "%s/static/graphs/%s" % (url(), image)
            href = "%s/showGraph?title=%s&domain=%s" % \
                    (url(), summary, dom)

        graphs.append( dict(url=u, href=href, summary=summary) )

    return render('usage', dict(graphs=graphs))

@app.route("/search", methods=['GET', 'POST'])
def search():
    isREADby("root")

    searchBox = request.form.get("searchBox", None)
    dest = request.form.get("dest", None)

    if searchBox is None:
        # Just show an empty search and allow user to start typing
        clients = []
    else:
        clients = _server.getSearchResult(searchBox)

    if type(clients) == type(-1) and clients == -1:
        error = "Search returns more than 100 clients.  Liquid Dragon has "\
                "set these on fire instead.  Perhaps you should ask for a "\
                "smaller subset of clients."
    elif type(clients) == type(-1) and clients == -2:
        error = "Smoke appears and the tempurature rises.  You have "\
                "angered Liguid Dragon with an empty search string."
    else:
        error = ""

    if error == "":
        if dest == "admin":
            target = "admin/host?host_id=%s"
        else:
            target = "client?host_id=%s"

        for client in clients:
            client['url'] = target % client['host_id']

            # Calculate status
            _checkClient(client)

    return render('search', dict(
                                 clients=clients,
                                 error=error,
                                 initial=(searchBox is None)
                 ))

@app.route("/getWrapped")
def getWrapped():
    refer = request.referrer
    if refer is None:
        refer = url()

    response = redirect("https://webauth.ncsu.edu/wrap-bin/was16.cgi")
    
    # This is the "correct" way to set a cookie, but the value ends up
    # quoted in the outgoing headers and the WRAP server doesn't deal
    # with those quotes. 
    #
    # response.set_cookie("WRAP_REFERER", value=refer, domain=".ncsu.edu")
    #
    # So we set this the old fashioned way instead
    cookie = "WRAP_REFERER=%s; path=/; domain=%s" % (refer, ".ncsu.edu")
    response.headers.add("Set-Cookie", cookie)

    return response


#def wsgi(req):
#    global config
#    if req.get_options().has_key('rlmtools.configfile'):
#        configfile = req.get_options()['rlmtools.configfile']
#    else:
#        configfile = defaultConfFiles

