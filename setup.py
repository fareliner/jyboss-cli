#!/usr/bin/env jython

#
# Licensed to the Apache Software Foundation (ASF) under one
# or more contributor license agreements. See the NOTICE file
# distributed with this work for additional information
# regarding copyright ownership. The ASF licenses this file
# to you under the Apache License, Version 2.0 (the
# "License"); you may not use this file except in compliance
# with the License. You may obtain a copy of the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing,
# software distributed under the License is distributed on an
# "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY
# KIND, either express or implied. See the License for the
# specific language governing permissions and limitations
# under the License.
#

import sys

try:
    from setuptools import setup, Extension
except:
    from distutils.core import setup, Extension

setup(
    name='jyboss',

    version='0.2.5',

    url='https://github.com/fareliner/jyboss-cli',

    author='Niels Bertram',
    author_email='nielsbne@gmail.com',

    description='Jython CLI for JBoss Application Server',

    license='Apache License 2.0',

    # See https://pypi.python.org/pypi?%3Aaction=list_classifiers
    classifiers=[
        # How mature is this project? Common values are
        #   3 - Alpha
        #   4 - Beta
        #   5 - Production/Stable
        'Development Status :: 3 - Alpha',

        # Indicate who your project is intended for
        'Intended Audience :: Developers',
        'Topic :: Software Development :: Build Tools',
        'Topic :: System :: Software Distribution',
        'Topic :: System :: Systems Administration',

        # released under Apache 2 License
        'License :: OSI Approved :: Apache Software License',

        # the language used by the author
        'Natural Language :: English',

        # Specify the Python versions you support here. In particular, ensure
        # that you indicate whether you support Python 2, Python 3 or both.
        'Programming Language :: Python :: 2',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.3',
        'Programming Language :: Python :: 3.4',
        'Programming Language :: Python :: 3.5',

        # only works on Jython
        'Programming Language :: Python :: Implementation :: Jython'
    ],

    keywords='jboss wildfly development cli',

    # only have 2 dependencies
    install_requires=[
        'simplejson',
        'PyYAML'
    ],

    # prepare for testing with nose
    test_suite='nose.collector',
    tests_require=[
        'nose',
        'pathlib2'
    ],

    # manually define packages
    py_modules=[
        'jyboss.context',
        'jyboss.cli',
        'jyboss.exceptions',
        'jyboss.logging',
        'jyboss.command.core',
        'jyboss.command.undertow',
        'jyboss.command.extension',
        'jyboss.command.security',
        'jyboss.command.keycloak',
        'jyboss.command.ee',
        'jyboss.command.weld',
        'jyboss.command.datasources',
        'jyboss.command.module',
        'jyboss.command.deployment',
        'jyboss.command.jgroups',
        'jyboss.command.infinispan',
        'jyboss.command.interface',
        'jyboss.command.binding',
        'jyboss.ansible'
    ]

)
