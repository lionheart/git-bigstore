#!/usr/bin/env python

import sys
import hashlib
from git import Git
import os
import re

hexdigest = sys.stdin.read()
thirty_two_hex = re.compile(r'^bigfile\$[a-f0-9]{32}')

g = Git('.')
git_directory = g.rev_parse(git_dir=True)
source_filename = os.path.join(git_directory, "storage/objects", hexdigest)

if thirty_two_hex.match(hexdigest):
    try:
        file = open(source_filename, 'rb')
    except IOError:
        sys.stderr.write("couldn't find file, saving placeholder \n")
        sys.stdout.write(hexdigest)
    else:
        for line in file:
            sys.stdout.write(line)
else:
    sys.stdout.write(hexdigest)

