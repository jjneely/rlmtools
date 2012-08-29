#!/usr/bin/python

import httplib2
import urllib

class RestClient(object):

    def __init__(self, url, username=None, password=None, ca=None,
                 sslkey=None, sslcrt=None, sslverify=True):

        self.http = httplib2.Http("/tmp/httplib2-cache", timeout=30,
                ca_certs=ca, 
                disable_ssl_certificate_validation=not sslverify)

        if sslkey and sslcrt:
            self.http.add_certificate(sslkey, sslcrt, "")
        elif username and password:
            self.http.add_credentials(username, password)

        if url.endswith("/"):
            self.url = url[:-1]
        else:
            self.url = url

        self.agent = "Slack Jackson 0.0.0"

    def _normalize(self, path):
        ret = path
        if ret.endswith("/"):
            ret = ret[:-1]
        if ret.startswith("/"):
            ret = ret[1:]
        
        return ret

    def _go(self, method, resource, args=None, headers={}, body=None):
        path = self._normalize(resource)

        if args is not None:
            path = u"%s?%s" % (path, urllib.urlencode(args))

        return self.http.request(u"%s/%s" % (self.url, path),
                method=method, headers=headers, body=body)

    def get(self, resource, args=None, headers={}):

        return self._go("GET", resource, args=args, headers=headers)

    def delete(self, resource, args=None, headers={}):

        return self._go("DELETE", resource, args=args, headers=headers)

    def put(self, resource, args=None, headers={}, body=None):

        return self._go("PUT", resource, args=args, headers=headers,
                body=body)

