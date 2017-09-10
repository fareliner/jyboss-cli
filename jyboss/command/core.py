# Make coding more python3-ish
from __future__ import (absolute_import, division, print_function)

import inspect
import re
import collections
from abc import ABCMeta, abstractmethod
from copy import deepcopy

from jyboss.exceptions import *
from jyboss.logging import debug
from jyboss.context import ConfigurationChangeHandler, JyBossContext

try:
    # noinspection PyUnresolvedReferences
    from java.lang import IllegalArgumentException
    # noinspection PyUnresolvedReferences
    from java.util import NoSuchElementException
except ImportError as jpe:
    raise ContextError('Java packages are not available, please run this module with jython.', jpe)

try:
    import simplejson as json
except ImportError:
    import json

try:
    # Python 2
    unicode
except NameError:
    # Python 3
    unicode = str

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

# python 2 and 3 way of none type
NoneType = type(None)

__metaclass__ = type


class UndefinedType(object):
    pass


undefined = type(UndefinedType())

_expression_matcher = re.compile('^[\'\"]?(?:expression\s*)?[\'\"]?(.*\$\{.*\}[^\'\"]*)[\'\"]*$')
_not_found_matcher = re.compile('WFLYCTL0030|WFLYCTL0216')


def unescape_keys(d):
    """
    Recursively processes all dictionary keys and replaces '_' with '-' and '#' with '.' . This function is mainly used
    to convert from YAML to jboss format.

    :param d {object} - any type of item to unescape

    :return {object} - the unescaped object with keys all fixed up
    """
    if isinstance(d, dict):
        new = {}
        for k, v in iteritems(d):
            new[k.replace('_', '-')] = unescape_keys(v)
        return new
    elif isinstance(d, list):
        new = []
        for v in d:
            new.append(unescape_keys(v))
        return new
    else:
        return d


def escape_keys(d):
    """
    Recursively processes all dictionary keys and replaces '-' with '_' and '.' with '#' . This function is mainly used
    to convert from jboss to YAML format.

    :param d {object} - any type of item to escape to be valid in YAML

    :return {object} - the escaped object with keys valid for YAML output
    """
    if isinstance(d, dict):
        new = {}
        for k, v in iteritems(d):
            if k == 'EXPRESSION_VALUE':  # collapse
                new = v
            else:
                new[k.replace('-', '_')] = escape_keys(v)
        return new
    elif isinstance(d, list):
        new = []
        for v in d:
            new.append(escape_keys(v))
        return new
    else:
        return d


def expression_deserializer(obj):
    """
    Collapses json nodes that are dicts and have a key name of EXPRESSION_VALUE. This call can be used as an object
    handler on the json.dumps method to collapse any DMR specific expression objects.

    :param obj {object} - the dmr serialised object value to check
    :return {object} - the object or if expression value, the value of the object
    """
    if isinstance(obj, dict) and 'EXPRESSION_VALUE' in obj:
        return obj['EXPRESSION_VALUE']
    else:
        return obj


def converts_to_dmr(obj):
    """
    Converts a python dict or list to a jboss dmr string. This function can be used to generate complex jboss cli
    attribute arguments. See SecurityModule for example use.

    :param obj {dict|list} - The dict or list object to turn into a dmr string
    :return {string} - a DMR string that can be used in the cli commands
    """
    return None if obj is None else json.dumps(obj, separators=(',', '=>'))


def convert_to_dmr_params(args, allowable_attributes=None):
    """
    Converts a dictionary of parameters into a "string" list that can be used in a add method call on the jboss cli).

    :param args {dict} - the argument key/value pair that needs to be turned into a param list
    :param allowable_attributes {list[string]} - a list of attribute names that will be included in the args string
    :return: {string} - a string list of args formatted for the cli
    """
    result = ', '.join(
        ['%s=%s' % (k, convert_type(v)) for k, v in iteritems(args) if
         allowable_attributes is not None and k in allowable_attributes])
    return result


def convert_type(obj):
    """
    Convert an object into a JSON string representation.

    :param obj {object} - the object to convert
    :return {string} - the object as a JSON string
    """
    if isinstance(obj, basestring):
        m = _expression_matcher.match(obj)
        if m:
            return "\"%s\"" % m.group(1)
        else:
            return "\"%s\"" % obj
    if isinstance(obj, dict):
        return '[' + ', '.join(['%s=%s' % (k, convert_type(v)) for (k, v) in iteritems(obj)]) + ']'
    else:
        return json.dumps(obj)


def stringify_object(obj):
    """
    Stringify a python dict so we can better compare it to a JSON serialised DMR object.

    :param obj {object} - the object to stringify
    :return {object} - a stringyfied object of any sort
    """
    if isinstance(obj, dict):
        return dict((k, stringify_object(v)) for k, v in iteritems(obj))
    if isinstance(obj, list):
        return [stringify_object(v) for v in obj]
    if isinstance(obj, bool):
        return unicode(obj).lower()
    elif isinstance(obj, (int, long, basestring)):
        return unicode(obj)
    else:
        raise ParameterError('Cannot convert object value %s of type %s to unicode' % (obj, type(obj)))


def clean_python_value(obj, target_type_hint=None):
    if obj is None:
        return None
    elif isinstance(obj, (int, long, bool)):
        return obj if target_type_hint is None or target_type_hint == NoneType \
            else target_type_hint(obj)
    elif isinstance(obj, basestring):
        try:
            match = _expression_matcher.match(obj).group(1)  # why was expression parser using .search() ?
        except AttributeError:  # no expression wrapping to clean
            match = obj
        return match if target_type_hint is None or target_type_hint == NoneType \
            else target_type_hint(match)
    elif isinstance(obj, list):
        return list(clean_python_value(item) for item in obj)
    elif isinstance(obj, dict):
        return dict((k, clean_python_value(v)) for k, v in iteritems(obj))
    else:
        raise IllegalArgumentException('Value cannot be pre-processed for synching: %r' % obj)


def convert_dmr_to_python(n):
    # TODO barf if not a DMR node
    if n is None \
            or not n.isDefined() \
            or n.type == n.type.UNDEFINED:
        return None
    elif n.type == n.type.INT:
        return n.asInt()
    elif n.type == n.type.LONG:
        return n.asLong()
    elif n.type == n.type.STRING:
        return n.asString()
    elif n.type == n.type.BOOLEAN:
        return n.asBoolean()
    elif n.type == n.type.EXPRESSION:
        exp = n.asExpression()
        return exp.getExpressionString()
    elif n.type == n.type.LIST:
        v_list = []
        for _, v_list_node in enumerate(n.asList()):
            i_v = convert_dmr_to_python(v_list_node)
            v_list.append(i_v)
        return v_list
    elif n.type == n.type.OBJECT:
        props = n.asPropertyList()
        obj = {}
        for prop in props:
            obj[prop.name] = convert_dmr_to_python(prop.value)
        return obj
    else:
        raise IllegalArgumentException('Node type cannot be converted to a python value: %r' % n)


class CommandHandler(ConfigurationChangeHandler):
    def __init__(self, context=None):
        super(CommandHandler, self).__init__()
        if context is None:
            self.context = JyBossContext.instance()
        else:
            self.context = context
        self.escape_keys = escape_keys
        self.unescape_keys = unescape_keys
        self.converts_to_dmr = converts_to_dmr
        self.convert_to_dmr_params = convert_to_dmr_params

    def configuration_changed(self, change):
        debug('%s.handle: cli is %r' % (self.__class__.__name__, change))
        # TODO anything the command handler needs to do on change?

    def _cli(self):
        if not self.context.is_connected():
            raise ContextError('%s: no session in progress, please connect()' % self.__class__.__name__)
        else:
            return self.context.connection.jcli

    def start(self):
        """
        Start a batch command session
        """
        self._cli().batch_start()

    def reset(self):
        """
        Reset batch command session
        """
        self._cli().batch_reset()

    def cmd(self, cmd, silent=False):
        debug('%s.cmd(): %s' % (self.__class__.__name__, cmd))
        result = self._cli().cmd(cmd)
        if result.isSuccess():
            return self._return_success(result, silent=silent)
        else:
            errm = self._extract_errm(result)
            if errm is None:
                raise OperationError('Unknown error occurred executing: %s' % cmd)
            elif _not_found_matcher.match(errm) is not None:
                raise NotFoundError(errm)
            else:
                raise OperationError(errm)

    def cmd_dmr(self, cmd):
        result = self._cli().cmd('%s' % cmd)
        if result.isSuccess():
            r = result.getResponse()
            if r.has('result'):
                return r.get('result')
            else:
                return r
        else:
            errm = self._extract_errm(result)
            if errm is None:
                raise OperationError('Unknown error occurred executing: %s' % cmd)
            elif _not_found_matcher.match(errm) is not None:
                raise NotFoundError(errm)
            else:
                raise OperationError(errm)

    def dmr_to_python(self, node=None):
        if node is None:
            return None
        else:
            node_str = node.toJSONString(True)
            return json.loads(node_str, object_hook=expression_deserializer)

    def _as_value_pair(self, node):
        pass

    def _return_success(self, result, transform_cb=None, silent=False):
        """
        Return an executed response to the caller.

        :param result: the jboss result to transform
        :param transform_cb: a callback method that can transform the result prior to being returned
        :param silent: if the response
        :return: the transformed response
        """
        node = result.getResponse()
        response = self.dmr_to_python(node=node)

        if transform_cb is not None:
            response = transform_cb(response)

        if not self.context.interactive or silent:
            if response is None:
                return 'ok'
            elif 'result' in response:
                return response['result']
            elif 'response' in response:
                return response['response']
            else:
                return response
        else:
            if response is None:
                print('ok')
            elif isinstance(response, dict) and 'result' in response:
                print(json.dumps({'response': response['result']}, indent=4))
            elif isinstance(response, dict) or isinstance(response, list):
                print(json.dumps(response, indent=4))
            else:
                # TODO may want to cater for other types that arrive here ?
                print(repr(response))

    @staticmethod
    def _extract_errm(result, encoding='utf-8'):
        """

        :param result: the JBoss DMR result node
        :return: the error message string
        """
        if result is not None:
            nv = result.getResponse().get('failure-description')
        else:
            nv = None

        nv = nv.asString()
        return None if nv is None else nv.encode(encoding)

    def cd(self, path='.', silent=False):
        try:
            result = self._cli().cmd('cd %s' % path)
            if result.isSuccess():
                return self._return_success(result, silent=silent)
            else:
                raise OperationError(self._extract_errm(result))
        except IllegalArgumentException as e:
            raise OperationError(e.getMessage())

    def ls(self, path=None, silent=False):
        result = self._cli().cmd('ls' if path is None else 'ls %s' % path)
        if result.isSuccess():
            return self._return_success(result, _ls_response_magic, silent=silent)
        else:
            errm = self._extract_errm(result)
            if errm.find('WFLYCTL0062') != -1 and _not_found_matcher.match(errm) is not None:
                # TODO snip errm?
                raise NotFoundError(errm)
            else:
                raise OperationError(errm)

    def run(self, silent=False):
        """
        Run the batch command
        :param silent: if True disable output to stdout
        """
        result = self._cli().cmd('run-batch')
        if result.isSuccess():
            return self._return_success(result, silent=silent)
        else:
            errm = self._extract_errm(result)
            if errm.find('WFLYCTL0062') != -1 and _not_found_matcher.match(errm) is not None:
                raise NotFoundError(errm)
            elif errm.find('WFLYCTL0062') != -1 and errm.find('WFLYCTL0212') != -1:
                raise DuplicateResourceError(errm)
            else:
                raise OperationError(errm)

    def add_cmd(self, batch_cmd):
        """
        Add command to batch command list for execution
        :param batch_cmd: {str|list(str)} - the command to add to the list of batch commands
        """
        if not isinstance(batch_cmd, list):
            batch_cmd = [batch_cmd]

        for cmd in batch_cmd:
            self._cli().batch_add_cmd(cmd)

    def is_active(self):
        return self._cli().batch_is_active()


class ChangeObservable(object):
    """
    Observable class that will be used to process the command line and delegate processing to the actual handler
    """

    def __init__(self):
        self._observers = {}

    def process_instructions(self, instructions):
        actions = []

        local_instructions = deepcopy(instructions)

        for k in instructions.keys():
            instruction = instructions[k]
            if k == 'actions':
                if instruction is None:
                    pass
                elif isinstance(instruction, list):
                    for action in instruction:
                        for ka, va in action.items():
                            actions.append((ka, va))
                else:
                    raise ParameterError('actions must be a list of module instructions')

                # need to remove the key as part of elimination
                del local_instructions[k]

            elif k in self._observers:
                actions.append((k, instruction))
                # need to remove the key as part of elimination
                del local_instructions[k]

        return self._execute_action(local_instructions, actions)

    def _execute_action(self, configuration, actions):
        result = dict(changed=False)

        for key, action in actions:
            debug('jyboss ChangeObservable.process(%s)' % key)
            local_instruction = deepcopy(configuration)
            local_instruction[key] = action
            # notify all observers that can handle this command instruction
            for observer in self._observers.setdefault(key, []):
                changes = observer.apply(**local_instruction)
                if changes is not None:
                    result['changed'] = True
                    # I want result['action'] = key and changes appended to result['changes']
                    result.setdefault('changes', [])
                    result['changes'].append({
                        'module': key,
                        'executor': observer.__class__.__name__,
                        'changes': changes
                    })
                    # FIXME facter needs to return mapped key and no change result[key_replacement_name] = changes

        return result

    def register(self, observer):

        if observer is None:
            raise ParameterError('observer cannot be null')

        elif not hasattr(observer, 'apply'):
            raise NotImplementedError(
                '%s does not have an apply method' % observer.__class__.__name__)

        spec = inspect.getargspec(observer.apply)
        # by definition the first argument in the apply function is the configuration name that can be handled
        if len(spec.args) > 1 and spec.args[0] == 'self':
            key = spec.args[1]
            self._observers.setdefault(key, []).append(observer)
        else:
            raise ParameterError('%s.apply is not implemented correctly' % observer.__class__.__name__)


class ReloadCommandHandler(CommandHandler):
    def __init__(self, context=None):
        super(ReloadCommandHandler, self).__init__(context=context)

    def apply(self, reload=False, **kwargs):
        debug('%s:apply() %r' % (self.__class__.__name__, reload))
        if bool(reload):
            self.cmd('/:reload()')
            return ['reloaded']
        else:
            return None


class CliCmdHandler(CommandHandler):
    """
    A basic handler that will simply execute the cli string given and return. IF an error occurs it will fail
    throw an error and execution halts.

    Example:
        cmd: ''
    """

    def __init__(self, context=None):
        super(CliCmdHandler, self).__init__(context=context)

    def apply(self, cmd=None, **kwargs):
        debug('%s:apply() %r' % (self.__class__.__name__, reload))
        if cmd is not None:
            self.cmd(cmd)

        return None


# TODO review this class
class AttributeUpdateHandler(object):
    __metaclass__ = ABCMeta

    @abstractmethod
    def update(self, **kwargs):
        pass


class BaseJBossModule(CommandHandler):
    STATE_ABSENT = 'absent'
    STATE_PRESENT = 'present'

    def __init__(self, path, context=None):
        super(BaseJBossModule, self).__init__(context=context)
        self.path = path
        self.compareLists = lambda x, y: collections.Counter(x) == collections.Counter(y)

    def update_list(self, parent_path=None, name=None, old_value=None, new_value=None, **kwargs):
        change = None
        # check if both lists have the same content (ignoring order or elements)
        if not self.compareLists(old_value, new_value):
            # not the same, clear list and add all values of the new list
            self.cmd('%s:list-clear(name=%s)' % (parent_path, name))
            for i, v in enumerate(new_value):
                self.cmd('%s:list-add(name=%s,index=%s,value="%s")' % (parent_path, name, i, v))
            change = {
                'attribute': name,
                'action': 'update',
                'old_value': old_value,
                'new_value': new_value
            }

        return change

    def update_object(self, parent_path=None, name=None, old_value=None, new_value=None, **kwargs):
        change = None

        if new_value is None and old_value is not None:
            self.cmd('%s:undefine-attribute(name=%s)' % (parent_path, name))

            change = {
                'attribute': name,
                'action': 'delete',
                'old_value': old_value
            }
        elif new_value is not None and old_value is None:
            self.cmd('%s:write-attribute(name=%s, value=%s)' % (parent_path, name, convert_type(new_value)))

            change = {
                'attribute': name,
                'action': 'add',
                'old_value': old_value,
                'new_value': new_value
            }
        else:
            new_value = stringify_object(new_value)
            if new_value != old_value:
                self.cmd('%s:write-attribute(name=%s, value=%s)' % (parent_path, name, convert_type(new_value)))

                change = {
                    'attribute': name,
                    'action': 'update',
                    'old_value': old_value,
                    'new_value': new_value
                }
                # we can't compare objects here since we don't know that their types would be
                # best we can do is turn all fields into string and compare strings

        return change

    def update_attribute(self, parent_path=None, name=None, old_value=None, new_value=None, **kwargs):

        change = None

        if new_value is None and old_value is not None:
            self.cmd('%s:undefine-attribute(name=%s)' % (parent_path, name))

            change = {
                'attribute': name,
                'action': 'delete',
                'old_value': old_value
            }
        elif new_value is not None and new_value != old_value:
            self.cmd('%s:write-attribute(name=%s, value=%s)' % (parent_path, name, convert_type(new_value)))

            change = {
                'attribute': name,
                'action': 'add' if new_value is not None and old_value is None else 'update',
                'old_value': old_value,
                'new_value': new_value
            }

        return change

    def _sync_attributes(self, parent_node=None, parent_path=None, allowable_attributes=None, target_state=None,
                         callback_handler=None, callback_args=None):
        """
        Synchronise the attributes of a configuration object with allowable list of args

        :param parent_node: {ModelNode} - the parent dmr node containing the attributes to sync
        :param parent_path: {string} - the path of the node that needs its attributes synced
        :param allowable_attributes: {list(string)} - a list of attributes that can be updated
        :param target_state: {dict} - the requested target state to sync the parent to
        :param callback_handler: {function} - callback handler that can process the attribute updates
        :param callback_args: {dict} - any other arguments that need to be passed to the callback handler
        :return: changed and changes as list
        """
        if parent_node is None:
            raise ParameterError('A parent node must be provided.')

        # noinspection PyUnresolvedReferences
        from org.jboss.dmr import ModelNode

        if not isinstance(parent_node, ModelNode):
            raise ParameterError('A parent node is not a jboss dmr ModelNode.')

        if parent_path is None:
            raise ParameterError('A parent node path must be provided')

        if target_state is None:
            raise ParameterError('A target state must be provided for the node')

        if callback_handler is None:
            # bind the default callback handler
            callback_handler = self.update_attribute
        elif not inspect.ismethod(callback_handler):  # validate the passed in callback handler
            raise ParameterError('Provided callback_handler is not a function')

        if callback_args is None:
            callback_args = {}

        # add allowable attributes to the callback args if provided else they will be None and ignored by the callback
        callback_args['parent_path'] = parent_path

        changes = []

        for k_t, v_t in target_state.items():

            if allowable_attributes is not None and k_t not in allowable_attributes:
                raise NotImplementedError(
                    'Setting attribute %s is not supported by this module. Node path is %s' % (k_t, parent_path))

            if parent_node.has(k_t):
                attr = parent_node.require(k_t)
            else:
                raise ParameterError('%s.sync_attr: synchronizing attribute %s is not supported on jboss node %s' % (
                    self.__class__.__name__, k_t, parent_path))

            # convert the attribute value to a comparable python value
            try:
                v_a = convert_dmr_to_python(attr)
            except IllegalArgumentException:
                raise ParameterError('%s.sync_attr: synchronizing attribute %s of type %s is not supported' % (
                    self.__class__.__name__, k_t, attr.type))

            # also need to ensure the v_t is escaped/cleaned so we can compare
            v_t = clean_python_value(v_t, type(v_a))

            debug('%s.sync_attr: param %s of type %s will be processed old[%r] new[%r]' % (
                self.__class__.__name__, k_t, attr.type, v_a, v_t))

            callback_args['name'] = k_t
            callback_args['old_value'] = v_a
            callback_args['new_value'] = v_t

            # if either value is of type list, we need to engage a different callback handler as syncing list is
            # not as simple as updating single value attributes, if both are undefined we don't really care and
            # if their types differ, the caster would have already thrown a tantrum
            if isinstance(v_a, list) or isinstance(v_t, list):
                callback_handler = self.update_list

            if isinstance(v_a, dict) or isinstance(v_t, dict):
                callback_handler = self.update_object

            change = callback_handler(**callback_args)
            if change is not None:
                changes.append(change)

        return changes

    def _get_param(self, obj, name, default=undefined):
        """
        Extracts a parameter from the provided configuration object.

        :param obj {dict} - the object to check
        :param name {string} - the name of the param to get
        :param default {any} - will be returned if the object is None or the name is not in the obj
        :return {any} - whatever this param is set to
        """
        if obj is None:
            if default == undefined:
                raise ParameterError('%s: configuration is null' % self.__class__.__name__)
            else:
                return default
        elif name not in obj:
            if default == undefined:
                raise ParameterError('%s: no % s was provided' % (self.__class__.__name__, name))
            else:
                return default
        else:
            return obj[name]

    def read_attribute_dmr(self, resource_path, attribute_name):
        """
        Read a resource and return it as a dmr node

        :param resource_path {string} - the absolute or relative path to the attribute parent from which to read
        :param attribute_name {string} - the attribute name to read
        :return {ModelNode} - a dmr result node
        """
        cmd = '%s:read-attribute(name=%s)' % (resource_path, attribute_name)
        return self.cmd_dmr(cmd)

    def read_resource_dmr(self, resource_path, recursive=False):
        """
        Read a resource and return it as a dmr node

        :param resource_path: {string} - the absolute or relative path to the resource to read
        :param recursive: {bool} - show the resource content recursive
        :return: a dmr node
        """
        cmd = '%s:read-resource(recursive=%s)' % (resource_path, str(recursive).lower())
        return self.cmd_dmr(cmd)

    def read_resource(self, resource_path, recursive=False):
        """
        Read a resource and return it in python type format

        :param resource_path: {string} - the absolute or relative path to the resource to read
        :param recursive: {bool} - show the resource content recursive
        :return: a dmr node
        """
        node = self.read_resource_dmr(resource_path, recursive)
        return self.dmr_to_python(node=node)

    def _format_apply_param(self, arg):
        """
        Apply parameters can be either dicts of list of dicts, this method will simply turn it into a list.
        :param arg: the apply param to format
        :return: a list of apply parameters
        """
        if arg is None:
            result = None
        elif isinstance(arg, dict):
            result = [arg]
        elif isinstance(arg, list):
            result = arg
        else:
            raise ParameterError('%s provided to %s is not an allowable type' % (type(arg), self.__class__.__name__))

        return self.unescape_keys(result)

    @abstractmethod
    def apply(self, **kwargs):
        """
        Method to call with the module configuration to apply the module specific actions.
         :param kwargs {dict} the full configuration set, each module is responsible for picking out
         the bits that it needs
         :return {bool, list} returns a change flag and a list of changes that have been applied
        """
        pass


def _ls_response_magic(response):
    if response is None:
        return None
    elif not isinstance(response, dict):
        return response
    else:
        result = response.get('result', None)
        # if there are steps its attribute and children, else its just the result
        if result is None:
            return None
        elif isinstance(result, list):
            return result
        elif isinstance(result, dict):
            children_step = result.get('step-1')
            attr_step = result.get('step-2')
            nr = dict()
            if children_step is not None:
                nr['children'] = children_step.get('result', None)
            if attr_step is not None:
                nr['attributes'] = attr_step.get('result', None)
            return nr
        else:
            return dict(response=repr(result))
