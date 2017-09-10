# JyBoss - Manage JBoss from Jython

<p align="center">
  <a href="https://pypi.python.org/pypi/jyboss">
    <img src="https://img.shields.io/pypi/v/jyboss.svg" alt="pypi version">
  </a>
  <a href="https://github.com/fareliner/jyboss-cli/releases">
    <img src="https://img.shields.io/github/downloads/fareliner/jyboss-cli/total.svg" alt="jyboss downloads">
  </a>
  <a href="https://pypi.python.org/pypi/jyboss">
    <img src="https://img.shields.io/pypi/l/jyboss.svg" alt="jyboss license">
  </a>
</p>

A jython module to automate JBoss/Wildfly server configuration either via the jython shell or Ansible. The jyboss modules use the jboss scripting cli library.    

### Prerequisites

The target machine on which to run this module must have Java 8 and [Jython 2.7](http://www.jython.org/downloads.html) installed.

### Installation

The module can be installed using `pip` with Jython 2.7.x.

```sh
pip install -U jyboss
```

Alterantively one can also download the packaged [JyBoss module](https://github.com/fareliner/jyboss-cli/releases/latest) and install it with pip (ensure the pip in use is the jython pip and not the python version which is typically installed with the operating system).

### Limitations

Requires at least ansible 2.0.2.0 if running the module with `become_user` due to an ansible bug issue [#14348](https://github.com/ansible/ansible/issues/14348)).

### Usage

Given this module uses the JBoss CLI client package, one must make sure the `jboss-cli-client.jar` is in the `CLASSPATH` or that the `JBOSS_HOME` variable is set in the environment.

Example Environment:

```sh
$ export JYTHON_HOME=/opt/jython-2.7.1
$ export JBOSS_HOME=/opt/jboss-eap-7.0
$ export PATH=$JYTHON_HOME/bin:$PATH
$ jython
>>>>
```

Start the server you like to manage, import the JyBoss, connect and hack away.


```py
#! /usr/bin/env jython
from jyboss import *

embedded.connect()
cd('/subsystem=datasources/data-source')
ls()
'''
[
    "ExampleDS",
    "ApimanDS"
]
'''

cd('ExampleDS')

# you can use pretty much any of the commands possible on the normal cli
cmd(':read-resource(attributes-only=true, include-defaults=false)')
'''
{
    "response": {
        "connectable": false,
        "track_statements": "NOWARN",
        "connection_url": "jdbc:h2:mem:test;DB_CLOSE_DELAY=-1;DB_CLOSE_ON_EXIT=FALSE",
        "share_prepared_statements": false,
         ...
     }
}
'''

# to assign command output to variables, change to non-interactive mode 
embedded.context.interactive=False
# issue any kind of command and assign the result to a variable 
r = ls('/subsystem=datasources/data-source=ExampleDS')
print(r['children'])
'''
[u'connection-properties']
'''

# also ensure to disconnect when done (or use automatic resource management described below)
if embedded.context.is_connected():
    embedded.disconnect()
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
  # jyboss context is available and so is the actual JBoss CLI
  print "the jyboss connection context: ", conn.context
  print "the jboss jcli: ", conn.jcli

  # if you want to assign the dict/list values of the commands to variables
  conn.context.interactive = False
  cd('/')
  r = ls()
  print json.dumps(r, indent=4)

# your connection has now been closed, further reading I recommend
# http://effbot.org/zone/python-with-statement.htm
```
### Advanced Configuration

#### Syslog

As the jyboss module is primarily written to be used with ansible it cannot write output to the terminal console in noninteractive mode. To be able to still troubleshoot things, the module is configured to write to the user facility in syslog if it is present. Just add below line to the `/etc/rsyslog.conf` file and tail the `/var/log/user` file for useful information.

```sh
# Log any user messages
user.*                                                  /var/log/user
```


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

Running this cli as an Ansible module, we need to make sure to disable all system output. Ansible module execution will break if the output to stdout is not valid JSON. The JBoss cli is unfortunately very inconsistent and random information is echoed by the underlying jline cli. There are some delegation methods in the code but some are protected and even if butchered, some things still leak to stdout and stderr.

Below a simplified configuration to shut the cli up but the jyboss module also contains a set of Streams to redirect to syslog if available.

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

### Dev Notes

**Connect to a running JBoss Server**

```cmd
set "CLASSPATH=%JAVA_HOME%\lib\jconsole.jar"
set "CLASSPATH=%CLASSPATH%;%JAVA_HOME%\lib\tools.jar"
set "CLASSPATH=%CLASSPATH%;%cd%\tests\bin\client\jboss-cli-client.jar"
jconsole service:jmx:remote+http://wildfly.vagrant.v8:9990
```

**Configuring PyCharm**

Mark project root as source folder

Unit Test configuration

* Select Path : `{workspaces}/jyboss-cli/tests`
* Working Directory: `{workspaces}/jyboss-cli`
* Add context root to PYTHONPATH: unchecked
* Add sources root to PYTHONPATH: checked

**Running Keycloak Tests**

To run the keycloak unittest, one will have to download and unzip a keycloak server distribution and the wildfly adapter overlay according to the keycloak installation guide. then either set the `JBOSS_HOME` environment variable or update the `jboss-test.properties` file accordingly. 