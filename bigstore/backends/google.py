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

try:
    import boto
except ImportError:
    pass

class GoogleBackend(object):
    def __init__(self, key, secret, bucket_name):
        self.access_key = key
        self.secret = secret
        self.bucket = bucket_name
        self.conn = boto.connect_gs(key, secret)
        self.bucket = boto.s3.bucket.Bucket(self.conn, bucket_name)

    @property
    def name(self):
        return "gs"

    def key(self, hash):
        return boto.s3.key.Key(self.bucket, "{}/{}".format(hash[:2], hash[2:]))

    def push(self, file, hash, cb=None):
        self.key(hash).set_contents_from_file(file, cb=cb)

    def pull(self, file, hash, cb=None):
        self.key(hash).get_contents_to_file(file, cb=cb)

    def exists(self, hash):
        return self.key(hash).exists()

