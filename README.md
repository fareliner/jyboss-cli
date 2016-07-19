# JyBoss - Manage JBoss from Jython

A python module that can be used with Jython to manage JBoss/Wildfly using the jboss scripting cli library.    

### Prerequisites

The target machine on which to run this module must have Java 8 and [Jython 2.7](http://www.jython.org/downloads.html) installed.

### Installation

Download the packaged [JyBoss module](https://github.com/fareliner/jyboss-cli/releases/latest) and install it with pip (make sure its the jython pip and not the python one installed with the typical OS).

Example `pip` Installation:

```sh
curl -L -o jyboss-0.0.6.tar.gz \
     https://github.com/fareliner/jyboss-cli/releases/download/v0.0.6/jyboss-0.0.6.tar.gz

pip install -U jyboss-0.0.6.tar.gz
```

### Usage

Given this module uses the JBoss CLI client package, one must make sure this jar is in the `CLASSPATH` or that the `JBOSS_HOME` variable is set in the environment.

Example Environment:

```sh
$ export JYTHON_HOME=/opt/jython-2.7.0
$ export JBOSS_HOME=/opt/jboss-eap-7.0
$ export PATH=$JYTHON_HOME/bin:$PATH
$ jython
>>>>
```

Start the server you like to manage, import the JyBoss, connect and hack away.


```py
#! /usr/bin/env jython
from jyboss import *

connect()
cd("/subsystem=datasources/data-source")
ls()
 [
    "ExampleDS",
    "ApimanDS"
 ]

cd("ExampleDS")

# you can use pretty much any of the commands possible on the normal cli
# only difference is, the output is proper json with field names are also valid in YAML
cmd(":read-resource(attributes-only=true, include-defaults=false)")
{
    "result": {
        "connectable": false,
        "track_statements": "NOWARN",
        "connection_url": "jdbc:h2:mem:test;DB_CLOSE_DELAY=-1;DB_CLOSE_ON_EXIT=FALSE",
        "share_prepared_statements": false,
         ...
     }
}

```

JyBoss also imports is also a Connection resource that can be used to handle the connection lifecycle using pythons with resource management (works like the file modules).

Another feature is the non-interactive mode of the session. In this mode printing to the terminal is suppressed and one can use the command and assign the result to variables - think ansible modules where the stdout must be a valid json response at the end of script execution.

```py
#! /usr/bin/env jython
import json
from jyboss import *

# connection takes the same arguments as the static connect() command
with standalone as conn:  
  # you now have a valid session
  # jyboss context is available and so is the actual Jboss CLI
  print "the jyboss context: ", conn.context
  print "the jyboss context: ", conn.jcli
  conn.context.noninteractive() # if you want to assign the dict/list values of the commands to variables

  cd("/")
  r = ls()
  print json.dumps(r, indent=4)

# your connection has now been closed, further reading I recommend
# http://effbot.org/zone/python-with-statement.htm
```
### Advanced Configuration

#### Syslog

On unix based hosts the jyboss will output internal log messages to syslog. Just copy the `ext/syslog.class` to `$JYTHON_HOME/Lib` and enable the local UDP receiver in your rsyslogd configuration file `/etc/rsyslog.conf`:

```properties
...
#### MODULES ####

# Provides UDP syslog reception
$ModLoad imudp
$UDPServerRun 514
...
```

Enable debug for `LOG_USER` location and `tail -f /var/log/messages` for log messages from the jyboss module. This is handy when using this module with ansible where logging to the console is not possible.


### Why You Ask?

A few weeks ago I tried to automate the installation and setup of JBoss AS with Ansible. Butchering standalone.xml files on initial deployment was not an option as the server xml files change as soon as one manages the server. I tried my luck with the jboss-cli but after reflecting on what this would look like in practice I quickly figured that this is not the right way to interact with the boss either. Simply getting facts on a datasource into ansible is a crazy commandline from hell.  

```yaml
# ansible task example which retrieves the datasource configuration of ExampleDS and makes the details available as facts.

- shell: >
    $JBOSS_HOME/bin/jboss-cli.sh -c --command="/subsystem=datasources/data-source=ExampleDS:read-resource(include-defaults=false, include-runtime=true, recursive=true)" | \
     sed -r -e 's/=>/:/g'
            -e 's/undefined/null/g'
            -e 's/"(type|value-type)"\s:\s([^"][A-Za-z0-9]*[^",])/"\1":"\2"/g'
            -e 's/"(.*)"\s?:\s?([^"][0-9.]*)L/"\1":\2/g'
            -e 's/:(\s?expression\s?)/:/g'
            -e  '/'\''?\[/!b;:a;/\]'\''?/bb;$!{N;ba};:b;s/('\''?\[.*)[ \t\n]+(.*\]'\''?)/\1\2/;tb' |
      jq 'def walk(f): . as $in | if type == "object" then reduce keys[] as $key ( {}; . + { ($key):  ($in[$key] | walk(f)) } ) | f elif type == "array" then map( walk(f) ) | f else f end; walk( if type == "object" then with_entries( .key |= sub( "-+"; "_") ) else . end )'
  register: example_ds_check

- set_fact:
   example_ds: "{{ example_ds_check.stdout | from_json }}"
```

So where from here? After some fiddling around with `jython`, the `jboss-cli-client.jar` and `ansible` I managed to produce a [custom ansible jython module](https://github.com/fareliner/ansible-custom-jython-module). Things got much more sophisticated much more quickly from the initial hack jython script that I decised to separate the ansible module from the jython wrapper.




### Example use of jboss-cli in Jython (the hard way)

Basic use of the CLI looks something like this:

```py
from org.jboss.as.cli.scriptsupport import CLI
cli = CLI.newInstance()
cli.connect()
cmd = cli.cmd("ls /")
if cmd.isSuccess():
    print cmd.getResponse()

```

### Controlling Output

For ansible we need to make sure to disable all system output (such as the connection information echoed by the underlying jline cli. Have to find a better way to get a handler to the jboss cli internal console.

```py
from java.lang import System
from java.io import PrintStream, OutputStream

class NoopOutputStream(OutputStream):
  def __init__(self):
    pass

  def write(self, b):
     pass

  def write(self, b, off, len):
     pass

  def close(self):
     pass

  def close(flush):
     pass


System.setOut(PrintStream(NoopOutputStream()))
System.setErr(PrintStream(NoopOutputStream()))

```

### Building a Release

This project uses the standard python setup mechanism. To build a distributable package simply use:

```sh
jython setup.py sdist --formats=gztar,zip
```
