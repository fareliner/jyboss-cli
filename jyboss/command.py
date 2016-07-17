# Make coding more python3-ish
from __future__ import (absolute_import, division, print_function)

import json

from jyboss.exceptions import *
from jyboss.logging import info, debug
from jyboss.context import ConnectionEventHandler

from java.lang import IllegalArgumentException


def _extract_errm(result):
    """

    :param result: the JBoss DMR result node
    :return: the error message string
    """
    if result is not None:
        nv = result.getResponse().get("failure-description")
    else:
        nv = None

    return None if nv is None else nv.asString()


class CommandHandler(ConnectionEventHandler):
    def __init__(self):
        self._connection = None

    def handle(self, connection):
        debug("%s.handle: cli is %s" % (self.__class__.__name__, repr(connection)))
        self._connection = connection

    def _cli(self):
        if self._connection is None or self._connection.jcli is None or not self._connection.jcli.is_connected():
            raise ContextError("%s: no session in progress, please connect()" % self.__class__.__name__)
        else:
            return self._connection.jcli

    def dmr_node_to_dict(self, node=None):
        from org.jboss.dmr import ModelNode
        if node is None:
            return None
        elif isinstance(node, ModelNode):
            # debug("node is a model node")
            return self._get_node_value(node)
        elif isinstance(node, basestring):
            # debug("node is a string node")
            return str(node)
        else:
            info("unable to process node: %s" % repr(node))

    def _get_node_value(self, node=None):
        from org.jboss.dmr import ModelType, ModelNode
        if node is None:
            return None
        elif not hasattr(node, 'type'):
            debug("-----------------------------------------------")
            debug("node has no type %s" % repr(node))
            debug("node dir %s" % repr(dir(node)))
            debug("node value %s" % repr(node.__str__))
            # symbolicNameNode = node.get(ModelConstants.SYMBOLIC_NAME)
            # debug("node sym %s" % symbolicNameNode.asString())

            debug("-----------------------------------------------")
        elif node is None or node.type is ModelType.UNDEFINED:
            return None
        elif node.type is ModelType.LIST:
            node_list = []
            for item in node.asList():
                sub_node = self.dmr_node_to_dict(item)
                node_list.append(sub_node)
            return node_list
        elif node.type is ModelType.DOUBLE:
            return node.asDouble()
        elif node.type is ModelType.INT:
            return node.asInt()
        elif node.type is ModelType.LONG:
            return node.asLong()
        elif node.type is ModelType.BIG_DECIMAL:
            return node.asBigDecimal()
        elif node.type is ModelType.BIG_INTEGER:
            return node.asBigInteger()
        elif node.type is ModelType.BOOLEAN:
            return node.asBoolean()
        elif node.type in [ModelType.STRING, ModelType.TYPE]:
            return node.asString()
        elif node.type is ModelType.PROPERTY:
            prop = node.asProperty()
            prop_name = prop.getName()
            prop_value = prop.getValue()
            if prop_value.isDefined():
                return {prop_name.replace('.', '_').replace('-', '_'): None}
            else:
                return {prop_name.replace('.', '_').replace('-', '_'): self._get_node_value(prop_value)}
        elif node.type is ModelType.BOOLEAN:
            return node.asBoolean()
        elif node.type is ModelType.EXPRESSION:
            return node.asString()
        elif node.type is ModelType.OBJECT:
            children = dict()
            o = node.asObject()
            for key in o.keys():
                child = o.get(key)
                children[key.replace('.', '_').replace('-', '_')] = self.dmr_node_to_dict(child)
            return children
        else:
            debug("reading model node type %s not supported" % node.type.toString())
            return None

    def _return_success(self, result, transform_cb=None, silent=False):
        """
        Return an executed response to the caller.

        :param result: the jboss result to transform
        :param transform_cb: a callback method that can transform the result prior to being returned
        :param silent: if the response
        :return: the transformed response
        """
        node = result.getResponse()
        response = self.dmr_node_to_dict(node)

        if transform_cb is not None:
            response = transform_cb(response)

        if not self._connection.context.is_interactive() or silent:
            if response is None:
                return {'response': 'ok'}
            elif 'result' in response:
                return {'response': response['result']}
            elif 'response' in response:
                return response
            else:
                return {'response': response}
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


class BasicCommandHandler(CommandHandler):
    def cd(self, path=".", silent=False):
        try:
            result = self._cli().cmd("cd %s" % path)
            if result.isSuccess():
                return self._return_success(result, silent=silent)
            else:
                raise OperationError(_extract_errm(result))
        except IllegalArgumentException as e:
            raise OperationError(e.getMessage())

    def ls(self, path=None, silent=False):
        result = self._cli().cmd("ls" if path is None else "ls %s" % path)
        if result.isSuccess():
            return self._return_success(result, BasicCommandHandler._ls_response_magic, silent=silent)
        else:
            errm = _extract_errm(result)
            if errm.find('WFLYCTL0062') != -1 and errm.find('WFLYCTL0216') != -1:
                # TODO snip errm?
                raise NotFoundError(errm)
            else:
                raise OperationError(errm)

    @staticmethod
    def _ls_response_magic(response):
        nr = None
        if response is not None and response.get("result") is not None:
            result = response.get("result")
            # if there are steps its attribute and children, else its just the result
            if isinstance(result, list):
                nr = result
            elif isinstance(result, dict):
                children_step = result.get("step_1")
                attr_step = result.get("step_2")
                nr = dict()
                if children_step is not None and children_step.get("result") is not None:
                    nr["children"] = children_step.get("result")
                if attr_step is not None and attr_step.get("result") is not None:
                    nr["attributes"] = attr_step.get("result")
            else:
                nr = dict(response=repr(result))
        return nr


class RawHandler(CommandHandler):
    def cmd(self, cmd, silent=False):
        result = self._cli().cmd("%s" % cmd)
        if result.isSuccess():
            return self._return_success(result, silent=silent)
        else:
            raise OperationError(_extract_errm(result))


class BatchHandler(CommandHandler):
    def start(self):
        self._cli().batch_start()

    def reset(self):
        self._cli().batch_reset()

    def run(self, silent=False):
        result = self._cli().cmd('run-batch')
        if result.isSuccess():
            return self._return_success(result, silent=silent)
        else:
            errm = _extract_errm(result)
            if errm.find('WFLYCTL0062') != -1 and errm.find('WFLYCTL0216') != -1:
                raise NotFoundError(errm)
            elif errm.find('WFLYCTL0062') != -1 and errm.find('WFLYCTL0212') != -1:
                raise DuplicateResourceError(errm)
            else:
                raise OperationError(errm)

    def add_cmd(self, batch_cmd):
        self._cli().batch_add_cmd(batch_cmd)

    def is_active(self):
        return self._cli().batch_is_active()
