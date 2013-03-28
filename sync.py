#!/usr/bin/env python

import boto
import git
import os
import sys
import re

thirty_two_hex = re.compile(r'^bigfile\$[a-f0-9]{32}')

g = git.Git('.')
access_key_id = g.config("bigstore.s3.key")
secret_access_key = g.config("bigstore.s3.secret")
bucket_name = g.config("bigstore.s3.bucket")

conn = boto.connect_s3(access_key_id, secret_access_key)
bucket = boto.s3.bucket.Bucket(conn, bucket_name)
git_directory = g.rev_parse(git_dir=True)
destination_folder = os.path.join(git_directory, "storage/objects")

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
                            sys.stderr.write("downloading file: {}\n".format(hexdigest))
                            key.get_contents_to_file(file)

                        g.add(filename)

# Now upload files
for dirpath, dirname, filenames in os.walk(destination_folder):
    for filename in filenames:
        with open(os.path.join(dirpath, filename)) as file:
            key = boto.s3.key.Key(bucket, filename)
            if not key.exists():
                sys.stderr.write("uploading file: {}\n".format(filename))
                key.set_contents_from_file(file)

