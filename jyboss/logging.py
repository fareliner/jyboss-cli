# Make coding more python3-ish
from __future__ import (absolute_import, division, print_function)

from synchronize import make_synchronized
from jyboss.exceptions import ContextError

try:
    from java.io import OutputStream
except ImportError as jpe:
    raise ContextError('Java packages are not available, please run this module with jython.', jpe)

try:
    from org.graylog2.syslog4j import SyslogConstants, Syslog

    HAS_SYSLOG = True
    syslog = Syslog.getInstance("unix_syslog")
    config = syslog.getConfig()
    config.setFacility(SyslogConstants.FACILITY_USER)
    config.setThrowExceptionOnWrite(False)
    config.setIdent(__name__.split(".", 1)[0])
    config.setIncludeIdentInMessageModifier(True)
    # localName ??
except ImportError:
    HAS_SYSLOG = False

__metaclass__ = type


def _log(level, msg):
    if HAS_SYSLOG:
        syslog.log(level, msg)


def emergency(msg):
    if HAS_SYSLOG:
        _log(SyslogConstants.LEVEL_EMERGENCY, msg)


def alert(msg):
    if HAS_SYSLOG:
        _log(SyslogConstants.LEVEL_ALERT, msg)


def critical(msg):
    if HAS_SYSLOG:
        _log(SyslogConstants.LEVEL_CRITICAL, msg)


def error(msg):
    if HAS_SYSLOG:
        _log(SyslogConstants.LEVEL_ERROR, msg)


def warn(msg):
    if HAS_SYSLOG:
        _log(SyslogConstants.LEVEL_WARN, msg)


def notice(msg):
    if HAS_SYSLOG:
        _log(SyslogConstants.LEVEL_NOTICE, msg)


def info(msg):
    if HAS_SYSLOG:
        _log(SyslogConstants.LEVEL_INFO, msg)


def debug(msg):
    if HAS_SYSLOG:
        _log(SyslogConstants.LEVEL_DEBUG, msg)


class SyslogOutputStream(OutputStream):
    OUT = "out"
    ERR = "err"

    def __init__(self, type=OUT):
        self.type = type
        self.lines = []

    def write(self, b):
        raise NotImplementedError('SyslogOutputStream.write(byte) is not implemented')

    # have to synchronise this otherwise access to the threads writing
    # to the capture array gets clobbered
    @make_synchronized
    def write(self, b, off, length):
        if off == 0 and length == 1:
            pass
        else:
            if b[length - 1] == 10:
                length -= 1
            line = "".join(map(chr, b[off:length]))
            # also log to syslog as info or errors
            if HAS_SYSLOG:
                if self.type == SyslogOutputStream.OUT:
                    info(line)
                elif self.type == SyslogOutputStream.ERR:
                    error(line)
            self.lines.append(line)
