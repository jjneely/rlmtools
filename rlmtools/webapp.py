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

class Application(object):

    def __init__(self):
        self.__server = server.Server("pamsadmin.pams.ncsu.edu")

    def index(self):
        t = self.__server.getTotalClients()
        active = self.__server.getActiveClients()
        departments = self.__server.getDepartments()

        for dept in departments:
            dept['url'] = "%s/dept?dept_id=%s" % (url(),
                                                  dept['dept_id'])
        return serialize('templates.index', 
                         dict(departments=departments,
                              active=active,
                              supported=t[0],
                              notsupported=t[1],
                              notregistered=t[2]))
    index.exposed = True

    def dept(self, dept_id):
        services = ['updates', 'client'] # Services that affect client status
        clients = self.__server.getClientList(int(dept_id))
        days30 = datetime.timedelta(30) # 30 days
        days7 = datetime.timedelta(7)
        today = datetime.datetime.today()
        support = []
        nosupport = []
        backurl = "%s" % url()

        for client in clients:
            client['status'] = True
            client['url'] = "%s/client?host_id=%s" % (url(),
                                                      client['host_id'])
 
            if client['lastcheck'] < today - days30:
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
        days30 = datetime.timedelta(30) # 30 days
        today = datetime.datetime.today()
        detail = self.__server.getClientDetail(int(host_id))
        detail['lastcheck_good'] = detail['lastcheck'] != None and \
                                   detail['lastcheck'] > today - days30
        goodStatus = {}
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

            if goodStatus.has_key(row['service']):
                row['class'] = "neutral"
            elif row['success']:
                goodStatus[row['service']] = True
                row['class'] = "good"
            else:
                row['class'] = "bad"


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
    
