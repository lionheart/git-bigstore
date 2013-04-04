#!/usr/bin/env python

from git import Git
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
g = Git('.')

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

def sync():
    access_key_id = g.config("bigstore.s3.key")
    secret_access_key = g.config("bigstore.s3.secret")
    bucket_name = g.config("bigstore.s3.bucket")

    conn = boto.connect_s3(access_key_id, secret_access_key)
    bucket = boto.s3.bucket.Bucket(conn, bucket_name)
    git_directory = g.rev_parse(git_dir=True)
    destination_folder = os.path.join(git_directory, "bigstore/objects")

    lines = g.ls_tree('HEAD', l=True, z=True, r=True).split('\x00')
    for line in lines:
        try:
            size, filename = line.split(' ')[-1].split('\t')
        except ValueError:
            pass
        else:
            if size == '40':
                with open(filename) as file:
                    contents = file.read()

                if thirty_two_hex.match(contents):
                    _, hexdigest = contents.split('$')
                    destination_filename = os.path.join(destination_folder, hexdigest)
                    try:
                        with open(destination_filename): pass
                    except IOError:
                        key = boto.s3.key.Key(bucket, hexdigest)
                        if key.exists():
                            # Download file
                            with open(filename, 'wb') as file:
                                key.get_contents_to_file(file, cb=transfer_callback(filename))

                            g.add(filename)

    # Now upload files
    for dirpath, dirname, filenames in os.walk(destination_folder):
        for filename in filenames:
            with open(os.path.join(dirpath, filename)) as file:
                key = boto.s3.key.Key(bucket, filename)
                if not key.exists():
                    key.set_contents_from_file(file, cb=transfer_callback(filename))

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
    print "Please enter your S3 Credentials"
    print ""
    s3_key = raw_input("Access Key: ")
    s3_secret = raw_input("Secret Key: ")
    s3_bucket = raw_input("Bucket Name: ")

    g.config("bigstore.s3.key", s3_key)
    g.config("bigstore.s3.secret", s3_secret)
    g.config("bigstore.s3.bucket", s3_bucket)

    g.config("filter.bigstore.clean", "git-bigstore filter-clean")
    g.config("filter.bigstore.smudge", "git-bigstore filter-smudge")

    git_directory = g.rev_parse(git_dir=True)
    destination_folder = os.path.join(git_directory, "bigstore/objects")
    mkdir_p(destination_folder)

