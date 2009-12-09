from genshi.template import TemplateLoader

import cherrypy
import webServer
import os.path
import pwd

def url():
    base = cherrypy.request.base + cherrypy.tree.mount_point()
    if base.endswith('/'):
        return base[:-1]
    else:
        return base

def short(fqdn): return fqdn.split('.')[0]

class Auth(object):
    
    def __init__(self):
        try:
            env = cherrypy.request.wsgi_environ
        except AttributeError:
            self.null()

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
        return self.userid != None

    def getName(self):
        # Note that the users that authenticate will also be in the system's
        # password db (hesiod/ldap)
        if not self.isAuthenticated():
            return "Guest User"
        return pwd.getpwnam(self.userid)[4]        

class AppHelpers(object):

    # Permission bitfield operations
    ADMIN = 0x01
    WRITE = 0x02
    READ  = 0x04

    def isADMIN(self, field): return (field & self.ADMIN) == 1
    def isWRITE(self, field): return (field & self.WRITE) >> 1 == 1
    def isREAD(self, field): return (field & self.READ) >> 2 == 1

    def __init__(self, loader=None):
        # The DB interface is safe enough for multiple classes to
        # instantiate their own.
        self._server = webServer.WebServer()

        # However, create a shortcut for only using one global template loader
        if loader is None:
            self.loader = TemplateLoader([os.path.join(os.path.dirname(__file__), 
                                         'templates')], auto_reload=True)
        else:
            self.loader = loader

        if cherrypy.config.configs['global']['server.protocol_version'] \
                == "HTTP/1.1":
            self.outEncoding = 'utf-8'
        else:
            self.outEncoding = 'latin-1'

    def render(self, tmpl, dict):
        # Add some default variables
        dict['name'] = Auth().getName()
        dict['baseURL'] = url()
        dict['templateName'] = tmpl

        compiled = self.loader.load('%s.xml' % tmpl)
        stream = compiled.generate(**dict)
        return stream.render('xhtml', encoding=self.outEncoding)

    def isAuthenticated(self):
        return Auth().isAuthenticated()
    
    def _parseDept(self, void):
        """Figure out what the ID of the dept is from whatever is in void.
           Returns an int or None."""
        if isinstance(void, int):
            return void
        if void.isdigit():
            return int(void)
        # If we are here this must be a name, use the DB to convert
        return self._server.getDeptIDNoCreate(void)

    def getAuthorization(self, dept):
        """Return the bitfield that indicates what access permissions the user
           has that is currently poking the web interface.  0 Mean no rights."""

        a = Auth()
        # Basic sanity
        if not a.isAuthenticated():
            return 0

        # What is our dept_id?
        d = self._parseDept(dept)

        acl = self._server.getAccess(a.userid, d)
        return acl

