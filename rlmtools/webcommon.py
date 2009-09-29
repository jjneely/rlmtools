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

    def isAuthorized(self):
        # STUB!!!
        return True

    def getName(self):
        # Note that the users that authenticate will also be in the system's
        # password db (hesiod/ldap)
        if not self.isAuthenticated():
            return "Guest User"
        return pwd.getpwnam(self.userid)[4]        

class AppHelpers(object):

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

    def render(self, tmpl, dict):
        # Add some default variables
        dict['name'] = Auth().getName()
        dict['baseURL'] = url()

        compiled = self.loader.load('%s.xml' % tmpl)
        stream = compiled.generate(**dict)
        return stream.render('xhtml')

