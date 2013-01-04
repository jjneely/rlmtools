from flask import request, url_for, abort, g

from genshi.template import TemplateLoader

import configDragon
import webServer
import wrap
import os.path
import pwd
import socket
import logging

# Flask application object
from rlmtools import app

log = logging.getLogger('xmlrpc')

class Auth(object):
   
    # XXX: Cache location of WRAP key?

    def __init__(self):
        self.null()
        if "auth" in configDragon.config.vars:
            # We are running in test harness, fake that auth, mode
            self.userid = configDragon.config.auth
            self.alliliation = "El Fako Land"
            self.expire = "37:00"
            self.ipaddress = "No Man's Land"
            return

        auth = wrap.WRAPCookie(request.cookies, configDragon.config.wrapkey)

        if auth.isValid():
            self.userid = auth.userID
            self.affiliation = auth.affiliation
            self.expire = auth.expiration
            self.ipaddress = auth.address
        else:
            self.null()

    def null(self):
        self.userid = None
        self.affiliation = None
        self.expire = None
        self.ipaddress = None

    def isAuthenticated(self):
        return self.userid is not None

    def require(self):
        if not self.isAuthenticated():
            abort(401)

    def getName(self):
        # Note that the users that authenticate will also be in the system's
        # password db (hesiod/ldap)
        if not self.isAuthenticated():
            return "Guest User"
        return pwd.getpwnam(self.userid)[4]        

_tloader = TemplateLoader([os.path.join(os.path.dirname(__file__),
                          'templates')], auto_reload=True)
_server = None

def _before_each_fqdn():
    ip = request.remote_addr
    
    if ip.startswith('::ffff:'):
        # Ugh...IPv6 crap in v4 addresses
        ip = ip[7:]
    try:
        addr = socket.gethostbyaddr(ip)
    except socket.herror, e:
        if e[0] == 0:
            # No error...IP does not resolve
            log.warning("Request from %s which does not resolve" % ip)
            addr = [ip]
        else:
            log.error("HELP! socket.gethostbyaddr(%s) blew up with: %s" \
                    % (ip, e))
            raise

    g.ip = ip
    g.fqdn = addr[0]

def _before_each_auth():
    g.auth = Auth()

def _init_webcommon():
    global _server
    _server = webServer.WebServer()

app.before_first_request(_init_webcommon)
app.before_request(_before_each_fqdn)
app.before_request(_before_each_auth)

# Permission bitfield operations
ADMIN = 0x01
WRITE = 0x02
READ  = 0x04

def isADMIN(field): return (field & ADMIN) == 1
def isWRITE(field): return (field & WRITE) >> 1 == 1
def isREAD(field): return (field & READ) >> 2 == 1

def isREADby(dept):
    return _authZ_require(dept, "READ")

def isWRITEby(dept):
    return _authZ_require(dept, "WRITE")

def isADMINby(dept):
    return _authZ_require(dept, "ADMIN")

def _authZ_require(dept, acl):
    g.auth.require()
    display = None

    if isinstance(dept, int) or isinstance(dept, long):
        display = _server.getDeptName(dept)
    elif dept.isdigit():
        display = _server.getDeptName(int(dept))
    else:
        display = dept

    if acl == "ADMIN":
        f = isADMIN
    elif acl == "WRITE":
        f = isWRITE
    elif acl == "READ":
        f = isREAD
    else:
        raise StandardError("Invalid ACL given in authorization require")

    if not f(getAuthZ(dept)):
        msg = "You do not seem to have %s access on the %s level of the "  \
              "department hierarchy.  Those permissions are required for " \
              "this page." % (acl, display)

        # Stuff this in the Flask globals so we can reference the error
        # message later
        g.error = msg
        abort(403)
    else:
        return True

def mapPermBits(field):
    if isADMIN(field): return "admin"
    if isWRITE(field): return "write"
    if isREAD(field) : return "read"
    return "unknown"

def isAuthenticated():
    return g.auth.isAuthenticated()

def getAuthZ(dept):
    """Return the bitfield that indicates what access permissions the user
       has that is currently poking the web interface.  0 Mean no rights."""

    # Basic sanity
    if not g.auth.isAuthenticated():
        return 0

    # Check the default initial admin
    if g.auth.userid == configDragon.config.default_admin:
        return 7   # read, write, admin

    # What is our dept_id?
    d = _parseDept(dept)

    perm = _server.getAccess(g.auth.userid, d)
    return perm

def url():
    base = request.url_root
    if base.endswith('/'):
        return base[:-1]
    else:
        return base

def short(fqdn): return fqdn.split('.')[0]

def render(tmpl, dict):
    # Add some default variables
    dict['name'] = g.auth.getName()
    dict['userid'] = g.auth.userid
    dict['baseURL'] = url()
    dict['templateName'] = tmpl
    dict['acls'] = _server.memberOfACL(g.auth.userid)

    if not tmpl.endswith(".xml"):
        tmpl = "%s.xml" % tmpl

    compiled = _tloader.load(tmpl)
    stream = compiled.generate(**dict)
    return stream.render('xhtml', encoding='utf8')

def message(s):
    return render('message', dict(message=s))

def _parseDept(void):
    """Figure out what the ID of the dept is from whatever is in void.
       Returns an int or None."""
    if isinstance(void, int) or isinstance(void, long):
        return void
    if void.isdigit():
        return int(void)
    # If we are here this must be a name, use the DB to convert
    return _server.getDeptIDNoCreate(void)

@app.errorhandler(401)
def error401(error):
    return message("You do not appear to be authenticated. (Error code 401.)")

@app.errorhandler(403)
def error403(error):
    if hasattr(g, "error"):
        msg = g.error
    else:
        msg = "You are not authorized to look at Liquid Dragon's treasure."

    return message("%s (Error code 403.)" % msg)

@app.errorhandler(400)
def error400(error):
    if hasattr(g, "error"):
        msg = g.error
    else:
        msg = "You are not authorized to look at Liquid Dragon's treasure."

    return message("%s (Error code 400.)" % msg)

