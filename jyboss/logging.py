from java.io import OutputStream

LOG_ERR = dict(code=3, name="ERROR")
LOG_WARNING = dict(code=4, name="WARN")
LOG_NOTICE = dict(code=5, name="NOTICE")
LOG_INFO = dict(code=6, name="INFO")
LOG_DEBUG = dict(code=7, name="DEBUG")

try:
    import syslog

    HAS_SYSLOG = True
except ImportError:
    HAS_SYSLOG = False


def _log(level, msg):
    logmod = 'ansible-%s' % __name__.split(".", 1)[0]
    if HAS_SYSLOG:
        syslog.openlog(str(logmod), 0, syslog.LOG_USER)
        syslog.syslog(level["code"], msg)
    else:
        print "[%s] %s: %s" % (level["name"], logmod, msg)


def error(msg):
    _log(LOG_ERR, msg)


def warn(msg):
    _log(LOG_WARNING, msg)


def info(msg):
    _log(LOG_INFO, msg)


def debug(msg):
    _log(LOG_DEBUG, msg)


class SyslogOutputStream(OutputStream):
    OUT = "out"
    ERR = "err"

    def __init__(self, type=OUT):
        self.type = type
        self.lines = []

    def write(self, b):
        if isinstance(b, int):
            pass
        elif isinstance(b, bytearray):
            pass

    def write(self, b, off, len):
        if off == 0 and len == 1:
            pass
        else:
            if b[len - 1] == 10: len = len - 1
            line = "".join(map(chr, b[off:len]))
            # also log to syslog as info or errors
            if HAS_SYSLOG:
                if self.type == SyslogOutputStream.OUT:
                    info(line)
                elif self.type == SyslogOutputStream.ERR:
                    error(line)
            self.lines.append(line)
