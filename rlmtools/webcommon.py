from flask import url_for

from genshi.template import TemplateLoader

import configDragon
import cherrypy
import webServer
import os.path
import pwd

def url():
    base = url_for("index")  # the "index" method must exist with route = /
    if base.endswith('/'):
        return base[:-1]
    else:
        return base

def short(fqdn): return fqdn.split('.')[0]

class Auth(object):
    
    def __init__(self):
        self.null()
        if "auth" in configDragon.config.vars:
            # We are running in test harness, fake that auth, mode
            self.userid = configDragon.config.auth
            self.alliliation = "El Fako Land"
            self.expire = "37:00"
            self.ipaddress = "No Man's Land"
            return

        try:
            env = cherrypy.request.wsgi_environ
        except AttributeError:
            # Gah!  Where is the WSGI environment?
            return

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
        return self.userid is not None

    def getName(self):
        # Note that the users that authenticate will also be in the system's
        # password db (hesiod/ldap)
        if not self.isAuthenticated():
            return "Guest User"
        return pwd.getpwnam(self.userid)[4]        

class AppHelpers(object):
    # XXX: Here to hold her together during porting to Flash
    pass

# Permission bitfield operations
ADMIN = 0x01
WRITE = 0x02
READ  = 0x04

def isADMIN(field): return (field & ADMIN) == 1
def isWRITE(field): return (field & WRITE) >> 1 == 1
def isREAD(field): return (field & READ) >> 2 == 1

def adminOf(dept_id): return isADMIN(getAuthZ(dept_id))

def mapPermBits(field):
    if isADMIN(field): return "admin"
    if isWRITE(field): return "write"
    if isREAD(field) : return "read"
    return "unknown"

#def __init__(self, loader=None):
#    # The DB interface is safe enough for multiple classes to
#    # instantiate their own.
#    self._server = webServer.WebServer()
#
#    # DB query, do it once only
#    self._default_admin = configDragon.config.default_admin
#
#    # However, create a shortcut for only using one global template loader
#    if loader is None:
#        self.loader = TemplateLoader([os.path.join(os.path.dirname(__file__), 
#                                     'templates')], auto_reload=True)
#    else:
#        self.loader = loader

_tloader = TemplateLoader([os.path.join(os.path.dirname(__file__),
                          'templates')], auto_reload=True)

def render(tmpl, dict):
    # Add some default variables
    a = Auth()
    dict['name'] = a.getName()
    dict['userid'] = a.userid
    dict['baseURL'] = url()
    dict['templateName'] = tmpl

    if not tmpl.endswith(".xml"):
        tmpl = "%s.xml" % tmpl

    compiled = _tloader.load(tmpl)
    stream = compiled.generate(**dict)
    return stream.render('xhtml', encoding='utf8')

def message(str):
    a = Auth()
    acls = self._server.memberOfACL(a.userid)

    return render('message', dict(
                           message=str,
                           userid=a.userid,
                           acls=acls,
                           fullname=a.getName(),
                      ))

def isAuthenticated():
    return Auth().isAuthenticated()

def _parseDept(void):
    """Figure out what the ID of the dept is from whatever is in void.
       Returns an int or None."""
    if isinstance(void, int) or isinstance(void, long):
        return void
    if void.isdigit():
        return int(void)
    # If we are here this must be a name, use the DB to convert
    return self._server.getDeptIDNoCreate(void)

def getAuthZ(dept):
    """Return the bitfield that indicates what access permissions the user
       has that is currently poking the web interface.  0 Mean no rights."""

    a = Auth()
    # Basic sanity
    if not a.isAuthenticated():
        return 0

    # Check the default initial admin
    if a.userid == configDragon.config.default_admin:
        return 7   # read, write, admin

    # What is our dept_id?
    d = self._parseDept(dept)

    perm = self._server.getAccess(a.userid, d)
    return perm

