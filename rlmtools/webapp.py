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

import kid
kid.enable_import()

import cherrypy
import server

def serialize(mod, dict):
    template = __import__(mod)
    if mod.rfind('.') > -1:
        template = getattr(template, mod[mod.rfind('.')+1:])
    else:
        template = getattr(template, mod)

    for key, value in dict.items():
        setattr(template, key, value)

    return template.serialize(encoding='utf-8', output='xhtml')

class Application(object):

    def __init__(self):
        self.__server = server.Server("pamsadmin.pams.ncsu.edu")

    def index(self):
        print self.__server.getDepartments()
        return serialize('templates.index', 
                         dict(departments=self.__server.getDepartments()))
    index.exposed = True


if __name__ == "__main__":
    cherrypy.root = Application()
    cherrypy.server.start()

