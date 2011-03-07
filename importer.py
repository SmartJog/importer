""" Importer """

import traceback, os, cookielib, urllib2, httplib, socket
import cStringIO
import gzip
from exc import *

__all__ = ['ImporterError', 'ImporterDeserializeError', 'ImporterSerializeError', 'ImporterConnectError', 'Importer']

class ImporterHTTPSHandler(urllib2.HTTPSHandler):
    """ To be used by urllib2, wrap calls to httplib. """
    def __init__(self, key, cert):
        urllib2.HTTPSHandler.__init__(self)
        self.key = key
        self.cert = cert

    def https_open(self, req):
        return self.do_open(self.create_conn, req)

    def create_conn(self, host, timeout = 300):
        return httplib.HTTPSConnection(host, key_file = self.key, cert_file = self.cert)

class ImporterBase(object):
    """
        Base class for both ImporterModule and ImporterVariable.
        Provide call/get/set methods, relying on proper self.__objinst__ object.
        ImporterModule and ImporterVariable are in charge of creating the appropriate object.
    """
    def __init__(self):
        self.__conf__ = {}
        self.__objinst__ = None

    def __getitem__(self, key):
        """
            Used to retrieve data from Importer configuration.
            Let exceptions be thrown.
        """
        return self.__conf__[key]

    def __setitem__(self, key, value):
        """ Set configuration key. """
        self.__conf__[key] = value

    def __delitem__(self, key):
        """ Delete configuration key. """
        del self.__conf__[key]

    def call(self, method, *args, **kw):
        """ Getattr self.__objinst__ which will be a module instance or a variable instance. """
        return getattr(self.__objinst__, method)(*args, **kw)

    def get(self, attr):
        """ Getattr self.__objinst__ and returns. """
        return getattr(self.__objinst__, attr)

class ImporterVariable(ImporterBase):
    def __init__(self, conf, module, klass, *args, **kw):
        ImporterBase.__init__(self)
        self.__mod__ = module
        self.__klass__ = klass
        self.__objinst__ = self.__mod__.get(self.__klass__)(*args, **kw)

class Importer(ImporterBase):
    """
        Main class. Contains all modules.
        Call/get/set/instantiate always check if execution must be done remotely.
    """
    def __init__(self):
        ImporterBase.__init__(self)
        self.__scope__ = {}
        self.__bound__ = None
        self.__cj__ = None

    def call(self, module, method, *args, **kw):
        """
            Perform a call to module.method, passing the given *args, **kw.
            Override ImporterBase.call()
            Return: module.method return.
        """
        if 'distant_url' in self.__conf__.keys():
            mod = '.'.join((module, method))
            return self.__perform_distant__(mod, 'call', *args, **kw)
        try:
            if module in self.__scope__.keys(): # Class instance
                return self.__scope__[module].call(method, *args, **kw)
            mod = __import__(module, {}, {}, [''])
            callee = getattr(mod, method)
            # The __request__ argument is added by the Exporter.
            # It is used only when the __exportable__ flag is present.
            request = kw.pop('__request__', None)
            # This attribute means that the callee object is a _Export object
            # defined by the @exportable decorator.
            # This is used to distinct between a standard python method, or a
            # webengine method, because a webengine method need a request object.
            if hasattr(callee, '__exportable__'): return callee(request, *args, **kw)
            else: return getattr(mod, method)(*args, **kw)
        except Exception, e:
            raise ImporterError(str(e), traceback=traceback.format_exc())

    def get(self, module, attr):
        """ Retrieve an attr from the given module. """
        if 'distant_url' in self.__conf__.keys():
            mod = '.'.join((module, attr))
            return self.__perform_distant__(mod, 'get')
        try:
            if module in self.__scope__.keys(): # Class instance
                return self.__scope__[module].get(attr)
            mod = __import__(module, {}, {}, [''])
            return getattr(mod, attr)
        except Exception, e:
            raise ImporterError(str(e), traceback=traceback.format_exc())

    def instantiate(self, variable, module, klass, *args, **kw):
        """
            Add in the current scope a 'klass' instance from module.
            Similar to module.klass(*args, **kw).
            variable will be usable in the scope as others modules.
        """
        if 'distant_url' in self.__conf__.keys():
            mod = '.'.join((module, klass))
            return self.__perform_distant__(mod, 'instantiate', variable=variable, *args, **kw)
        try:
            if variable in self.__scope__.keys(): return
            module = self.__load_module__(module)
            self.__scope__[variable] = ImporterVariable(self.__conf__, module, klass, *args, **kw)
        except Exception, e:
            raise ImporterError(str(e), traceback=traceback.format_exc())

    def _set_bound(self, bound):
        """ Bound Importer scope to "bound" list. """
        self.__bound__ = bound
    def _get_bound(self):
        """ Returns bound list. """
        return self.__bound__
    bound = property(_get_bound, _set_bound)

    def __perform_distant__(self, module, type, *args, **kw):
        """ Perform the distant call. """
        import cPickle
        try:
            if not self.__cj__:
                self.__cj__ = cookielib.CookieJar()
            if 'timeout' in self.__conf__.keys():
                socket.setdefaulttimeout(self.__conf__['timeout'])
            else:
                socket.setdefaulttimeout(30)
            opener = urllib2.build_opener(urllib2.HTTPCookieProcessor(self.__cj__), ImporterHTTPSHandler(key = self.__conf__.get('ssl_key'), cert = self.__conf__.get('ssl_cert')))
            path = module.replace('.', '/') + '/' #Force trailing slash
            # Should be able to select encoder
            # TODO: Create a wrapper for cPickle, pickle in fallback
            data = cPickle.dumps({'type': type, 'args': args, 'kw': kw}, cPickle.HIGHEST_PROTOCOL)
            req = urllib2.Request(self.__conf__['distant_url'] + path, data, {'WEBENGINE_OUTPUT': 'pickle'})
            # We accept gzipped content
            req.add_header('Accept-Encoding', 'gzip')
            f = opener.open(req)
            if f.headers.get('Content-Encoding') == 'gzip':
                # Decompress the data
                data_compressed = cStringIO.StringIO(f.read())
                gzip_decompressor = gzip.GzipFile(fileobj = data_compressed)
                data_read = gzip_decompressor.read()
            else:
                data_read = f.read()
            # We have to set recv to None, because otherwise, circular dependencies leads to memory leaks.
            f.fp._sock.recv = None
            f.close()
            if data_read == '': return None
            try:
                data_decoded = cPickle.loads(data_read)
                return data_decoded
            except cPickle.UnpicklingError:
                raise ImporterDeserializeError(data_read, traceback=traceback.format_exc())
        except urllib2.HTTPError, e:
            if e.headers.get('Content-Encoding') == 'gzip':
                # Decompress the data
                data_compressed = cStringIO.StringIO(e.read())
                gzip_decompressor = gzip.GzipFile(fileobj = data_compressed)
                error = gzip_decompressor.read()
            else:
                error = e.read()

            # Most likely a normal HTTP server error
            if e.headers.get('Content-Type') != 'application/octet-stream':
                raise ImporterError(str(e), local=False)

            import sys
            if hasattr(e, 'fp') and sys.version_info[0:2] == (2, 4):
                # We have to set recv to None, otherwise circular dependencies
                # leads to memory leaks, see http://bugs.python.org/issue1208304.
                # Seems to happen only on Python2.4
                e.fp.fp._sock.recv = None
                e.fp.fp.close()
                e.fp.close()

            try:
                data_decoded = cPickle.loads(error) # Read exception
            except cPickle.UnpicklingError, e:
                raise ImporterDeserializeError(error, traceback=error)
            raise ImporterError(data_decoded['msg'], local=False, traceback=data_decoded['traceback'])
        except urllib2.URLError, e:
            if hasattr(e, 'fp'):
                e.fp.fp._sock.recv = None
                e.fp.fp.close()
                e.fp.close()
            raise ImporterConnectError(str(e), traceback=traceback.format_exc())
        except cPickle.PickleError, e:
            raise ImporterSerializeError(str(e), traceback=traceback.format_exc())

