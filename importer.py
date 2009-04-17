""" Importer """

import traceback, os, cookielib, urllib2

COOKIE_FILE = 'cookies.lwp'

class ImporterError(Exception):
    """ Raised when something happen in Importer."""
    def __init__(self, msg, local=True, traceback=''):
        self.msg = msg.strip()
        self.local = local
        self.traceback = traceback.strip()

    def __repr__(self):
        return self.traceback or self.msg or 'Importer failed'
    __str__ = __repr__

class ImporterDeserializeError(ImporterError):
    pass

class ImporterSerializeError(ImporterError):
    pass

class ImporterConnectError(ImporterError):
    pass

class ImporterBase(object):
    """
        Base class for both ImporterModule and ImporterVariable.
        Provide call/get/set methods, relying on proper self.__objinst__ object.
        ImporterModule and ImporterVariable are in charge of creating the appropriate object.
    """
    def __init__(self, conf={}):
        self.__conf__ = conf
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
        try:
            return getattr(self.__objinst__, method)(*args, **kw)
        except Exception, e:
            raise ImporterError(str(e), traceback=traceback.format_exc())

    def get(self, attr):
        """ Getattr self.__objinst__ and returns. """
        try:
            return getattr(self.__objinst__, attr)
        except AttributeError, e:
            raise ImporterError(str(e), traceback=traceback.format_exc())

class ImporterModule(ImporterBase):
    def __init__(self, conf, module):
        """ Takes configuration from Importer() instance. """
        super(ImporterBase, self).__init__(conf)
        self.__mod__ = module
        try:
            # Just try to import it
            __import__(self.__mod__, {}, {}, [''])
        except ImportError, e:
            raise ImporterError(str(e), traceback=traceback.format_exc())

    def call(self, method, *args, **kw):
        """
            Override ImporterBase.call, but call it after.
            We need to do this, because if we store the module instance in __objinst__,
            when saving the session, module is tried to be pickled, and it fails.
        """
        try:
            self.__objinst__ = __import__(self.__mod__, {}, {}, [''])
        except ImportError, e:
            raise ImporterError(str(e), traceback=traceback.format_exc())
        ret = ImporterBase.call(self, method, *args, **kw)
        # We need to remove from the object, cause a lot of module are not "pickable"
        self.__objinst__ = None
        return ret

    def get(self, attr):
        """
        """
        try:
            return getattr(__import__(self.__mod__, {}, {}, ['']), attr)
        except ImportError, e:
            raise ImporterError(str(e), traceback=traceback.format_exc())

class ImporterVariable(ImporterBase):
    def __init__(self, conf, module, klass, *args, **kw):
        super(ImporterBase, self).__init__(conf)
        self.__mod__ = module
        self.__klass__ = klass
        try:
            #Instantiate the object
            if isinstance(self.__mod__, ImporterBase):
                self.__objinst__ = getattr(self.__mod__.__objinst__, klass)(*args, **kw)
            else:
                self.__objinst__ = getattr(__import__(self.__mod__, {}, {}, ['']), klass)(*args, **kw)
        except Exception, e:
            raise ImporterError(str(e), traceback=traceback.format_exc())

class Importer(ImporterBase):
    """
        Main class. Contains all modules.
        Call/get/set/instantiate always check if execution must be done remotely.
    """
    def __init__(self, file=COOKIE_FILE):
        super(Importer, self).__init__()
        self.__scope__ = {}
        self.__bound__ = None
        self.__file__ = file

    def call(self, module, method, *args, **kw):
        """
            Perform a call to module.method, passing the given *args, **kw.
            Override ImporterBase.call()
            Return: module.method return.
        """
        if 'distant_url' in self.__conf__.keys():
            mod = '.'.join((module, method))
            return self.__perform_distant__(mod, 'call', *args, **kw)
        self.__load_module__(module)
        return self.__scope__[module].call(method, *args, **kw)

    def get(self, module, attr):
        """ Retrieve an attr from the given module. """
        if 'distant_url' in self.__conf__.keys():
            mod = '.'.join((module, attr))
            return self.__perform_distant__(mod, 'get')
        self.__load_module__(module)
        return self.__scope__[module].get(attr)

    def instantiate(self, variable, module, klass, *args, **kw):
        """
            Add in the current scope a 'klass' instance from module.
            Similar to module.klass(*args, **kw).
            variable will be usable in the scope as others modules.
        """
        if 'distant_url' in self.__conf__.keys():
            mod = '.'.join((module, klass))
            return self.__perform_distant__(mod, 'instantiate', variable=variable, *args, **kw)
        if variable in self.__scope__.keys(): return
        if module in self.__scope__.keys():
            module = self.__scope__[module]
        self.__scope__[variable] = ImporterVariable(self.__conf__, module, klass, *args, **kw)

    def bound(self, bound):
        """ Bound Importer scope to "bound" list. """
        self.__bound__ = bound

    def __load_module__(self, module):
        """ Lookup for 'module' in scope, and if not present, create a ImporterModule object, and return it """
        # Module already in scope?
        if module not in self.__scope__.keys():
            first = module.split('/')[0]
            # Module out of bounds?
            if self.__bound__ and first not in self.__bound__:
                raise ImporterError('Module %s out of bounds' % first)
            # Add module to scope and import
            self.__scope__[module] = ImporterModule(self.__conf__, module)
        return self.__scope__[module]

    def __perform_distant__(self, module, type, *args, **kw):
        """ Perform the distant call. """
        import cPickle
        try:
            cj = cookielib.LWPCookieJar(self.__file__)
            if os.path.isfile(self.__file__):
                cj.load(self.__file__)
            opener = urllib2.build_opener(urllib2.HTTPCookieProcessor(cj))
            path = module.replace('.', '/') + '/' #Force trailing slash
            # Should be able to select encoder
            # TODO: Create a wrapper for cPickle, pickle in fallback
            data = cPickle.dumps({'type': type, 'args': args, 'kw': kw}, cPickle.HIGHEST_PROTOCOL)
            req = urllib2.Request(url=self.__conf__['distant_url'] + path, data=data)
            f = opener.open(req)
            data_read = f.read()
            if data_read == '': return None
            data_decoded = cPickle.loads(data_read)
            cj.save()
            return data_decoded
        except urllib2.HTTPError, e:
            data_decoded = cPickle.loads(e.read()) # Read exception
            raise ImporterError(data_decoded['msg'], local=False, traceback=data_decoded['traceback'])
        except urllib2.URLError, e:
            raise ImporterConnectError(str(e), traceback=traceback.format_exc())
        except cPickle.PickleError, e:
            raise ImporterSerializeError(str(e), traceback=traceback.format_exc())

