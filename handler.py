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
API = apache.import_module("API", log=1)

def handler(req):
    "Process XML_RPC"
    
    fn = os.path.basename(req.filename)
    if fn != "handler.py":
        # We know because of the PythonHandler that the user requested
        # a python (.py) file.  Find it and give it to them.
        try:
            mod = __import__(fn[:-3])
            return mod.handler(req)
        except Exception, e:
            apache.log_error("Failed to import %s" % fn)
            return apache.HTTP_BAD_REQUEST

    if not req.method == "POST":
        #req.content_type = "text/plain"
        #req.send_http_header()
        #req.write("Get off me with your web browser, boy!\n")
        return apache.HTTP_BAD_REQUEST
    
    data = req.read(int(req.headers_in['content-length']))
    params, method = xmlrpclib.loads(data)
    params = list(params)

    #API.req = req
    method_ret = call_method(method, params, req)
    ret = ""
    
    if not isinstance(method_ret, xmlrpclib.Fault):
        if not type(method_ret) is TupleType:
            method_ret = (method_ret, )
        
        ret = xmlrpclib.dumps(method_ret, methodresponse=1)
    else:
        apache.log_error(str(method_ret))
        return apache.HTTP_METHOD_NOT_ALLOWED

    req.content_type = 'text/xml'
    req.headers_out.add('Content-length', str(len(ret)))
    req.send_http_header()
    req.write(ret)

    return apache.OK


def call_method(method, params, req):
    "Find an exported method that matches what we've been given and call it."

    API.req = req

    list = string.split(method, '.')
                     
    # Now walk down the tree and check export lists
    func = API
    if not dir(API).has_key("__API__"):
        # Mother fuck!  WHY?!?!?!
        s = "No __API__!! dir(API) == %s" % str(dir(API))
        raise AttributeError(s)
    for module in list:
        if module in func.__API__:
            try:
                func = func.__getattribute__(module)
            except AttributeError, e:
                s = "AttributeError!  dir(func) = %s\n" % str(dir(func))
                s += "Module = %s\n" % module
                s += "Exception = %s\n" % str(e)
                raise AttributeError(s)

        else:
            return xmlrpclib.Fault(1000, "%s not exported or found.\n"
                                   % method)

    try:
        ret = apply(func, params)
    except TypeError, e:
        return xmlrpclib.Fault(1000, "%s exists but parameters were wrong.\n"
                               % method)
    except Exception, e:
        return xmlrpclib.Fault(1000, str(e))

    return ret

