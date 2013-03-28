#!/usr/bin/env/python

import os
from bigstore import metadata

try:
    from setuptools import setup
except ImportError:
    from distutils.core import setup

setup(
    name = 'git-bigstore',
    version = metadata.__version__,
    license = metadata.__license__,
    description = "Track big files with Git.",
    author = metadata.__author__,
    author_email = metadata.__email__,
    packages=[
        'bigstore',
    ],
    scripts=[
        'bin/git-bigstore',
    ],
    install_requires=[
        'gitpython==0.3.2.RC1',
        'progressbar'
    ],
)

