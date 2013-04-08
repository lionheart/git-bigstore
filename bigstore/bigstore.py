#!/usr/bin/env python

import time
import os
import fnmatch
from datetime import datetime

from .backends import S3Backend
from .backends import RackspaceBackend
from .backends import GoogleBackend

import git
import boto
import errno
import hashlib
import os
import re
import shutil
import sys
import tempfile

attribute_regex = re.compile(r'(^[^\s]*)')
g = git.Git('.')
git_directory = g.rev_parse(git_dir=True)

try:
    default_hash_function_name = g.config("bigstore.hash_function")
except git.exc.GitCommandError:
    default_hash_function_name = 'sha256'

hash_functions = {
    'md5': hashlib.md5,
    'sha1': hashlib.sha1,
    'sha224': hashlib.sha224,
    'sha256': hashlib.sha256,
    'sha384': hashlib.sha384,
    'sha512': hashlib.sha512
}

default_hash_function = hash_functions[default_hash_function_name]

def default_backend():
    try:
        backend_name = g.config("bigstore.backend", file=".bigstore")
    except git.exc.GitCommandError:
        backend_name = None

    backend = backend_for_name(backend_name)

    if backend:
        return backend
    else:
        sys.stderr.write("error: s3, gs, and cloudfiles are currently the only supported backends")
        sys.exit(0)

def backend_for_name(name):
    if name == "s3":
        access_key_id = g.config("bigstore.s3.key", file=".bigstore")
        secret_access_key = g.config("bigstore.s3.secret", file=".bigstore")
        bucket_name = g.config("bigstore.s3.bucket", file=".bigstore")
        return S3Backend(access_key_id, secret_access_key, bucket_name)
    elif name == "cloudfiles":
        username = g.config("bigstore.cloudfiles.username", file=".bigstore")
        api_key = g.config("bigstore.cloudfiles.key", file=".bigstore")
        container_name = g.config("bigstore.cloudfiles.container", file=".bigstore")
        return RackspaceBackend(username, api_key, container_name)
    elif name == "gs":
        access_key_id = g.config("bigstore.gs.key", file=".bigstore")
        secret_access_key = g.config("bigstore.gs.secret", file=".bigstore")
        bucket_name = g.config("bigstore.gs.bucket", file=".bigstore")
        return GoogleBackend(access_key_id, secret_access_key, bucket_name)
    else:
        return None

def object_directory(hash_function_name):
    return os.path.join(git_directory, "bigstore", "objects", hash_function_name)

def object_filename(hash_function_name, hexdigest):
    return os.path.join(object_directory(hash_function_name), hexdigest[:2], hexdigest[2:])

def mkdir_p(path):
    try:
        os.makedirs(path)
    except OSError as exc: # Python >2.5
        if exc.errno == errno.EEXIST and os.path.isdir(path):
            pass
        else:
            raise

def upload_callback(filename):
    def inner(size, total):
        sys.stderr.write("\r")
        if total > 0:
            sys.stderr.write("{: <4.0%}\t{}".format(size / float(total), filename))
        else:
            sys.stderr.write("?%\t{}".format(filename))

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
        sys.stderr.write("pulling bigstore metadata...")
        g.fetch("origin", "refs/notes/bigstore:refs/notes/bigstore-remote", "--force")
    except git.exc.GitCommandError:
        g.notes("--ref=bigstore", "add", "HEAD", "-m", "bigstore")
        sys.stderr.write("done\n")
    else:
        g.notes("--ref=bigstore", "merge", "-s", "cat_sort_uniq", "refs/notes/bigstore-remote")
        sys.stderr.write("done\n")

    if len(sys.argv) > 2:
        filters = sys.argv[2:]
    else:
        filters = []

    for sha, filename in pathnames():
        should_process = len(filters) == 0 or any(fnmatch.fnmatch(filename, filter) for filter in filters)
        if should_process:
            try:
                entries = g.notes("--ref=bigstore", "show", sha).split('\n')
            except git.exc.GitCommandError:
                # No notes exist for this object
                entries = []

            backend = default_backend()
            for entry in entries:
                if "upload" in entry and backend.name in entry:
                    break
            else:
                firstline, hash_function_name, hexdigest = g.show(sha).split('\n')
                if firstline == 'bigstore':
                    if not backend.exists(hexdigest):
                        with open(object_filename(hash_function_name, hexdigest)) as file:
                            backend.push(file, hexdigest, cb=upload_callback(filename))

                        sys.stderr.write("\n")

                    user_name = g.config("user.name")
                    user_email = g.config("user.email")

                    # XXX Should the action ("upload") be different if the file already exists on the backend?
                    action = "upload"

                    # We use the timestamp as the first entry as it will help us
                    # sort the entries easily with the cat_sort_uniq merge.
                    g.notes("--ref=bigstore", "append", sha, "-m", "{}	{}	{}	{} <{}>".format(time.time(), action, backend.name, user_name, user_email))

    sys.stderr.write("pushing bigstore metadata...")
    g.push("origin", "refs/notes/bigstore")
    sys.stderr.write("done\n")

def pull():
    try:
        sys.stderr.write("pulling bigstore metadata...")
        g.fetch("origin", "refs/notes/bigstore:refs/notes/bigstore-remote", "--force")
    except git.exc.GitCommandError:
        g.notes("--ref=bigstore", "add", "HEAD", "-m", "bigstore")
        sys.stderr.write("done\n")
    else:
        g.notes("--ref=bigstore", "merge", "-s", "cat_sort_uniq", "refs/notes/bigstore-remote")
        sys.stderr.write("done\n")

    if len(sys.argv) > 2:
        filters = sys.argv[2:]
    else:
        filters = []

    for sha, filename in pathnames():
        should_process = len(filters) == 0 or any(fnmatch.fnmatch(filename, filter) for filter in filters)
        if should_process:
            try:
                entries = g.notes("--ref=bigstore", "show", sha).split('\n')
            except git.exc.GitCommandError:
                pass
            else:
                for entry in entries:
                    timestamp, action, backend_name, _ = entry.split('\t')
                    if action == "upload":
                        firstline, hash_function_name, hexdigest = g.show(sha).split('\n')
                        if firstline == 'bigstore':
                            try:
                                with open(object_filename(hash_function_name, hexdigest)):
                                    pass
                            except IOError:
                                backend = backend_for_name(backend_name)
                                if backend.exists(hexdigest):
                                    with open(filename, 'wb') as file:
                                        backend.pull(file, hexdigest, cb=upload_callback(filename))

                                    sys.stderr.write("\n")

                                    user_name = g.config("user.name")
                                    user_email = g.config("user.email")
                                    g.notes("--ref=bigstore", "append", sha, "-m", "{}	download	{}	{} <{}>".format(time.time() + time.timezone, backend.name, user_name, user_email))
                                    g.add(filename)

                        break

    sys.stderr.write("pushing bigstore metadata...")
    g.push("origin", "refs/notes/bigstore")
    sys.stderr.write("done\n")

def filter_clean():
    firstline = sys.stdin.next()
    if firstline == "bigstore\n":
        sys.stdout.write(firstline)
        for line in sys.stdin:
            sys.stdout.write(line)
    else:
        file = tempfile.NamedTemporaryFile(mode='w+t', delete=False)
        hash_function = default_hash_function()
        hash_function.update(firstline)
        file.write(firstline)

        for line in sys.stdin:
            hash_function.update(line)
            file.write(line)

        file.close()

        hexdigest = hash_function.hexdigest()
        mkdir_p(os.path.join(object_directory(default_hash_function_name), hexdigest[:2]))
        shutil.copy(file.name, object_filename(default_hash_function_name, hexdigest))

        sys.stdout.write("bigstore\n")
        sys.stdout.write("{}\n".format(default_hash_function_name))
        sys.stdout.write("{}\n".format(hexdigest))


def filter_smudge():
    firstline = sys.stdin.next()
    if firstline == "bigstore\n":
        hash_function_name = sys.stdin.next()
        hexdigest = sys.stdin.next()
        source_filename = object_filename(hash_function_name[:-1], hexdigest[:-1])

        try:
            with open(source_filename):
                pass
        except IOError:
            sys.stdout.write(firstline)
            sys.stdout.write(hash_function_name)
            sys.stdout.write(hexdigest)
        else:
            with open(source_filename, 'rb') as file:
                for line in file:
                    sys.stdout.write(line)
    else:
        sys.stdout.write(firstline)
        for line in sys.stdin:
            sys.stdout.write(line)

def request_rackspace_credentials():
    print
    print "Enter your Rackspace Cloud Files Credentials"
    print
    username = raw_input("Username: ")
    api_key = raw_input("API Key: ")
    container = raw_input("Container: ")

    g.config("bigstore.backend", "cloudfiles", file=".bigstore")
    g.config("bigstore.cloudfiles.username", username, file=".bigstore")
    g.config("bigstore.cloudfiles.key", api_key, file=".bigstore")
    g.config("bigstore.cloudfiles.container", container, file=".bigstore")

def request_s3_credentials():
    print
    print "Enter your Amazon S3 Credentials"
    print
    s3_key = raw_input("Access Key: ")
    s3_secret = raw_input("Secret Key: ")
    s3_bucket = raw_input("Bucket Name: ")

    g.config("bigstore.backend", "s3", file=".bigstore")
    g.config("bigstore.s3.key", s3_key, file=".bigstore")
    g.config("bigstore.s3.secret", s3_secret, file=".bigstore")
    g.config("bigstore.s3.bucket", s3_bucket, file=".bigstore")

def request_google_cloud_storage_credentials():
    print
    print "Enter your Google Cloud Storage Credentials"
    print
    google_key = raw_input("Access Key: ")
    google_secret = raw_input("Secret Key: ")
    google_bucket = raw_input("Bucket Name: ")

    g.config("bigstore.backend", "gs", file=".bigstore")
    g.config("bigstore.gs.key", google_key, file=".bigstore")
    g.config("bigstore.gs.secret", google_secret, file=".bigstore")
    g.config("bigstore.gs.bucket", google_bucket, file=".bigstore")

def log():
    filename = sys.argv[2]
    trees = g.log("--pretty=format:%T", filename).split('\n')
    for tree in trees:
        entry = g.ls_tree('-r', tree, filename)
        metadata, filename = entry.split('\t')
        _, _, digest = metadata.split(' ')
        notes = g.notes("--ref=bigstore", "show", digest).split('\n')
        notes.reverse()
        for note in notes:
            if note == '':
                continue

            timestamp, action, backend, user = note.split('\t')
            dt = datetime.fromtimestamp(float(timestamp))
            if action == "upload":
                print u"{}: {} \u2190 {}".format(dt.strftime("%a %b %e %X %Y +0000"), backend, user)
            else:
                print u"{}: {} \u2192 {}".format(dt.strftime("%a %b %e %X %Y +0000"), backend, user)

def init():
    try:
        g.config("bigstore.backend", file=".bigstore")
    except git.exc.GitCommandError:
        print "What backend would you like to store your files with?"
        print "(1) Amazon S3"
        print "(2) Google Cloud Storage"
        print "(3) Rackspace Cloud Files"
        choice = None
        while choice not in ["1", "2", "3"]:
            choice = raw_input("Enter your choice here: ")

        if choice == "1":
            try:
                g.config("bigstore.s3.key", file=".bigstore")
                g.config("bigstore.s3.secret", file=".bigstore")
                g.config("bigstore.s3.bucket", file=".bigstore")
            except git.exc.GitCommandError:
                request_s3_credentials()
        elif choice == "2":
            try:
                g.config("bigstore.gs.key", file=".bigstore")
                g.config("bigstore.gs.secret", file=".bigstore")
                g.config("bigstore.gs.bucket", file=".bigstore")
            except git.exc.GitCommandError:
                request_google_cloud_storage_credentials()
        elif choice == "3":
            try:
                g.config("bigstore.cloudfiles.username", file=".bigstore")
                g.config("bigstore.cloudfiles.key", file=".bigstore")
                g.config("bigstore.cloudfiles.container", file=".bigstore")
            except git.exc.GitCommandError:
                request_rackspace_credentials()

    else:
        print "Reading credentials from .bigstore configuration file."

    try:
        g.fetch("origin", "refs/notes/bigstore:refs/notes/bigstore")
    except git.exc.GitCommandError:
        g.notes("--ref=bigstore", "add", "HEAD", "-m", "bigstore")

    g.config("filter.bigstore.clean", "git-bigstore filter-clean")
    g.config("filter.bigstore.smudge", "git-bigstore filter-smudge")

    git_directory = g.rev_parse(git_dir=True)
    mkdir_p(object_directory(default_hash_function_name))

