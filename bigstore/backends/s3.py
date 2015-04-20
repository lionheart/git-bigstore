try:
    import boto
except ImportError:
    pass

class S3Backend(object):
    def __init__(self, key, secret, bucket_name):
        self.access_key = key
        self.secret = secret
        self.bucket = bucket_name
        self.conn = boto.connect_s3(key, secret)
        self.bucket = boto.s3.bucket.Bucket(self.conn, bucket_name)

    @property
    def name(self):
        return "s3"

    def key(self, hash):
        return boto.s3.key.Key(self.bucket, "{}/{}".format(hash[:2], hash[2:]))

    def push(self, file, hash, cb=None):
        self.key(hash).set_contents_from_file(file, cb=cb)

    def pull(self, file, hash, cb=None):
        self.key(hash).get_contents_to_file(file, cb=cb)

    def exists(self, hash):
        return self.key(hash).exists()

