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
import sys
import os
import os.path

from webKickstart.webks import webKickstart

import configDragon
from webcommon import *

from flask import request

# Flask Application object
from rlmtools import app

def _getWebKs():
    # Helper function to return a WebKickstart object
    return webKickstart('url', {}, configDragon.config.webks_dir)

@app.route("/webKickstart")
def wk_index():
    isREADby("root")
    return render('wk.index', dict(title="Web-Kickstart Tools"))

@app.route("/webKickstart/rawKickstart")
def rawKickstart():
    isREADby("root")
    host = request.args["host"]

    host = host.strip()
    w = _getWebKs()
    w.setDebug(True)           # Previent running of things that shouldn't
                               # for preview mode
    tuple = w.getKS(host)

    return tuple[1], 200, {"Content-Type": "text/plain"}

@app.route("/webKickstart/debugtool", methods=["POST"])
def debugtool():
    isREADby("root")
    host = request.form["host"]

    host = host.strip()
    if host == "":
        return self.render('wk.debugtool', dict(host="None",
              kickstart="# You failed to provide a host to check."))

    w = _getWebKs()
    w.setDebug(True)           # Previent running of things that shouldn't
                               # for preview mode
    tuple = w.getKS(host)

    return render('wk.debugtool', dict(host=host, kickstart=tuple[1]))

@app.route("/webKickstart/collision", methods=["POST"])
def collision():
    isREADby("root")
    host = request.form["host"]

    host = host.strip()
    if host == "":
        return render('wk.debugtool', dict(host="None",
              kickstart="# You failed to provide a host to check."))
    
    w = _getWebKs()
    tuple = w.collisionDetection(host)
    return render('wk.collision', dict(host=host, output=tuple[1]))

@app.route("/webKickstart/checkconfigs", methods=["POST"])
def checkconfigs():
    isREADby("root")
    
    w = _getWebKs()
    tuple = w.checkConfigHostnames()

    return render('wk.checkconfigs', dict(output=tuple[1]))

