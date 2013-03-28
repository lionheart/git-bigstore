# -*- coding: utf-8 -*-

"""
Django Statictastic
~~~~~~~~~~~~~~~~~~~

:copyright: © 2012 Aurora Software
"""

from .metadata import (
    __author__,
    __copyright__,
    __email__,
    __license__,
    __maintainer__,
    __version__,
)

from .bigstore import (
    filter_smudge,
    filter_clean,
    sync,
    mkdir_p
)

__all__ = [
    '__author__', '__copyright__', '__email__', '__license__',
    '__maintainer__', '__version__', 'filter_smudge', 'filter_clean',
    'sync', 'mkdir_p'
]

