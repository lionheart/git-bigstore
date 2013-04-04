#!/usr/bin/env python

import time
import os
import fnmatch

from .backends import S3Backend

import git
import boto
import errno
import hashlib
import os
import re
import shutil
import sys
import tempfile
import progressbar

thirty_two_hex = re.compile(r'^bigfile\$[a-f0-9]{32}')
attribute_regex = re.compile(r'(^[^\s]*)')
g = git.Git('.')
git_directory = g.rev_parse(git_dir=True)

def object_filename(hash):
    return os.path.join(git_directory, "bigstore/objects", hash)

def mkdir_p(path):
    try:
        os.makedirs(path)
    except OSError as exc: # Python >2.5
        if exc.errno == errno.EEXIST and os.path.isdir(path):
            pass
        else:
            raise

def transfer_callback(name):
    def inner(size, total):
        widgets = ['{}: '.format(name), progressbar.Percentage(), ' ', progressbar.Bar()]
        pbar = progressbar.ProgressBar(widgets=widgets, maxval=total).start()
        pbar.update(size)

        if size == total:
            pbar.finish()
    return inner

def pathnames():
    """ Generator that will yield pathnames for files tracked under gitattributes """
    filters = []
    try:
        with open(".gitattributes") as file:
            for line in file:
                match = attribute_regex.match(line)
                groups = match.groups()
                if len(groups) > 0:
                    filters.append(groups[0])
    except IOError:
        pass
    else:
        results = g.ls_tree("HEAD", r=True).split('\n')
        filenames = {}
        for result in results:
            metadata, filename = result.split('\t')
            _, _, sha = metadata.split(' ')
            filenames[filename] = sha

        for filter in filters:
            for filename, sha in filenames.iteritems():
                if fnmatch.fnmatch(filename, filter):
                    yield sha, filename

def push():
    try:
        g.fetch("origin", "refs/notes/bigstore:refs/notes/bigstore-remote")
    except git.exc.GitCommandError:
        pass
    else:
        g.notes("--ref=bigstore", "merge", "-s", "cat_sort_uniq", "refs/notes/bigstore-remote")

    access_key_id = g.config("bigstore.s3.key")
    secret_access_key = g.config("bigstore.s3.secret")
    bucket_name = g.config("bigstore.s3.bucket")
    backend = S3Backend(access_key_id, secret_access_key, bucket_name)

    for sha, filename in pathnames():
        try:
            entries = g.notes("--ref=bigstore", "show", sha).split('\n')
        except git.exc.GitCommandError:
            # No notes exist for this object
            entries = []

        for entry in entries:
            if "upload" in entry:
                break
        else:
            with open(filename) as file:
                # upload the file
                if file.next() == 'bigstore':
                    _, hash = file.next().split('$')
                else:
                    continue

            if not backend.exists(hash):
                with open(object_filename(hash)) as file:
                    backend.push(file, hash)

                g.notes("--ref=bigstore", "append", sha, "-m", str(time.time()), "upload", "s3", "Dan", "Loewenherz", "<dloewenherz@gmail.com")

    g.push("origin", "refs/notes/bigstore")

def pull():
    pass

def filter_clean():
    def clean_file(hash, file):
        hexdigest = hash.hexdigest()
        filename = file.name
        file.close()

        git_directory = g.rev_parse(git_dir=True)
        destination_folder = os.path.join(git_directory, "bigstore/objects")
        mkdir_p(destination_folder)
        destination_filename = os.path.join(destination_folder, hexdigest)
        shutil.copy(filename, destination_filename)
        sys.stdout.write("bigfile${}".format(hexdigest))

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
            sys.stdout.write(contents)
            sys.exit(0)

    clean_file(hash, file)

def filter_smudge():
    contents = sys.stdin.read()

    git_directory = g.rev_parse(git_dir=True)

    if thirty_two_hex.match(contents):
        _, hexdigest = contents.split('$')
        source_filename = os.path.join(git_directory, "bigstore/objects", hexdigest)
        try:
            file = open(source_filename, 'rb')
        except IOError:
            sys.stdout.write(contents)
        else:
            for line in file:
                sys.stdout.write(line)
    else:
        sys.stdout.write(contents)

def init():
    # print "Please enter your S3 Credentials"
    # print ""
    # s3_key = raw_input("Access Key: ")
    # s3_secret = raw_input("Secret Key: ")
    # s3_bucket = raw_input("Bucket Name: ")

    # g.config("bigstore.s3.key", s3_key)
    # g.config("bigstore.s3.secret", s3_secret)
    # g.config("bigstore.s3.bucket", s3_bucket)

    # g.config("filter.bigstore.clean", "git-bigstore filter-clean")
    # g.config("filter.bigstore.smudge", "git-bigstore filter-smudge")

    git_directory = g.rev_parse(git_dir=True)
    destination_folder = os.path.join(git_directory, "bigstore/objects")
    mkdir_p(destination_folder)

