#!/usr/bin/python

# webapp.py - The CherryPy based web app
# Copyright 2006 NC State University
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
import os
import os.path
import pwd
import datetime
import kid
kid.enable_import()

import cherrypy
import server

def importer(module):
    tree = module.split('.')
    for path in sys.path:
        basepath = apply(os.path.join, [path] + tree[:-1])
        file = os.path.join(basepath, tree[-1]+'.kid')
        if os.path.exists(file):
            return kid.Template(file=file)

    return None

def serialize(mod, dict):
    template = importer(mod)
    if template == None:
        template = importer('rlmtools.%s' % mod)

    if template == None:
        raise Exception("No kid module %s" % mod)

    for key, value in dict.items():
        setattr(template, key, value)

    return template.serialize(encoding='utf-8', output='xhtml')

def url():
    base = cherrypy.request.base + cherrypy.tree.mount_point()
    if base.endswith('/'):
        return base[:-1]
    else:
        return base

class Auth(object):
    
    def __init__(self):
        try:
            env = cherrypy.request.wsgi_environ
        except AttributeError:
            self.null()

        try:
            self.userid = env['WRAP_USERID']
            self.affiliation = env['WRAP_AFFIL']
            self.expire = env['WRAP_EXPDATE']
            self.ipaddress = env['WRAP_ADDRESS']
        except KeyError:
            self.null()

    def null(self):
        self.userid = None
        self.affiliation = None
        self.expire = None
        self.ipaddress = None

    def isAuthenticated(self):
        return self.userid != None

    def getName(self):
        # Note that the users that authenticate will also be in the system's
        # password db (hesiod/ldap)
        if not self.isAuthenticated():
            return "Guest User"
        return pwd.getpwnam(self.userid)[4]        
    
class Application(object):

    def __init__(self):
        self.__server = server.Server("pamsadmin.pams.ncsu.edu")

    def index(self):
        totals = self.__server.getTotalClients()
        active = self.__server.getActiveClients()
        departments = self.__server.getDepartments()

        for dept in departments:
            dept['url'] = "%s/dept?dept_id=%s" % (url(),
                                                  dept['dept_id'])
        return serialize('templates.index', 
                         dict(departments=departments,
                              active=active,
                              totals=totals,
                              name=Auth().getName()))
    index.exposed = True

    def dept(self, dept_id):
        services = ['updates', 'client'] # Services that affect client status
        clients = self.__server.getClientList(int(dept_id))
        days7 = datetime.timedelta(7)
        today = datetime.datetime.today()
        support = []
        nosupport = []
        backurl = "%s" % url()

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

            if client['support']:
                support.append(client)
            else:
                nosupport.append(client)

        return serialize('templates.dept', dict(support=support, 
                         nosupport=nosupport, 
                         department=self.__server.getDeptName(int(dept_id)),
                         backurl=backurl ))
    dept.exposed = True

    def client(self, host_id):
        days7 = datetime.timedelta(7)
        today = datetime.datetime.today()
        detail = self.__server.getClientDetail(int(host_id))
        detail['warnUpdate'] = False
        detail['lastcheck_good'] = detail['lastcheck'] != None and \
                                   detail['lastcheck'] > today - days7 and \
                                   detail['lastcheck'] > detail['installdate']
        status = {}
        if detail['recvdkey'] == 1:
            backurl = "%s/dept?dept_id=%s" % (url(),
                                              detail['dept_id'])
        else:
            backurl = "%s/notregistered" % url()

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

        return serialize('templates.client',
                         dict(client=detail, status=detail['status'],
                              backurl=backurl))
    client.exposed = True

    def status(self, status_id):
        status = self.__server.getStatusDetail(int(status_id))
        backurl = "%s/client?host_id=%s" % (url(),
                                            status['host_id'])
            
        if status['data'] == None or status['data'] == "":
            status['data'] = "No data available."
            status['data_class'] = "neutral"
        elif status['success']:
            status['data_class'] = "good"
        else:
            status['data_class'] = "bad"

        return serialize('templates.status', 
                         dict(status=status, backurl=backurl))
    status.exposed = True

    def notregistered(self):
        backurl = "%s" % url()
        clients = self.__server.getNotRegistered()
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

        return serialize('templates.notregistered',
                         dict(support=support,
                              nosupport=nosupport,
                              department="Not Registered",
                              backurl=backurl)
                        )
    notregistered.exposed = True

    def problems(self):
        clients = self.__server.getProblemList()
        data = {}

        for client in clients:
            host = {}
            host['hostname'] = client['hostname']
            host['url'] = "%s/client?host_id=%s" % (url(), client['host_id'])
            if data.has_key(client['deptname']):
                data[client['deptname']].append(host)
            else:
                data[client['deptname']] = [host]
        
        return serialize('templates.problems',
                         dict( clients=data,
                               backurl=url())
                        )
    problems.exposed = True

    def noupdates(self):
        clients = self.__server.getNoUpdates()
        data = {}

        for client in clients:
            host = {}
            host['hostname'] = client['hostname']
            host['url'] = "%s/client?host_id=%s" % (url(), client['host_id'])
            if data.has_key(client['deptname']):
                data[client['deptname']].append(host)
            else:
                data[client['deptname']] = [host]
        
        return serialize('templates.noupdates',
                         dict( clients=data,
                               backurl=url())
                        )
    noupdates.exposed = True

def main():
    cherrypy.tree.mount(Application(), '/')
    cherrypy.server.start()

def wsgi(start_responce):
    cherrypy.tree.mount(Application(), '/rlmtools')
    cherrypy.config.update({"server.environment": "production",
                            "server.protocolVersion": "HTTP/1.1",
                            "server.log_file": "/tmp/rlmtools.log"})
    cherrypy.server.start(initOnly=True, serverClass=None)

if __name__ == "__main__":
    main()
    
