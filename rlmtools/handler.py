#!/usr/bin/python

##     Simple mod_python XML-RPC server
##     Copyright (C) 2003 NC State University
##     Written by Jack Neely <slack@quackmaster.net>

##     SDG

##     This program is free software; you can redistribute it and/or modify
##     it under the terms of the GNU General Public License as published by
##     the Free Software Foundation; either version 2 of the License, or
##     (at your option) any later version.

##     This program is distributed in the hope that it will be useful,
##     but WITHOUT ANY WARRANTY; without even the implied warranty of
##     MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
##     GNU General Public License for more details.

##     You should have received a copy of the GNU General Public License
##     along with this program; if not, write to the Free Software
##     Foundation, Inc., 675 Mass Ave, Cambridge, MA 02139, USA.

# This is the actual server that mod_python will use to serve out XMLRPC.
# You'll need a .htaccess file with something that looks like the following
# so that Apache will know what to do:
#
# AddHandler python-program .py
# PythonHandler handler
# PythonDebug On


from mod_python import apache
from types import *
import xmlrpclib
import string
import os.path

## API that is exposed
import configDragon  # setup logging early
import API
import server
import logging

def handler(req):
    "Process XML_RPC"

    log = logging.getLogger("xmlrpc")

    # Log the request
    if req.headers_in.has_key('User-Agent'):
        userAgent = req.headers_in['User-Agent']
    else:
        userAgent = "None"

    log.info("%s - %s - %s" % (req.get_remote_host(apache.REMOTE_NOLOOKUP),
                              userAgent, req.the_request))

    if not req.method == "POST":
        log.debug("Refusing POST method request.  (Probably a web browser.)")
        return apache.HTTP_BAD_REQUEST
    
    data = req.read(int(req.headers_in['content-length']))
    params, method = xmlrpclib.loads(data)
    params = list(params)

    method_ret = call_method(method, params, req)
    ret = ""
    
    if not isinstance(method_ret, xmlrpclib.Fault):
        if not type(method_ret) is TupleType:
            method_ret = (method_ret, )
        
        ret = xmlrpclib.dumps(method_ret, methodresponse=1)
    else:
        apache.log_error(str(method_ret))
        return apache.HTTP_INTERNAL_SERVER_ERROR

    req.content_type = 'text/xml'
    req.headers_out.add('content-length', str(len(ret)))
    req.send_http_header()
    req.write(ret)

    return apache.OK


def call_method(method, params, req):
    "Find an exported method that matches what we've been given and call it."

    log = logging.getLogger("xmlrpc")
    API.req = req

    list = string.split(method, '.')

    # Handle conversion to a versioned API:  If the method params do NOT
    # start with an int we make it start with 0.  This requires that the
    # first param for all functions must always be the api version.
    if len(params) > 0 and not isinstance(params[0], int):
        params.insert(0, 0)
    if len(params) == 0:
        params = [0]

    # Now walk down the tree and check export lists
    func = API
    if "__API__" not in dir(API):
        # Mother fuck!  WHY?!?!?!
        s = "No __API__!! dir(API) == %s" % str(dir(API))
        reload(API)
    for module in list:
        if module in func.__API__:
            try:
                func = func.__getattribute__(module)
            except AttributeError, e:
                log.warning("Attribute Error raised finding API calls")
                server.logException()
                #raise 

        else:
            log.warning("Requested method %s not exported or found." % method)
            return xmlrpclib.Fault(1000, "%s not exported or found.\n"
                                   % method)

    try:
        ret = apply(func, params)
    except Exception, e:
        log.warning("Exception during function run!")
        log.warning(str(e))
        log.warning(str(dir(server)))
        server.logException()
        return xmlrpclib.Fault(1000, str(e))

    return ret

