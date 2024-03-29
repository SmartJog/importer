# Generator


class Generator:

    mime_type = None

    def __init__(self):
        self._obj = None
        self._output = "None"

    def generate(self, obj):
        self._obj = obj

    def __str__(self):
        if self._obj:
            return self.generate(self._obj)
        return "<Generator %s>" % str(self._output)


class XmlGenerator(Generator):

    mime_type = "text/xml"

    def __init__(self):
        super().__init__()
        self._output = "xml"

    def generate(self, obj):
        super().generate(obj)
        # TODO


class SoapGenerator(Generator):

    mime_type = "application/soap+xml"

    def __init__(self):
        super().__init__()
        self._output = "soap"

    def generate(self, obj):
        super().generate(obj)
        # TODO


class JSONGenerator(Generator):

    mime_type = "application/json"

    def __init__(self):
        super().__init__()
        self._output = "json"

    def generate(self, obj):
        super().generate(obj)
        import json
        from django.core.serializers.json import DjangoJSONEncoder

        return json.dumps(obj, cls=DjangoJSONEncoder)


class PickleGenerator(Generator):

    mime_type = "application/pickle"

    def __init__(self):
        super().__init__()
        self._output = "pickle"

    def generate(self, obj):
        super().generate(obj)
        import pickle

        try:
            return pickle.dumps(obj, pickle.HIGHEST_PROTOCOL)
        except pickle.PickleError as _error:
            # cPickle failed, try pickle
            import pickle

            return pickle.dumps(obj, pickle.HIGHEST_PROTOCOL)


class MsgpackGenerator(Generator):

    mime_type = "application/x-msgpack"

    def __init__(self):
        super().__init__()
        self._output = "msgpack"

    def generate(self, obj):
        super().generate(obj)
        import msgpack

        # use_bin_type is required while we need to exchange with very old versions in production.
        # This should be removable once everyone uses Python3.
        return msgpack.packb(obj, use_bin_type=False, default=str)


class DefaultGenerator(Generator):

    mime_type = "text/plain"

    def __init__(self):
        super().__init__()
        self._output = "default"

    def generate(self, obj):
        super().generate(obj)
        return str(obj)


class GeneratorFactory:
    """GeneratorFactory handles Generator instances for the right output mode."""

    _output = {
        "xml": XmlGenerator,
        "soap": SoapGenerator,
        "json": JSONGenerator,
        "pickle": PickleGenerator,
        "default": DefaultGenerator,
        "msgpack": MsgpackGenerator,
    }

    @staticmethod
    def get(output):
        """
        Returns a valid Generator instance for the given output mode.
        If the output mode is invalid, returns a DefaultGenerator.
        """

        out = "default"
        if output in GeneratorFactory._output:
            out = output
        return GeneratorFactory._output[out]()
