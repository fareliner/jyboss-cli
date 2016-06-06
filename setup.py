from distutils.core import setup

setup(
    name='jyboss',
    version='0.0.2',
    url="https://github.com/bertramn/jyboss-cli",
    author="Niels Bertram",
    author_email="nielsbne@gmail.com",
    py_modules=['jyboss.context', 'jyboss.exceptions', 'jyboss.logging', 'jyboss.command']
)
