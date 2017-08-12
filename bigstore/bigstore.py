#!/usr/bin/env python

# Copyright 2015-2017 Lionheart Software LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from datetime import datetime
import bz2
import errno
import fnmatch
import hashlib
import operator
import os
import re
import shutil
import sys
import tempfile
import time

from .backends import S3Backend
from .backends import RackspaceBackend
from .backends import GoogleBackend

from dateutil import tz as dateutil_tz
import git
import pytz

attribute_regex = re.compile(r'^([^\s]*) filter=(bigstore(?:-compress)?)$')

g = lambda: git.Git('.')
git_directory = lambda git_instance: git_instance.rev_parse(git_dir=True)

try:
    default_hash_function_name = g().config("bigstore.hash_function")
except git.exc.GitCommandError:
    default_hash_function_name = 'sha1'

try:
    toplevel_dir = g().rev_parse(show_toplevel=True)
except git.exc.GitCommandError:
    toplevel_dir = '.'
config_filename = os.path.join(toplevel_dir, '.bigstore')

hash_functions = {
    'md5': hashlib.md5,
    'sha1': hashlib.sha1,
    'sha224': hashlib.sha224,
    'sha256': hashlib.sha256,
    'sha384': hashlib.sha384,
    'sha512': hashlib.sha512
}

default_hash_function = hash_functions[default_hash_function_name]


def config(name):
    """
    Read a setting from the .bigstore config file

    :param name: name of config setting to read
    :return: str or None
    """
    try:
        return g().config(name, file=config_filename)
    except git.exc.GitCommandError:
        return None


def default_backend():
    backend_name = config('bigstore.backend')
    backend = backend_for_name(backend_name)

    if backend:
        return backend
    else:
        sys.stderr.write("error: s3, gs, and cloudfiles are currently the only supported backends")
        sys.exit(0)


def backend_for_name(name):
    if name == 's3':
        bucket_name = config('bigstore.s3.bucket')
        access_key_id = config('bigstore.s3.key')
        secret_access_key = config('bigstore.s3.secret')
        profile_name = config('bigstore.s3.profile-name')
        return S3Backend(bucket_name, access_key_id, secret_access_key, profile_name)
    elif name == 'cloudfiles':
        username = config('bigstore.cloudfiles.username')
        api_key = config('bigstore.cloudfiles.key')
        container_name = config('bigstore.cloudfiles.container')
        return RackspaceBackend(username, api_key, container_name)
    elif name == 'gs':
        access_key_id = config('bigstore.gs.key')
        secret_access_key = config('bigstore.gs.secret')
        bucket_name = config('bigstore.gs.bucket')
        return GoogleBackend(access_key_id, secret_access_key, bucket_name)
    else:
        return None


def object_directory(hash_function_name):
    return os.path.join(git_directory(g()), "bigstore", "objects", hash_function_name)


def object_filename(hash_function_name, hexdigest):
    return os.path.join(object_directory(hash_function_name), hexdigest[:2], hexdigest[2:])


def mkdir_p(path):
    try:
        os.makedirs(path)
    except OSError as exc:
        # Python >2.5
        if exc.errno == errno.EEXIST and os.path.isdir(path):
            pass
        else:
            raise


class ProgressPercentage(object):
    def __init__(self, filename):
        self.filename = filename
        self.size = float(os.path.getsize(filename))
        self.seen_so_far = 0

    def __call__(self, bytes_amount):
        self.seen_so_far += bytes_amount
        if self.size:
            percentage = self.seen_so_far / self.size
            sys.stdout.write("\r{}  {} / {}  ({: <2.0%})".format(
                self.filename, self.seen_so_far, self.size, percentage))
        else:
            sys.stdout.write("\r{}  {}".format(self.filename, self.seen_so_far))
        sys.stdout.flush()


def pathnames_from_filename(filename):
    filters = []
    try:
        with open(filename) as file:
            for line in file:
                match = attribute_regex.match(line)
                if match:
                    groups = match.groups()
                    if len(groups) > 0:
                        filters.append((groups[0], groups[1]))
    except IOError:
        # The .gitattributes file might not exist. Should prompt the user to run
        # "git bigstore init"?
        pass
    return filters


def pathnames():
    """ Generator that will yield pathnames for pathnames tracked under .gitattributes and private attributes """
    filters = []
    filters.extend(pathnames_from_filename(os.path.join(toplevel_dir, '.gitattributes')))
    filters.extend(pathnames_from_filename(os.path.join(toplevel_dir, '.git/info/attributes')))
    if not filters:
        sys.stderr.write("No bigstore gitattributes filters found.  Is .gitattributes set up correctly?\n")
        return

    results = g().ls_tree("HEAD", r=True).split('\n')
    filenames = {}
    for result in results:
        metadata, filename = result.split('\t')
        _, _, sha = metadata.split(' ')
        filenames[filename] = sha

    for wildcard, filter in filters:
        for filename, sha in filenames.iteritems():
            if fnmatch.fnmatch(filename, wildcard):
                yield sha, filename, filter == "bigstore-compress"


def pull_metadata(repository='origin'):
    """
    Pull metadata from repository and automatically merge it with local metadata

    :param repository: git url or remote
    """
    try:
        if repository == "origin":
            sys.stderr.write("pulling bigstore metadata...")
        else:
            sys.stderr.write("pulling bigstore metadata from {}...".format(repository))

        g().fetch(repository, "refs/notes/bigstore:refs/notes/bigstore-remote", "--force")
    except git.exc.GitCommandError:
        try:
            # Create a ref so that we can push up to the repo.
            g().notes("--ref=bigstore", "add", "HEAD", "-m", "bigstore")
            sys.stderr.write("done\n")
        except git.exc.GitCommandError:
            # If it fails silently, an existing notes object already exists.
            sys.stderr.write("\n")
    else:
        g().notes("--ref=bigstore", "merge", "-s", "cat_sort_uniq", "refs/notes/bigstore-remote")
        sys.stderr.write("done\n")


def push():
    assert_initialized()
    pull_metadata()

    if len(sys.argv) > 2:
        filters = sys.argv[2:]
    else:
        filters = []

    # Should show a message to the user if not in the base directory.
    for sha, filename, compress in pathnames():
        should_process = len(filters) == 0 or any(fnmatch.fnmatch(filename, filter) for filter in filters)
        if should_process:
            try:
                entries = g().notes("--ref=bigstore", "show", sha).split('\n')
            except git.exc.GitCommandError:
                # No notes exist for this object
                entries = []

            backend = default_backend()
            for entry in entries:
                try:
                    timestamp, action, backend_name, _ = entry.split('\t')
                except ValueError:
                    # probably a blank line
                    pass
                else:
                    if action in ("upload", "upload-compressed") and backend.name == backend_name:
                        break
            else:
                try:
                    firstline, hash_function_name, hexdigest = g().show(sha).split('\n')
                except ValueError:
                    pass
                else:
                    if firstline == 'bigstore':
                        if not backend.exists(hexdigest):
                            with open(object_filename(hash_function_name, hexdigest)) as file:
                                if compress:
                                    with tempfile.TemporaryFile() as compressed_file:
                                        compressor = bz2.BZ2Compressor()
                                        for line in file:
                                            compressed_file.write(compressor.compress(line))

                                        compressed_file.write(compressor.flush())
                                        compressed_file.seek(0)

                                        sys.stderr.write("compressed!\n")
                                        backend.push(compressed_file, hexdigest, cb=ProgressPercentage(filename))
                                else:
                                    backend.push(file, hexdigest, cb=ProgressPercentage(filename))

                            sys.stderr.write("\n")

                        user_name = g().config("user.name")
                        user_email = g().config("user.email")

                        # XXX Should the action ("upload / upload-compress") be
                        # different if the file already exists on the backend?
                        if compress:
                            action = "upload-compressed"
                        else:
                            action = "upload"

                        # We use the timestamp as the first entry as it will help us
                        # sort the entries easily with the cat_sort_uniq merge.
                        g().notes("--ref=bigstore", "append", sha, "-m", "{}	{}	{}	{} <{}>".format(
                            time.time(), action, backend.name, user_name, user_email))

    sys.stderr.write("pushing bigstore metadata...")
    g().push("origin", "refs/notes/bigstore")
    sys.stderr.write("done\n")


def pull():
    assert_initialized()
    pull_metadata()

    if len(sys.argv) > 2:
        filters = sys.argv[2:]
    else:
        filters = []

    for sha, filename, compress in pathnames():
        should_process = len(filters) == 0 or any(fnmatch.fnmatch(filename, filter) for filter in filters)
        if should_process:
            try:
                entries = g().notes("--ref=bigstore", "show", sha).split('\n')
            except git.exc.GitCommandError:
                pass
            else:
                for entry in entries:
                    timestamp, action, backend_name, _ = entry.split('\t')
                    if action in ("upload", "upload-compressed"):
                        firstline, hash_function_name, hexdigest = g().show(sha).split('\n')
                        if firstline == 'bigstore':
                            try:
                                with open(object_filename(hash_function_name, hexdigest)):
                                    pass
                            except IOError:
                                backend = backend_for_name(backend_name)
                                if backend.exists(hexdigest):
                                    if action == "upload-compressed":
                                        with tempfile.TemporaryFile() as compressed_file:
                                            backend.pull(compressed_file, hexdigest, cb=ProgressPercentage(filename))
                                            compressed_file.seek(0)

                                            decompressor = bz2.BZ2Decompressor()
                                            with open(filename, 'wb') as file:
                                                for line in compressed_file:
                                                    file.write(decompressor.decompress(line))
                                    else:
                                        with open(filename, 'wb') as file:
                                            backend.pull(file, hexdigest, cb=ProgressPercentage(filename))

                                    sys.stderr.write("\n")
                                    g().add(filename)

                        break

    sys.stderr.write('pushing bigstore metadata...')
    try:
        g().push('origin', 'refs/notes/bigstore')
        sys.stderr.write('done\n')
    except git.exc.GitCommandError as e:
        if e.stderr and 'read only' in e.stderr:
            sys.stderr.write('read only\n')
        else:
            # An error pushing during a pull is not fatal
            sys.stderr.write('ERROR\n')


def fetch(repository):
    """
    Pull metadata from a remote repository and merge it with our own.

    :param repository: either a git url or name of a remote
    """
    pull_metadata()
    pull_metadata(repository)

    sys.stderr.write("pushing bigstore metadata...")
    g().push("origin", "refs/notes/bigstore")
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

    g().config("bigstore.backend", "cloudfiles", file=config_filename)
    g().config("bigstore.cloudfiles.username", username, file=config_filename)
    g().config("bigstore.cloudfiles.key", api_key, file=config_filename)
    g().config("bigstore.cloudfiles.container", container, file=config_filename)


def request_s3_credentials():
    print
    print "Enter your Amazon S3 Credentials"
    print
    s3_bucket = raw_input("Bucket Name: ")
    s3_key = raw_input("Access Key: ")
    s3_secret = raw_input("Secret Key: ")
    s3_profile_name = raw_input("Profile Name: ")

    g().config("bigstore.backend", "s3", file=config_filename)
    g().config("bigstore.s3.bucket", s3_bucket, file=config_filename)
    if s3_key != '':
        g().config("bigstore.s3.key", s3_key, file=config_filename)
    if s3_secret != '':
        g().config("bigstore.s3.secret", s3_secret, file=config_filename)
    if s3_profile_name != '':
        g().config("bigstore.s3.profile-name", s3_profile_name, file=config_filename)


def request_google_cloud_storage_credentials():
    print
    print "Enter your Google Cloud Storage Credentials"
    print
    google_key = raw_input("Access Key: ")
    google_secret = raw_input("Secret Key: ")
    google_bucket = raw_input("Bucket Name: ")

    g().config("bigstore.backend", "gs", file=config_filename)
    g().config("bigstore.gs.key", google_key, file=config_filename)
    g().config("bigstore.gs.secret", google_secret, file=config_filename)
    g().config("bigstore.gs.bucket", google_bucket, file=config_filename)


def log():
    filename = sys.argv[2]
    trees = g().log("--pretty=format:%T", filename).split('\n')
    entries = []
    for tree in trees:
        entry = g().ls_tree('-r', tree, filename)
        if entry.strip() == '':
            # skip empty lines as they will cause exceptions later
            continue
        metadata, filename = entry.split('\t')
        _, _, sha = metadata.split(' ')
        try:
            notes = g().notes("--ref=bigstore", "show", sha).split('\n')
        except git.exc.GitCommandError:
            # No note found for object.
            pass
        else:
            notes.reverse()
            for note in notes:
                if note == '':
                    continue

                timestamp, action, backend, user = note.split('\t')
                utc_dt = datetime.fromtimestamp(float(timestamp), tz=pytz.timezone("UTC"))
                dt = utc_dt.astimezone(dateutil_tz.tzlocal())
                formatted_date = "{} {} {}".format(dt.strftime("%a %b"), dt.strftime("%e").replace(' ', ''),
                                                   dt.strftime("%T %Y %Z"))
                entries.append((dt, sha, formatted_date, action, backend, user))

    sorted_entries = sorted(entries, key=operator.itemgetter(0), reverse=True)
    for dt, sha, formatted_date, action, backend, user in sorted_entries:
        if action in ("upload", "upload-compressed"):
            line = u"({}) {}: {} \u2190 {}".format(sha[:6], formatted_date, backend, user)
        else:
            line = u"({}) {}: {} \u2192 {}".format(sha[:6], formatted_date, backend, user)

        print line


def init():
    try:
        g().config("bigstore.backend", file=config_filename)
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
                g().config("bigstore.s3.bucket", file=config_filename)
            except git.exc.GitCommandError:
                request_s3_credentials()

            keys_set = True
            try:
                g().config("bigstore.s3.key", file=config_filename)
                g().config("bigstore.s3.secret", file=config_filename)
            except git.exc.GitCommandError:
                keys_set = False

            profile_name_set = True
            try:
                g().config("bigstore.s3.profile-name", file=config_filename)
            except git.exc.GitCommandError:
                profile_name_set = False

            if not keys_set and not profile_name_set:
                print "Either the secret keys are not set or the profile name is not set"
                request_s3_credentials()
        elif choice == "2":
            try:
                g().config("bigstore.gs.key", file=config_filename)
                g().config("bigstore.gs.secret", file=config_filename)
                g().config("bigstore.gs.bucket", file=config_filename)
            except git.exc.GitCommandError:
                request_google_cloud_storage_credentials()
        elif choice == "3":
            try:
                g().config("bigstore.cloudfiles.username", file=config_filename)
                g().config("bigstore.cloudfiles.key", file=config_filename)
                g().config("bigstore.cloudfiles.container", file=config_filename)
            except git.exc.GitCommandError:
                request_rackspace_credentials()

    else:
        print "Reading credentials from .bigstore configuration file."

    try:
        g().fetch("origin", "refs/notes/bigstore:refs/notes/bigstore")
    except git.exc.GitCommandError:
        try:
            g().notes("--ref=bigstore", "add", "HEAD", "-m", "bigstore")
        except git.exc.GitCommandError:
            # Occurs when notes already exist for this ref.
            print "Bigstore has already been initialized."

    g().config("filter.bigstore.clean", "git-bigstore filter-clean")
    g().config("filter.bigstore.smudge", "git-bigstore filter-smudge")
    g().config("filter.bigstore-compress.clean", "git-bigstore filter-clean")
    g().config("filter.bigstore-compress.smudge", "git-bigstore filter-smudge")

    mkdir_p(object_directory(default_hash_function_name))


def assert_initialized():
    """
    Check to make sure `git bigstore init` has been called.
    If not, then print an error and exit(1)
    """
    try:
        if g().config('filter.bigstore.clean') == 'git-bigstore filter-clean':
            return  # repo config looks good
    except git.exc.GitCommandError:
        # `git config` can throw errors if the key is missing
        pass
    if os.path.exists(os.path.join(toplevel_dir, '.git')):
        sys.stderr.write('fatal: You must run `git bigstore init` first.\n')
    else:
        sys.stderr.write('fatal: Not a git repository.\n')
    sys.exit(1)
