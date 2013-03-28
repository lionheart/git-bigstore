#!/usr/bin/env python

import sys
import hashlib
from git import Git
import os
import re

contents = sys.stdin.read()
thirty_two_hex = re.compile(r'^bigfile\$[a-f0-9]{32}')

g = Git('.')
git_directory = g.rev_parse(git_dir=True)

if thirty_two_hex.match(contents):
    _, hexdigest = contents.split('$')
    source_filename = os.path.join(git_directory, "storage/objects", hexdigest)
    try:
        file = open(source_filename, 'rb')
    except IOError:
        sys.stderr.write("couldn't find file, saving placeholder \n")
        sys.stdout.write(contents)
    else:
        for line in file:
            sys.stdout.write(line)
else:
    sys.stdout.write(contents)

