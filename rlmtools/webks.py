# ks.py -- apache mod_python handler
#
# Copyright, 2002 - 2009 Jack Neely <jjneely@ncsu.edu>
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

from webKickstart import webKickstart
from webKickstart import configtools

import configDragon
from webcommon import *

class Application(AppHelpers):

    def _getWebKs(self):
        # Helper function to return a WebKickstart object
        return webKickstart('url', {}, configDragon.config.webks_dir)

    def index(self):
        if not self.isREAD(self.getAuthZ("root")):
            return self.message("You need root level read access to debug "
                                    "Web-Kickstarts.")
        
        return self.render('wk.index', dict(title="Web-Kickstart Tools"))
    index.exposed = True

    def rawKickstart(self, host):
        if not self.isREAD(self.getAuthZ("root")):
            return self.message("You need root level read access to debug "
                                    "Web-Kickstarts.")

        host = host.strip()
        w = self._getWebKs()
        w.setDebug(True)           # Previent running of things that shouldn't
                                   # for preview mode
        tuple = w.getKS(host)

        cherrypy.response.headers['Content-Type'] = 'text/plain'
        return tuple[1]
    rawKickstart.exposed = True

    def debugtool(self, host):
        if not self.isREAD(self.getAuthZ("root")):
            return self.message("You need root level read access to debug "
                                    "Web-Kickstarts.")
        
        host = host.strip()
        if host == "":
            return self.render('wk.debugtool', dict(host="None",
                  kickstart="# You failed to provide a host to check."))

        w = self._getWebKs()
        w.setDebug(True)           # Previent running of things that shouldn't
                                   # for preview mode
        tuple = w.getKS(host)

        return self.render('wk.debugtool', dict(host=host, kickstart=tuple[1]))
    debugtool.exposed = True

    def collision(self, host):
        if not self.isREAD(self.getAuthZ("root")):
            return self.message("You need root level read access to debug "
                                    "Web-Kickstarts.")
        
        host = host.strip()
        if host == "":
            return self.render('wk.debugtool', dict(host="None",
                  kickstart="# You failed to provide a host to check."))
        
        w = self._getWebKs()
        tuple = w.collisionDetection(host)
        return self.render('wk.collision', dict(host=host, output=tuple[1]))
    collision.exposed = True

    def checkconfigs(self):
        if not self.isREAD(self.getAuthZ("root")):
            return self.message("You need root level read access to debug "
                                    "Web-Kickstarts.")
        
        w = self._getWebKs()
        tuple = w.checkConfigHostnames()

        return self.render('wk.checkconfigs', dict(output=tuple[1]))
    checkconfigs.exposed = True


