from distutils.core import setup

setup(
    name='jyboss',
    version='0.0.7',
    url='https://github.com/fareliner/jyboss-cli',
    author='Niels Bertram',
    author_email='nielsbne@gmail.com',
    requires=['simplejson'],
    py_modules=['jyboss.context', 'jyboss.cli', 'jyboss.exceptions', 'jyboss.logging', 'jyboss.command.core',
                'jyboss.command.undertow', 'jyboss.command.extension', 'jyboss.command.security',
                'jyboss.command.keycloak', 'jyboss.ansible']
)
