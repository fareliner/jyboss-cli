# Make coding more python3-ish
from __future__ import (absolute_import, division, print_function)

import sys
import os
import types
import re
from collections import OrderedDict

import datetime

from itertools import repeat, chain

try:
    # Python 2
    from itertools import imap
except ImportError:
    # Python 3
    imap = map

try:
    dict.iteritems
except AttributeError:
    # Python 3
    def iteritems(d):
        return d.items()
else:
    # Python 2
    def iteritems(d):
        return d.iteritems()

try:
    # Python 2
    basestring
except NameError:
    # Python 3
    basestring = str

try:
    # Python 2
    unicode
except NameError:
    # Python 3
    unicode = str

# Python2 & 3 way to get NoneType
NoneType = type(None)

try:
    NUMBERTYPES = (int, long, float)
except NameError:
    # Python 3
    NUMBERTYPES = (int, float)

try:
    from collections import Sequence, Mapping
except ImportError:
    # python2.5
    Sequence = (list, tuple)
    Mapping = (dict,)

try:
    from collections.abc import KeysView

    SEQUENCETYPE = (Sequence, KeysView)
except:
    SEQUENCETYPE = Sequence

try:
    import json

    # Detect the python-json library which is incompatible
    # Look for simplejson if that's the case
    try:
        if not isinstance(json.loads, types.FunctionType) or not isinstance(json.dumps, types.FunctionType):
            raise ImportError
    except AttributeError:
        raise ImportError
except ImportError:
    try:
        import simplejson as json
    except ImportError:
        print(
            '\n{"msg": "Error: ansible requires the stdlib json or simplejson module, neither was found!", "failed": true}')
        sys.exit(1)
    except SyntaxError:
        print(
            '\n{"msg": "SyntaxError: probably due to installed simplejson being for a different python version", "failed": true}')
        sys.exit(1)

try:
    from ast import literal_eval
except ImportError:
    # a replacement for literal_eval that works with python 2.4. from:
    # https://mail.python.org/pipermail/python-list/2009-September/551880.html
    # which is essentially a cut/paste from an earlier (2.6) version of python's
    # ast.py
    from compiler import ast, parse


    def literal_eval(node_or_string):
        """
        Safely evaluate an expression node or a string containing a Python
        expression.  The string or node provided may only consist of the  following
        Python literal structures: strings, numbers, tuples, lists, dicts,  booleans,
        and None.
        """
        _safe_names = {'None': None, 'True': True, 'False': False}
        if isinstance(node_or_string, basestring):
            node_or_string = parse(node_or_string, mode='eval')
        if isinstance(node_or_string, ast.Expression):
            node_or_string = node_or_string.node

        def _convert(node):
            if isinstance(node, ast.Const) and isinstance(node.value, (basestring, int, float, long, complex)):
                return node.value
            elif isinstance(node, ast.Tuple):
                return tuple(map(_convert, node.nodes))
            elif isinstance(node, ast.List):
                return list(map(_convert, node.nodes))
            elif isinstance(node, ast.Dict):
                return dict((_convert(k), _convert(v)) for k, v in node.items())
            elif isinstance(node, ast.Name):
                if node.name in _safe_names:
                    return _safe_names[node.name]
            elif isinstance(node, ast.UnarySub):
                return -_convert(node.expr)
            raise ValueError('malformed string')

        return _convert(node_or_string)

__metaclass__ = type

PY2 = sys.version_info[0] == 2
PY3 = sys.version_info[0] == 3

_literal_eval = literal_eval


def get_exception():
    """Get the current exception.
    This code needs to work on Python 2.4 through 3.x, so we cannot use
    "except Exception, e:" (SyntaxError on Python 3.x) nor
    "except Exception as e:" (SyntaxError on Python 2.4-2.5).
    Instead we must use ::
        except Exception:
            e = get_exception()
    """
    return sys.exc_info()[1]


BOOLEANS_TRUE = ['yes', 'on', '1', 'true', 1, True]
BOOLEANS_FALSE = ['no', 'off', '0', 'false', 0, False]

# Internal global holding passed in params.  This is consulted in case
# multiple AnsibleModules are created.  Otherwise each AnsibleModule would
# attempt to read from stdin.  Other code should not use this directly as it
# is an internal implementation detail
_ANSIBLE_ARGS = None


def json_dict_unicode_to_bytes(d, encoding='utf-8'):
    """ Recursively convert dict keys and values to byte str

        Specialized for json return because this only handles, lists, tuples,
        and dict container types (the containers that the json module returns)
    """

    if isinstance(d, unicode):
        return d.encode(encoding)
    elif isinstance(d, dict):
        return OrderedDict(imap(json_dict_unicode_to_bytes, iteritems(d), repeat(encoding)))
    elif isinstance(d, list):
        return list(imap(json_dict_unicode_to_bytes, d, repeat(encoding)))
    elif isinstance(d, tuple):
        return tuple(imap(json_dict_unicode_to_bytes, d, repeat(encoding)))
    else:
        return d


def json_dict_bytes_to_unicode(d, encoding='utf-8'):
    """ Recursively convert dict keys and values to byte str

        Specialized for json return because this only handles, lists, tuples,
        and dict container types (the containers that the json module returns)
    """

    if isinstance(d, bytes):
        return unicode(d, encoding)
    elif isinstance(d, dict):
        return dict(imap(json_dict_bytes_to_unicode, iteritems(d), repeat(encoding)))
    elif isinstance(d, list):
        return list(imap(json_dict_bytes_to_unicode, d, repeat(encoding)))
    elif isinstance(d, tuple):
        return tuple(imap(json_dict_bytes_to_unicode, d, repeat(encoding)))
    else:
        return d


def return_values(obj):
    """ Return stringified values from datastructures. For use with removing
    sensitive values pre-jsonification."""
    if isinstance(obj, basestring):
        if obj:
            if isinstance(obj, bytes):
                yield obj
            else:
                # Unicode objects should all convert to utf-8
                # (still must deal with surrogateescape on python3)
                yield obj.encode('utf-8')
        return
    elif isinstance(obj, SEQUENCETYPE):
        for element in obj:
            for subelement in return_values(element):
                yield subelement
    elif isinstance(obj, Mapping):
        for element in obj.items():
            for subelement in return_values(element[1]):
                yield subelement
    elif isinstance(obj, (bool, NoneType)):
        # This must come before int because bools are also ints
        return
    elif isinstance(obj, NUMBERTYPES):
        yield str(obj)
    else:
        raise TypeError('Unknown parameter type: %s, %s' % (type(obj), obj))


def remove_values(value, no_log_strings):
    """ Remove strings in no_log_strings from value.  If value is a container
    type, then remove a lot more"""
    if isinstance(value, basestring):
        if isinstance(value, unicode):
            # This should work everywhere on python2. Need to check
            # surrogateescape on python3
            bytes_value = value.encode('utf-8')
            value_is_unicode = True
        else:
            bytes_value = value
            value_is_unicode = False
        if bytes_value in no_log_strings:
            return 'VALUE_SPECIFIED_IN_NO_LOG_PARAMETER'
        for omit_me in no_log_strings:
            bytes_value = bytes_value.replace(omit_me, '*' * 8)
        if value_is_unicode:
            value = unicode(bytes_value, 'utf-8', errors='replace')
        else:
            value = bytes_value
    elif isinstance(value, SEQUENCETYPE):
        return [remove_values(elem, no_log_strings) for elem in value]
    elif isinstance(value, Mapping):
        return dict((k, remove_values(v, no_log_strings)) for k, v in value.items())
    elif isinstance(value, tuple(chain(NUMBERTYPES, (bool, NoneType)))):
        stringy_value = str(value)
        if stringy_value in no_log_strings:
            return 'VALUE_SPECIFIED_IN_NO_LOG_PARAMETER'
        for omit_me in no_log_strings:
            if omit_me in stringy_value:
                return 'VALUE_SPECIFIED_IN_NO_LOG_PARAMETER'
    elif isinstance(value, datetime.datetime):
        value = value.isoformat()
    else:
        raise TypeError('Value of unknown type: %s, %s' % (type(value), value))
    return value


def _load_params():
    """ read the modules parameters and store them globally """
    global _ANSIBLE_ARGS

    buff = None
    if _ANSIBLE_ARGS is not None:
        buff = _ANSIBLE_ARGS
    else:
        if len(sys.argv) > 1:
            if os.path.isfile(sys.argv[1]):
                fd = open(sys.argv[1], 'rb')
                buff = fd.read()
                fd.close()
            else:
                buff = sys.argv[1]
        else:
            print(
                '\n{"msg": "Error: Module was not supplied with arguments in a JSON file. Unable to figure out what parameters were passed", "failed": true}')
            sys.exit(1)

        _ANSIBLE_ARGS = buff

    try:
        params = json.loads(buff.decode('utf-8'), object_pairs_hook=OrderedDict)
    except ValueError:
        # This helper used too early for fail_json to work.
        print(
            '\n{"msg": "Error: Module unable to decode valid JSON on stdin.  Unable to figure out what parameters were passed", "failed": true}')
        sys.exit(1)

    if PY2:
        params = json_dict_unicode_to_bytes(params)

    return params


class AnsibleModule(object):
    """simple implementation of the python module util shipped with ansible"""

    def __init__(self, argument_spec, bypass_checks=False, required_together=None, required_one_of=None,
                 required_if=None):
        self.argument_spec = argument_spec

        self._load_params()

        self._CHECK_ARGUMENT_TYPES_DISPATCHER = {
            'str': self._check_type_str,
            'list': self._check_type_list,
            'dict': self._check_type_dict,
            'bool': self._check_type_bool,
            'int': self._check_type_int,
            'float': self._check_type_float,
            'path': self._check_type_path,
            'raw': self._check_type_raw,
            'jsonarg': self._check_type_jsonarg,
        }
        if not bypass_checks:
            self._check_required_arguments()
            self._check_argument_types()
            self._check_argument_values()
            self._check_required_together(required_together)
            self._check_required_one_of(required_one_of)
            self._check_required_if(required_if)

        # Save parameter values that should never be logged
        self.no_log_values = set()

        # Use the argspec to determine which args are no_log
        for arg_name, arg_opts in self.argument_spec.items():
            if arg_opts.get('no_log', False):
                # Find the value for the no_log'd param
                no_log_object = self.params.get(arg_name, None)
                if no_log_object:
                    self.no_log_values.update(return_values(no_log_object))

        self.pretty_print = self.params.get('pretty', False)

    def fail_on_missing_params(self, required_params=None):
        """ This is for checking for required params when we can not check via argspec because we
        need more information than is simply given in the argspec.
        """
        if not required_params:
            return
        missing_params = []
        for required_param in required_params:
            if not self.params.get(required_param):
                missing_params.append(required_param)
        if missing_params:
            self.fail_json(msg="missing required arguments: %s" % ','.join(missing_params))

    def fail_json(self, **kwargs):
        """ return from the module, with an error message """
        assert 'msg' in kwargs, "implementation error -- msg to explain the error is required"
        kwargs['failed'] = True
        if 'invocation' not in kwargs:
            kwargs['invocation'] = {'module_args': self.params, 'interpreter': sys.executable}
        kwargs = remove_values(kwargs, self.no_log_values)
        # REVIEW self.do_cleanup_files()
        print('\n%s' % self.jsonify(kwargs))
        sys.exit(1)

    def exit_json(self, **kwargs):
        """ return from the module, without error """
        # REVIEW self.add_path_info(kwargs)
        if not 'changed' in kwargs:
            kwargs['changed'] = False
        if 'invocation' not in kwargs:
            kwargs['invocation'] = {'module_args': self.params, 'interpreter': sys.executable}
        kwargs = remove_values(kwargs, self.no_log_values)
        # REVIEW self.do_cleanup_files()
        print('\n%s' % self.jsonify(kwargs))
        sys.exit(0)

    def jsonify(self, data):
        for encoding in ("utf-8", "latin-1"):
            try:
                pretty = dict()
                if self.pretty_print:
                    pretty['indent'] = 4
                return json.dumps(data, encoding=encoding, **pretty)
            # Old systems using old simplejson module does not support encoding keyword.
            except TypeError:
                try:
                    new_data = json_dict_bytes_to_unicode(data, encoding=encoding)
                except UnicodeDecodeError:
                    continue
                return json.dumps(new_data)
            except UnicodeDecodeError:
                continue
        self.fail_json(msg='Invalid unicode encoding encountered')

    def boolean(self, arg):
        """ return a bool for the arg """
        if arg is None or type(arg) == bool:
            return arg
        if isinstance(arg, basestring):
            arg = arg.lower()
        if arg in BOOLEANS_TRUE:
            return True
        elif arg in BOOLEANS_FALSE:
            return False
        else:
            self.fail_json(msg='Boolean %s not in either boolean list' % arg)

    @staticmethod
    def safe_eval(str, locals=None, include_exceptions=False):

        # do not allow method calls to modules
        if not isinstance(str, basestring):
            # already templated to a datastructure, perhaps?
            if include_exceptions:
                return (str, None)
            return str
        if re.search(r'\w\.\w+\(', str):
            if include_exceptions:
                return (str, None)
            return str
        # do not allow imports
        if re.search(r'import \w+', str):
            if include_exceptions:
                return (str, None)
            return str
        try:
            result = literal_eval(str)
            if include_exceptions:
                return (result, None)
            else:
                return result
        except Exception:
            e = get_exception()
            if include_exceptions:
                return (str, e)
            return str

    @staticmethod
    def _check_type_str(value):
        if isinstance(value, basestring):
            return value
        # Note: This could throw a unicode error if value's __str__() method
        # returns non-ascii.  Have to port utils.to_bytes() if that happens
        return str(value)

    @staticmethod
    def _check_type_list(value):
        if isinstance(value, list):
            return value

        if isinstance(value, basestring):
            return value.split(",")
        elif isinstance(value, int) or isinstance(value, float):
            return [str(value)]

        raise TypeError('%s cannot be converted to a list' % type(value))

    def _check_type_dict(self, value):
        if isinstance(value, dict):
            return value

        if isinstance(value, basestring):
            if value.startswith("{"):
                try:
                    return json.loads(value)
                except:
                    (result, exc) = self.safe_eval(value, dict(), include_exceptions=True)
                    if exc is not None:
                        raise TypeError('unable to evaluate string as dictionary')
                    return result
            elif '=' in value:
                fields = []
                field_buffer = []
                in_quote = False
                in_escape = False
                for c in value.strip():
                    if in_escape:
                        field_buffer.append(c)
                        in_escape = False
                    elif c == '\\':
                        in_escape = True
                    elif not in_quote and c in ('\'', '"'):
                        in_quote = c
                    elif in_quote and in_quote == c:
                        in_quote = False
                    elif not in_quote and c in (',', ' '):
                        field = ''.join(field_buffer)
                        if field:
                            fields.append(field)
                        field_buffer = []
                    else:
                        field_buffer.append(c)

                field = ''.join(field_buffer)
                if field:
                    fields.append(field)
                return dict(x.split("=", 1) for x in fields)
            else:
                raise TypeError("dictionary requested, could not parse JSON or key=value")

        raise TypeError('%s cannot be converted to a dict' % type(value))

    def _check_type_bool(self, value):
        if isinstance(value, bool):
            return value

        if isinstance(value, basestring) or isinstance(value, int):
            return self.boolean(value)

        raise TypeError('%s cannot be converted to a bool' % type(value))

    @staticmethod
    def _check_type_int(value):
        if isinstance(value, int):
            return value

        if isinstance(value, basestring):
            return int(value)

        raise TypeError('%s cannot be converted to an int' % type(value))

    @staticmethod
    def _check_type_float(value):
        if isinstance(value, float):
            return value

        if isinstance(value, basestring):
            return float(value)

        raise TypeError('%s cannot be converted to a float' % type(value))

    def _check_type_path(self, value):
        value = self._check_type_str(value)
        return os.path.expanduser(os.path.expandvars(value))

    @staticmethod
    def _check_type_jsonarg(value):
        # Return a jsonified string.  Sometimes the controller turns a json
        # string into a dict/list so transform it back into json here
        if isinstance(value, (unicode, bytes)):
            return value.strip()
        else:
            if isinstance(value(list, tuple, dict)):
                return json.dumps(value)
        raise TypeError('%s cannot be converted to a json string' % type(value))

    @staticmethod
    def _check_type_raw(value):
        return value

    def _check_required_arguments(self):
        """ ensure all required arguments are present """
        missing = []
        for (k, v) in self.argument_spec.items():
            required = v.get('required', False)
            if required and k not in self.params:
                missing.append(k)
        if len(missing) > 0:
            self.fail_json(msg="missing required arguments: %s" % ",".join(missing))

    def _check_argument_types(self):
        """ ensure all arguments have the requested type """
        for (k, v) in self.argument_spec.items():
            wanted = v.get('type', None)

            # only if we have a wanted field we rampage and fiddle with the value
            # otherwise it would convert items we want to morph (e.g. param can be a list or single value)
            if wanted is None or k not in self.params or self.params[k] is None:
                continue

            value = self.params[k]

            try:
                type_checker = self._CHECK_ARGUMENT_TYPES_DISPATCHER[wanted]
            except KeyError:
                self.fail_json(msg="implementation error: unknown type %s requested for %s" % (wanted, k))
            try:
                self.params[k] = type_checker(value)
            except (TypeError, ValueError):
                self.fail_json(
                    msg="argument %s is of type %s and we were unable to convert to %s" % (k, type(value), wanted))

    def _check_argument_values(self):
        ''' ensure all arguments have the requested values, and there are no stray arguments '''
        for (k, v) in self.argument_spec.items():
            choices = v.get('choices', None)
            if choices is None:
                continue
            if isinstance(choices, SEQUENCETYPE):
                if k in self.params:
                    if self.params[k] not in choices:
                        choices_str = ",".join([str(c) for c in choices])
                        msg = "value of %s must be one of: %s, got: %s" % (k, choices_str, self.params[k])
                        self.fail_json(msg=msg)
            else:
                self.fail_json(msg="internal error: choices for argument %s are not iterable: %s" % (k, choices))

    def _count_terms(self, check):
        count = 0
        for term in check:
            if term in self.params:
                count += 1
        return count

    def _check_required_if(self, spec):
        """ ensure that parameters which conditionally required are present """
        if spec is None:
            return
        for (key, val, requirements) in spec:
            missing = []
            if key in self.params and self.params[key] == val:
                for check in requirements:
                    count = self._count_terms((check,))
                    if count == 0:
                        missing.append(check)
            if len(missing) > 0:
                self.fail_json(msg="%s is %s but the following are missing: %s" % (key, val, ','.join(missing)))

    def _check_required_together(self, spec):
        if spec is None:
            return
        for check in spec:
            counts = [self._count_terms([field]) for field in check]
            non_zero = [c for c in counts if c > 0]
            if len(non_zero) > 0:
                if 0 in counts:
                    self.fail_json(msg="parameters are required together: %s" % (check,))

    def _check_required_one_of(self, spec):
        if spec is None:
            return
        for check in spec:
            count = self._count_terms(check)
            if count == 0:
                self.fail_json(msg="one of the following is required: %s" % ','.join(check))

    def _check_mutually_exclusive(self, spec):
        if spec is None:
            return
        for check in spec:
            count = self._count_terms(check)
            if count > 1:
                self.fail_json(msg="parameters are mutually exclusive: %s" % (check,))

    def _load_params(self):
        ''' read the input and set the params attribute.

        This method is for backwards compatibility.  The guts of the function
        were moved out in 2.1 so that custom modules could read the parameters.
        '''
        # debug overrides to read args from file or cmdline
        self.params = _load_params()
