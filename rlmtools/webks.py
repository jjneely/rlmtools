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
from webKickstart.libwebks import LibWebKickstart

import configDragon
from webcommon import *

from flask import request, g, abort

# Flask Application object
from rlmtools import app

def _getWebKs():
    # Helper function to return a WebKickstart object
    return webKickstart('url', {}, configDragon.config.webks_dir)

@app.route("/webKickstart/")
@app.route("/webKickstart/build/")
@app.route("/webKickstart/kickstart/")
@app.route("/webKickstart/collision/")
def wk_index():
    isREADby("root")
    return render('wk.index', dict(title="Web-Kickstart Tools"))

@app.route("/webKickstart/kickstart/<host>")
def debugtool(host):
    # XXX: Should we support Web-Kickstart's tokens?  libwebks needs
    # updating if we do.
    isREADby("root")
    raw = 'raw' in request.args

    host = str(host)
    if host == "":
        return render('wk.debugtool', dict(host="None",
              kickstart="# You failed to provide a host to check."))

    w = _getWebKs()
    w.setDebug(True)           # Previent running of things that shouldn't
                               # for preview mode

    # Parse 1: Find the dept string
    libwk = LibWebKickstart(configDragon.config.webks_dir)
    keys = libwk.getEverything(host)
    if keys is not None and "dept" in keys:
        isADMINby(keys["dept"][0][0])
    elif keys is not None:
        g.error = "Web-Kickstart config file does not state a department."
        abort(400)

    # Parse 2:  Generate the whole she-bang
    tuple = w.getKS(host)

    if raw:
        return tuple[1], 200, {"Content-Type": "text/plain"}
    else:
        return render('wk.debugtool', dict(host=host, kickstart=tuple[1]))

@app.route("/webKickstart/collision/<host>")
def collision(host):
    isREADby("root")

    host = host.strip()
    if host == "":
        return render('wk.debugtool', dict(host="None",
              kickstart="# You failed to provide a host to check."))
    
    w = _getWebKs()
    tuple = w.collisionDetection(host)
    return render('wk.collision', dict(host=host, output=tuple[1]))

@app.route("/webKickstart/checkconfigs")
def checkconfigs():
    isREADby("root")
    
    w = _getWebKs()
    tuple = w.checkConfigHostnames()

    return render('wk.checkconfigs', dict(output=tuple[1]))

@app.route("/webKickstart/build/<host>")
def build(host):

    return render("wk.build", dict(
        message="",
        host=host,
        depts=['unity', 'foo'],
        ))

