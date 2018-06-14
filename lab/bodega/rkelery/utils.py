"""RKelery utilities."""
import json


def json_dump(o):
    """Dump to a standardized compact JSON representation."""
    return json.dumps(o, sort_keys=True, separators=(',', ':'))


def arguments_string(args, kwargs):
    """Create a representation of arguments resembling a function call."""
    arg_strings = [json_dump(arg) for arg in args]
    kwarg_strings = ['%s=%s' % (key, json_dump(val))
                     for (key, val) in kwargs.items()]
    return ', '.join(arg_strings + kwarg_strings)
