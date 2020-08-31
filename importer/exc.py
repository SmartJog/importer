# -*- coding: utf-8 -*-


class ImporterError(Exception):
    """ Raised when something happen in Importer."""

    def __init__(self, msg, local=True, traceback=""):
        self.msg = msg.strip()
        self.local = local
        self.traceback = traceback.strip()

    def __repr__(self):
        return self.traceback or self.msg or "Importer failed"

    __str__ = __repr__


class ImporterDeserializeError(ImporterError):
    """ Error when deserializing from exporter. """

    pass


class ImporterSerializeError(ImporterError):
    """ Error when serializing. """

    pass


class ImporterConnectError(ImporterError):
    """ Error when connecting to remote exporter. """

    pass
