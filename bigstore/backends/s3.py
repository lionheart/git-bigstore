try:
    import boto3
    import botocore
except ImportError:
    pass

class S3Backend(object):
    def __init__(self, bucket_name, key, secret):
        self.bucket = bucket_name
        self.session = boto3.Session(aws_access_key_id=key, aws_secret_access_key=secret)
        self.s3_client = self.session.client('s3')

    @property
    def name(self):
        return "s3"

    def get_remote_file_name(self, hash):
        return "{}/{}".format(hash[:2], hash[2:])

    def push(self, file, hash, cb=None):
        self.s3_client.upload_file(file.name, self.bucket, self.get_remote_file_name(hash), Callback=cb)

    def pull(self, file, hash, cb=None):
        self.s3_client.download_file(self.bucket, self.get_remote_file_name(hash), file.name, Callback=cb)

    def exists(self, hash):
        exists = False

        try:
            self.s3_client.head_object(Bucket=self.bucket, Key=self.get_remote_file_name(hash))
        except botocore.exceptions.ClientError as e:
            if e.response['Error']['Code'] == "404":
                exists = False
            else:
                raise e
        else:
            exists = True

        return exists
