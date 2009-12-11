#!/usr/bin/python

# webapp.py - The CherryPy based web app
# Copyright 2006 - 2007 NC State University
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

import cherrypy
import rrdconstants

from webcommon import *
from constants import defaultConfFiles

import configDragon
import webks
import webadmin

config = None

class Application(AppHelpers):

    def __init__(self, **kwargs):
        AppHelpers.__init__(self, **kwargs)

        # Sub directories in the webapp attach here
        self.webKickstart = webks.Application()
        self.webKickstart.exposed = True

        self.admin = webadmin.Application()
        self.admin.exposed = True

    def index(self):
        if not self.isAuthenticated():
            return self.message("You do not appear to be authenticated.")

        totals = self._server.getTotalClients()
        active = self._server.getActiveClients()
        departments = self._server.getDepartments()
        graphs = []
        domainTable = [('master', 'Liquid Dragon Totals'),
                       ('problems', 'Liquid Dragon Problem Clients'),
                      ]

        for domain, t in domainTable:
            image = "%s-3d.png" % domain
            path = os.path.join(config.rrd_dir, 'graphs', image)
            if os.path.exists(path):
                img = os.path.join('/rlmtools/static/graphs/', image)
                href = '/rlmtools/showGraph?title=%s&domain=%s' % (t, domain)
            else:
                img = ""
                href = ""

            graphs.append( {'url':img, 'domain':domain,
                            'href':href, 'title':t} )

        for dept in departments:
            dept['url'] = "%s/dept?dept_id=%s" % (url(),
                                                  dept['dept_id'])
        return self.render('index', 
                         dict(departments=departments,
                              graphs=graphs,
                              active=active,
                              totals=totals))
    index.exposed = True

    def versionIndex(self, version):
        # See also dept()
        if not self.isREAD(self.getAuthZ("root")):
            return self.message("You need root level read access to view "
                                "the version index.")
        services = ['updates', 'client'] # Services that affect client status
        clients = self._server.getVersionPile(version)
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

        return self.render('versionindex', 
                    dict(departments=departments,
                         clients=pile,
                         count=len(clients),
                         version=version))
    versionIndex.exposed = True

    def _checkClient(self, client):
        # Figure out if the client is RED or GREEN by setting
        # cDict['status'] to False or True respectively
        services = ['updates', 'client'] # Services that affect client status

        if client['lastcheck'] is None:
            client['status'] = False
            return client

        client['status'] = True

        if client['lastcheck'] < self.today - self.days7:
            client['status'] = False

        if client['lastcheck'] < client['installdate']:
            client['status'] = False

        for service in services:
            key = "%s_time" % service
            if not client.has_key(service) or \
               client[key] < self.today - self.days7:
                client['status'] = False
                break
            if not client[service]:
                client['status'] = False

        return client

    def dept(self, dept_id):
        if not self.isREAD(self.getAuthZ("root")):
            return self.message("You need root level read access to view "
                                "the department index.")

        # set some globals to speed helper fucntions
        self.days7 = datetime.timedelta(7)
        self.today = datetime.datetime.today()

        subMenu = [ ('Department Admin Panel',
                     '%s/admin/dept?dept_id=%s' % (url(), dept_id)),
                  ]

        clients = self._server.getClientList(int(dept_id))
        support = []
        nosupport = []

        for client in clients:
            client['url'] = "%s/client?host_id=%s" % (url(),
                                                      client['host_id'])
 
            # Calculate status
            self._checkClient(client)

            if client['support']:
                support.append(client)
            else:
                nosupport.append(client)

        return self.render('dept', dict(support=support, 
                         nosupport=nosupport, 
                         department=self._server.getDeptName(int(dept_id)),
                         subMenu=subMenu,
                         title="Department Listing"))
    dept.exposed = True

    def client(self, host_id):
        if not self.isREAD(self.getAuthZ("root")):
            return self.message("You need root level read access to view "
                                "the client index.")

        days7 = datetime.timedelta(7)
        today = datetime.datetime.today()
        detail = self._server.getClientDetail(int(host_id))
        detail['warnUpdate'] = False
        detail['lastcheck_good'] = detail['lastcheck'] != None and \
                                   detail['lastcheck'] > today - days7 and \
                                   detail['lastcheck'] > detail['installdate']
        status = {}
        if detail['recvdkey'] == 1:
            backlinks = [
                         ('Host Admin Panel',
                          '%s/admin/host?host_id=%s' % (url(), host_id)),
                         ('Version: %s' % detail['version'],
                          '%s/versionIndex?version=%s' % (url(), 
                                                          detail['version'])),
                         ('Dept: %s' % detail['dept'],
                          "%s/dept?dept_id=%s" % (url(), detail['dept_id'])),
                         ]
        else:
            backlinks = [
                         ('Host Admin Panel',
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

        return self.render('client',
                         dict(client=detail, status=detail['status'],
                              subMenu=backlinks,
                              title="Host Detail"))
    client.exposed = True

    def status(self, status_id):
        if not self.isREAD(self.getAuthZ("root")):
            return self.message("You need root level read access to view "
                                "the a client status message.")
        status = self._server.getStatusDetail(int(status_id))
        backlinks = [
                     ('Dept: %s' % status['dept'],
                      "%s/dept?dept_id=%s" % (url(), status['dept_id'])),
                     ('Host: %s' % short(status['hostname']),
                      "%s/client?host_id=%s" % (url(), status['host_id'])),
                    ]

        if status['data'] == None or status['data'] == "":
            status['data'] = "No data available."
            status['data_class'] = "neutral"
        elif status['success']:
            status['data_class'] = "good"
        else:
            status['data_class'] = "bad"

        return self.render('status', 
                         dict(status=status, subMenu=backlinks))
    status.exposed = True

    def notregistered(self):
        if not self.isREAD(self.getAuthZ("root")):
            return self.message("You need root level read access to view "
                                "the non-registered clients.")
        clients = self._server.getNotRegistered()
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

        return self.render('notregistered',
                         dict(support=support,
                              nosupport=nosupport,
                              department="Not Registered")
                        )
    notregistered.exposed = True

    def problems(self):
        if not self.isREAD(self.getAuthZ("root")):
            return self.message("You need root level read access to view "
                                "the problem children.")
        clients = self._server.getProblemList()
        data = {}

        for client in clients:
            host = {}
            host['hostname'] = client['hostname']
            host['url'] = "%s/client?host_id=%s" % (url(), client['host_id'])
            if data.has_key(client['deptname']):
                data[client['deptname']].append(host)
            else:
                data[client['deptname']] = [host]
        
        return self.render('problems',
                         dict( clients=data )
                        )
    problems.exposed = True

    def noupdates(self):
        if not self.isREAD(self.getAuthZ("root")):
            return self.message("You need root level read access to view "
                                "the clients not updating.")
        clients = self._server.getNoUpdates()
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
        return self.render('noupdates',
                         dict( clients=data,
                               departments=departments )
                        )
    noupdates.exposed = True

    def versionList(self):
        if not self.isREAD(self.getAuthZ("root")):
            return self.message("You need root level read access to view "
                                "the version list.")
        versions = self._server.getVersionList()
        graphs = []
        image = "versions-3d.png"
        path = os.path.join(config.rrd_dir, 'graphs', image)

        if os.path.exists(path):
            graphs.append( dict(
                     domain='versions',
                     url="/rlmtools/static/graphs/%s" % image,
                     href="/rlmtools/showGraph?title=%s&domain=%s" % \
                             ("Version Statistics", "versions")))
        else:
            graphs.append( dict(
                     domain='versions',
                     url="",
                     href=""))

        return self.render('versionlist',
                         dict( versions=versions,
                               graphs=graphs ))
    versionList.exposed = True

    def showGraph(self, title, domain):
        if not self.isREAD(self.getAuthZ("root")):
            return self.message("You need root level read access to view "
                                "graphs.")
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
                url = ""
            else:
                url = "/rlmtools/static/graphs/%s" % image

            d['url'] = url
            graphs.append(d)

        return self.render('graphs',
                         dict( title=title, graphs=graphs )
                        )
    showGraph.exposed = True

    def usage(self):
        if not self.isREAD(self.getAuthZ("root")):
            return self.message("You need root level read access to view "
                                "the usage information.")
        depts = self._server.getDeptNames()
        graphs = []

        image = "usage-1w.png"
        path = os.path.join(config.rrd_dir, 'graphs', image)
        if os.path.exists(path):
            d = dict(summary="Total Usage Statistics:",
                     url="/rlmtools/static/graphs/%s" % image,
                     href="/rlmtools/showGraph?title=%s&domain=%s" % \
                             ("Total Usage Statistics", "usage"))
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
                url = ""
                href = ""
            else:
                url = "/rlmtools/static/graphs/%s" % image
                href = "/rlmtools/showGraph?title=%s&domain=%s" % (summary,
                                                                   dom)

            graphs.append( dict(url=url, href=href, summary=summary) )

        return self.render('usage', dict(graphs=graphs))
    usage.exposed = True

    def search(self, searchBox=None, dest=None):
        if not self.isREAD(self.getAuthZ("root")):
            return self.message("You need root level read access to search.")
        
        # This works a lot like the dept() method above
        # set some globals to speed helper fucntions
        self.days7 = datetime.timedelta(7)
        self.today = datetime.datetime.today()
        
        if searchBox is None:
            # Just show an empty search and allow user to start typing
            clients = []
        else:
            clients = self._server.getSearchResult(searchBox)

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
                self._checkClient(client)

        return self.render('search', dict(
                                          clients=clients,
                                          error=error,
                                          initial=(searchBox is None)
                                          ))
    search.exposed = True



def main():
    parser = optparse.OptionParser()
    parser.add_option("-C", "--configfile", action="store",
                      default=defaultConfFiles,
                      dest="configfile",
                      help="Configuration file")
    parser.add_option("-a", "--auth", action="store", default=None,
                      dest="auth", 
                      help="The webapp will pretend you are this user.")
    (options, args) = parser.parse_args()

    # Start up configuration/logging/databases
    configDragon.initConfig(options.configfile)
    config = configDragon.config

    # Handle testing harness authorization
    if options.auth is not None:
        config.vars['auth'] = ["", False]
        config.auth = options.auth

    # Set "error_page.500" in config to specify a custome error page in CP2.3
    staticDir = os.path.join(os.path.dirname(__file__), "static")
    staticDir = os.path.abspath(staticDir)

    graphDir = os.path.join(config.rrd_dir, 'graphs')

    cherrypy.config.update({"/rlmtools/static": {
                               'static_filter.on': True,
                               'static_filter.dir': staticDir },
                            "/rlmtools/static/graphs": {
                               'static_filter.on': True,
                               'static_filter.dir': graphDir },
                           })

    cherrypy.tree.mount(Application(), '/rlmtools')
    cherrypy.server.start()

def wsgi(req):
    if req.get_options().has_key('rlmtools.configfile'):
        configfile = req.get_options()['rlmtools.configfile']
    else:
        configfile = defaultConfFiles

    # Start up configuration/logging/databases
    configDragon.initConfig(configfile)
    config = configDragon.config

    staticDir = os.path.join(os.path.dirname(__file__), "static")
    staticDir = os.path.abspath(staticDir)

    graphDir = os.path.join(config.rrd_dir, 'graphs')

    cherrypy.config.update({"server.environment": "production",
                            "server.protocolVersion": "HTTP/1.1",
                            "server.log_file": "/var/log/rlmtools-cherrypy.log"})
    cherrypy.config.update({"/rlmtools/static": {
                               'static_filter.on': True,
                               'static_filter.dir': staticDir },
                            "/rlmtools/static/graphs": {
                               'static_filter.on': True,
                               'static_filter.dir': graphDir }
                           })

    cherrypy.tree.mount(Application(), '/rlmtools')
    cherrypy.server.start(initOnly=True, serverClass=None)

if __name__ == "__main__":
    main()
    
