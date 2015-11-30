#!/usr/bin/env python

import os

try:
    from setuptools import setup
except ImportError:
    from distutils.core import setup

metadata = {}
execfile("bigstore/metadata.py", metadata)

setup(
    name='git-bigstore',
    version=metadata['__version__'],
    license=metadata['__license__'],
    description="Track big files with Git.",
    author=metadata['__author__'],
    author_email=metadata['__email__'],
    url="https://github.com/lionheart/git-bigstore",
    packages=[
        'bigstore.backends',
        'bigstore',
    ],
    scripts=[
        'bin/git-bigstore',
    ],
)

