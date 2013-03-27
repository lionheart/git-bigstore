#!/usr/bin/env python

from git import Git
import errno
import hashlib
import os
import re
import shutil
import sys
import tempfile

thirty_two_hex = re.compile(r'^bigfile\$[a-f0-9]{32}')

def clean_file(hash, file):
    sys.stderr.write("cleaning file\n")
    hexdigest = hash.hexdigest()
    filename = file.name
    file.close()

    g = Git('.')
    git_directory = g.rev_parse(git_dir=True)
    destination_folder = os.path.join(git_directory, "storage/objects")
    mkdir_p(destination_folder)
    destination_filename = os.path.join(destination_folder, hexdigest)
    shutil.copy(filename, destination_filename)
    sys.stdout.write("bigfile${}".format(hexdigest))

def mkdir_p(path):
    try:
        os.makedirs(path)
    except OSError as exc: # Python >2.5
        if exc.errno == errno.EEXIST and os.path.isdir(path):
            pass
        else:
            raise

file = tempfile.NamedTemporaryFile(mode='w+t', delete=False)
hash = hashlib.md5()
for line in sys.stdin:
    hash.update(line)
    file.write(line)

file_length = file.tell()
file.seek(0)

if file_length == 40:
    contents = file.read()
    if thirty_two_hex.match(contents):
        sys.stderr.write("file already cleaned: {}\n".format(contents))
        sys.stdout.write(contents)
        sys.exit(0)

clean_file(hash, file)

