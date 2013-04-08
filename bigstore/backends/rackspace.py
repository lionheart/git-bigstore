import cloudfiles

class RackspaceBackend(object):
    def __init__(self, username, api_key, container_name):
        self.username = username
        self.api_key = api_key
        self.conn = cloudfiles.Connection(username=username, api_key=api_key)
        self.container = cloudfiles.Container(self.conn, name=container_name)

    def key(self, hash):
        return cloudfiles.Object(container=self.container, name="{}/{}".format(hash[:2], hash[2:]))

    def push(self, file, hash, cb=None):
        self.key(hash).load_from_filename(file.name, callback=cb)

    def pull(self, file, hash, cb=None):
        self.key(hash).save_to_filename(file.name, callback=cb)

    def exists(self, hash):
        return self.key(hash).etag is not None


