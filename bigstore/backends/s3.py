import boto

class S3Backend(object):
    def __init__(self, key, secret, bucket_name):
        self.key = key
        self.secret = secret
        self.bucket = bucket_name
        self.conn = boto.connect_s3(key, secret)
        self.bucket = boto.s3.bucket.Bucket(self.conn, bucket_name)

    def push(self, file, hash):
        # key.set_contents_from_file(file, cb=transfer_callback(filename))
        key = boto.s3.key.Key(self.bucket, hash)
        key.set_contents_from_file(file)

    def pull(self, file, hash, cb=None):
        # key.get_contents_to_file(file, cb=transfer_callback(filename))
        key = boto.s3.key.Key(self.bucket, hash)
        key.get_contents_to_file(file)

    def exists(self, hash):
        return False
        return boto.s3.key.Key(self.bucket, hash).exists()

