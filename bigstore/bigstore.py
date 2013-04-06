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
object_directory = os.path.join(git_directory, "bigstore", "objects")

def object_filename(hash):
    return os.path.join(object_directory, hash)

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
                firstline = file.next()
                if firstline == 'bigstore\n':
                    _, hash = file.next()[:-1].split('$')
                else:
                    continue

            if not backend.exists(hash):
                with open(object_filename(hash)) as file:
                    backend.push(file, hash)

                g.notes("--ref=bigstore", "append", sha, "-m", "{}	upload	s3	Dan Loewenherz <dloewenherz@gmail.com>".format(time.time()))

    g.push("origin", "refs/notes/bigstore")

def pull():
    pass

def filter_clean():
    file = tempfile.NamedTemporaryFile(mode='w+t', delete=False)
    hash = hashlib.md5()

    for line in sys.stdin:
        if line == "bigstore\n":
            sys.stdout.write(line)
            sys.stdout.write(sys.stdin.next())
            break

        hash.update(line)
        file.write(line)
    else:
        hexdigest = hash.hexdigest()
        mkdir_p(object_directory)
        shutil.copy(file, object_filename(hexdigest))

        sys.stdout.write("bigstore\n")
        sys.stdout.write("md5${}".format(hexdigest))


def filter_smudge():
    for line in sys.stdin:
        if line == "bigstore\n":
            second_line = sys.stdin.next()
            _, hash = second_line[:-1].split('$')
            source_filename = object_filename(hash)

            try:
                with open(source_filename):
                    pass
            except IOError:
                sys.stdout.write(line)
                sys.stdout.write(second_line)
            else:
                with open(source_filename, 'rb') as file:
                    for line in file:
                        sys.stdout.write(line)

                break

def init():
    # print "Please enter your S3 Credentials"
    # print ""
    # s3_key = raw_input("Access Key: ")
    # s3_secret = raw_input("Secret Key: ")
    # s3_bucket = raw_input("Bucket Name: ")

    # g.config("bigstore.s3.key", s3_key)
    # g.config("bigstore.s3.secret", s3_secret)
    # g.config("bigstore.s3.bucket", s3_bucket)

    g.config("filter.bigstore.clean", "git-bigstore filter-clean")
    g.config("filter.bigstore.smudge", "git-bigstore filter-smudge")

    git_directory = g.rev_parse(git_dir=True)
    mkdir_p(object_directory)

