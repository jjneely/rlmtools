#!/usr/bin/python

# __init__.py - Initialize the RLMTools webapp
# Copyright 2012 NC State University
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

from flask import Flask

# Global configuration for RLMTools
config = None

app = Flask(__name__)

# Use my logger please
app.config["LOGGER_NAME"] = "xmlrpc"

# Modules exposing views must be imported below
import rlmtools.webapp
import rlmtools.webks
import rlmtools.webadmin
import rlmtools.webperms
import rlmtools.webacl
import rlmtools.API     # XMLRPC API

