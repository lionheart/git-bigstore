#!/usr/bin/env/python

import os
from bigstore import metadata

try:
    from setuptools import setup
except ImportError:
    from distutils.core import setup

setup(
    name='git-bigstore',
    version=metadata.__version__,
    license=metadata.__license__,
    description="Track big files with Git.",
    author=metadata.__author__,
    author_email=metadata.__email__,
    url="http://aurora.io/git-bigstore",
    packages=[
        'bigstore.backends',
        'bigstore',
    ],
    scripts=[
        'bin/git-bigstore',
    ],
    install_requires=[
        'gitpython==0.3.2.RC1',
        'boto==2.8.0',
        'python-dateutil==1.5',
        'pytz==2012h',
        'python-cloudfiles==1.7.10',
    ],
)

