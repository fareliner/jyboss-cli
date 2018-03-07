# Make coding more python3-ish
from __future__ import (absolute_import, division, print_function)

from jyboss.exceptions import ParameterError, NotFoundError
from jyboss.command.core import BaseJBossModule

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


class WeldModule(BaseJBossModule):

    def __init__(self, context=None):
        super(WeldModule, self).__init__(path='/subsystem=weld', context=context)

    def apply(self, weld=None, **kwargs):
        """
        Apply a CDI Weld subsystem operation:

        Example:

        weld:
          state: present

        """
        if not isinstance(weld, dict):
            raise ParameterError('%s provided to %s is not an allowable type' % (weld, self.__class__.__name__))

        changes = []

        state = self._get_param(weld, 'state')

        if state not in ['present', 'absent']:
            raise ParameterError('CDI Weld subsystem state is not one of [present|absent]')

        if state == 'present':
            changes += self.apply_present()
        elif state == 'absent':
            changes += self.apply_absent()

        return None if len(changes) < 1 else changes

    def apply_absent(self):
        try:
            self.cmd('%s:remove()' % self.path)
            return [{'subsystem': 'weld', 'action': 'delete'}]
        except NotFoundError:
            return []

    def apply_present(self):
        try:
            self.read_resource('%s' % self.path)
            return []
        except NotFoundError:
            self.cmd('%s:add()' % self.path)
            return [{'subsystem': 'weld', 'action': 'add'}]
