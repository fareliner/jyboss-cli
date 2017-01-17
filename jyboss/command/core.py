# Make coding more python3-ish
from __future__ import (absolute_import, division, print_function)

import inspect
import re
from abc import ABCMeta, abstractmethod
from copy import deepcopy

from jyboss.exceptions import *
from jyboss.logging import debug
from jyboss.context import ConfigurationChangeHandler, JyBossContext

try:
    from java.lang import IllegalArgumentException
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

__metaclass__ = type


class UndefinedType(object):
    pass


undefined = type(UndefinedType())

_expression_matcher = re.compile('^[\'\"]?(?:expression\s*[\'\"]?)?(\$\{.*\})[\'\"]*$')
_not_found_matcher = re.compile('WFLYCTL0030|WFLYCTL0216')


def unescape_keys(d):
    """
    Recursively proceses all dictionary keys and replaces '_' with '-' and '#' with '.' . Used to convert from YAML to
    jboss format.

    :param d: an item to convert

    :return: the escaped item
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
    Recursively proceses all dictionary keys and replaces '-' with '_' and '.' with '#' . Used to convert from YAML to
    jboss format.

    :param d: an item to convert

    :return: the escaped item
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
    Collapses json nodes that are dicts and have a key name of EXPRESSION_VALUE. This call can be used to
    :param obj: the object to check
    :return: the object or if expression value, the value of the object
    """
    if isinstance(obj, dict) and 'EXPRESSION_VALUE' in obj:
        return obj['EXPRESSION_VALUE']
    else:
        return obj


def converts_to_dmr(obj):
    """
    Converts a python dict or list to a jboss dmr string. This function can be used to generate complex jboss cli
    attribute arguments. See SecurityModule for example use.
    :param obj: {dict|list} - the dict or list object to turn into a dmr string
    :return: a dmr string that can be used in the cli commands
    """
    return None if obj is None else json.dumps(obj, separators=(',', '=>'))


def convert_to_dmr_params(args, allowable_attributes=None):
    """
    Converts a dictionary of parameters into a "string" list that can be used in a add method call on the jboss cli)
    :param args: {dict} - the argument key/value pair that needs to be turned into a param list
    :param allowable_attributes: {list[string]} - a list of attribute names that will be included in the args string
    :return: a string list of args formatted for the cli
    """
    result = ', '.join(
        ['%s=%s' % (k, convert_type(v)) for k, v in iteritems(args) if k in allowable_attributes])
    return result


def convert_type(obj):
    if isinstance(obj, basestring):
        m = _expression_matcher.match(obj)
        if m:
            return "\"%s\"" % m.group(1)
        else:
            return "\"%s\"" % obj  # FIXME this needs to be reviewed as it is normally not required to wrap strings in cli
    else:
        return json.dumps(obj)


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
            return json.loads(node_str)

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
        self.ARG_TYPE_DISPATCHER = {
            'UNDEFINED': self._cast_node_undefined,
            'INT': self._cast_node_int,
            'LONG': self._cast_node_long,
            'STRING': self._cast_node_string,
            'BOOLEAN': self._cast_node_boolean,
            'EXPRESSION': self._cast_node_expression
        }

    @staticmethod
    def _cast_node_undefined(n, v):
        if n is None or not n.isDefined or (n.type == n.type.UNDEFINED) or (
                        hasattr(n, 'type') and n.isDefined() and n.type == n.type.OBJECT):
            v_a = None
        else:
            raise ParameterError('Node has a undefined type but contains some value: %r' % n)
        # we have no means to work out what type this target value is supposed to have so just regurgitate
        return v_a, v

    @staticmethod
    def _cast_node_int(n, v):
        v_a = None if n is None else n.asInt()

        if v is None:
            v_t = None
        elif isinstance(v, int):
            v_t = int(v)
        else:
            try:
                v_t = _expression_matcher.match(v).group(1)
            except AttributeError:
                v_t = int(v)

        return v_a, v_t

    @staticmethod
    def _cast_node_long(n, v):
        v_a = None if n is None else n.asLong()

        if v is None:
            v_t = None
        elif isinstance(v, (int, long)):
            v_t = long(v)
        else:
            try:
                v_t = _expression_matcher.match(v).group(1)
            except AttributeError:
                v_t = long(v)

        return v_a, v_t

    @staticmethod
    def _cast_node_string(n, v):
        v_a = None if n is None else str(n.asString())

        if v is None:
            v_t = None
        else:
            try:
                v_t = _expression_matcher.match(v).group(1)
            except AttributeError:
                v_t = str(v)

        return v_a, v_t

    @staticmethod
    def _cast_node_boolean(n, v):
        v_a = None if n is None else n.asBoolean()

        if v is None:
            v_t = None
        elif type(v) is bool:
            v_t = v
        else:
            try:
                v_t = _expression_matcher.match(v).group(1)
            except AttributeError:
                v_t = bool(v)

        return v_a, v_t

    @staticmethod
    def _cast_node_expression(n, v):
        if n is None:
            v_a = None
        else:
            exp = n.asExpression()
            exp_val = exp.getExpressionString()
            v_a = str(exp_val)

        if v is None:
            v_t = None
        elif not isinstance(v, basestring):
            v_t = str(v)
        else:
            try:
                v_t = re.search('^(?:expression\s*)?(\$\{.*})$', v).group(1)
            except AttributeError:
                # TODO should probably use reflection on the node to work out what value the node can accept
                v_t = str(v)

        return v_a, v_t

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
                'action': 'updated',
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

            attr = parent_node.get(k_t)
            attr_type = 'UNDEFINED' if attr is None else str(attr.type)

            if attr_type not in self.ARG_TYPE_DISPATCHER:
                raise ParameterError('%s.sync_attr: synchronizing attribute %s of type %s is not supported' % (
                    self.__class__.__name__, k_t, attr_type))

            dp = self.ARG_TYPE_DISPATCHER[attr_type]
            v_a, v_t = dp(attr, v_t)
            debug('%s.sync_attr: param %s of type %s will be processed old[%r] new[%r]' % (
                self.__class__.__name__, k_t, attr_type, v_a, v_t))

            callback_args['name'] = k_t
            callback_args['old_value'] = v_a
            callback_args['new_value'] = v_t
            change = callback_handler(**callback_args)
            if change is not None:
                changes.append(change)

        return changes

    def _get_param(self, obj, name, default=undefined):
        """
        extracts a parameter from the provided configuration object
        :param obj {dict} - the object to check
        :param name {str} - the name of the param to get
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
