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
    import cloudfiles
except ImportError:
    pass

class RackspaceBackend(object):
    def __init__(self, username, api_key, container_name):
        self.username = username
        self.api_key = api_key
        self.conn = cloudfiles.Connection(username=username, api_key=api_key)
        self.container = cloudfiles.Container(self.conn, name=container_name)

    @property
    def name(self):
        return "cloudfiles"

    def key(self, hash):
        return cloudfiles.Object(container=self.container, name="{}/{}".format(hash[:2], hash[2:]))

    def push(self, file, hash, cb=None):
        self.key(hash).load_from_filename(file.name, callback=cb)

    def pull(self, file, hash, cb=None):
        self.key(hash).save_to_filename(file.name, callback=cb)

    def exists(self, hash):
        return self.key(hash).etag is not None


