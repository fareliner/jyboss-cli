from distutils.core import setup

setup(
    name='jyboss',
    version='0.2.1',
    url='https://github.com/fareliner/jyboss-cli',
    author='Niels Bertram',
    author_email='nielsbne@gmail.com',
    requires=['simplejson', 'PyYAML'],
    py_modules=['jyboss.context', 'jyboss.cli', 'jyboss.exceptions', 'jyboss.logging', 'jyboss.command.core',
                'jyboss.command.undertow', 'jyboss.command.extension', 'jyboss.command.security',
                'jyboss.command.keycloak', 'jyboss.command.ee', 'jyboss.command.datasources', 'jyboss.command.module',
                'jyboss.command.deployment', 'jyboss.command.jgroups', 'jyboss.command.infinispan',
                'jyboss.command.interface', 'jyboss.command.binding', 'jyboss.ansible']
)
