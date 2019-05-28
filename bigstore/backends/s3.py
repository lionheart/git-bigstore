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

from builtins import object
import sys

try:
    import boto3
    import botocore
except ImportError:
    pass

class S3Backend(object):
    def __init__(self, bucket_name):
        self.bucket = bucket_name
        self.s3_client = aws(type="client", service_name="s3")

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

## Generic AWS helper functions, from https://gist.github.com/bkruger99/6bbaacf1e7fa49891d421d6a1a7ba9c9
"""
    Generic AWS Helper call class to setup a boto3 Session.  Now with assume role support.
    Pass in 'type=' to do either 'client' or 'resource'
    usage:
    ec2 = aws(type='client', service_name='ec2')
    sqs_resource = aws(type='resource', service_name='sqs', RoleArn='arn:aws:iam::012345678901:role/example-role',
                       RoleSessionName='SomeSessionName')
    This will allow for either using your ~/.aws credentials or allow you to override in the function calls.
    Python 2 and 3 compatible without six.
"""

def aws(type='client', **kwargs):
    """
    This makes boto3 client connection. EC2 is the default service being used.
    :param: type (str) - client type.  Either "resource" or "client" right now
    :param: **kwargs - anything else passed in.
    :returns: Your aws object type you requested.
    """
    myargs = {}
    if 'service_name' not in kwargs:
        print("You need to specify a service_name")
        raise

    myargs.update(**kwargs)
    if 'RoleArn' in kwargs and 'RoleSessionName' in myargs:
        stscreds = __role_arn_to_session(**myargs)
        myargs.update(stscreds)

    myargs = __stripargs(**myargs)
    session = boto3.Session()
    client = eval("session." + type)(**myargs)
    return client


# sts assume role
# originally from: https://gist.github.com/gene1wood/938ff578fbe57cf894a105b4107702de
# slightly modified.
def __role_arn_to_session(**args):
    """
    Pass in at least "RoleArn" and "RoleSessionName" with your args in the 'aws' function above.
    """
    clientargs = __stripargs(**args)
    stsargs = __stripargs(sts=True, **args)
    clientargs['service_name'] = 'sts'
    client = boto3.client(**clientargs)
    response = client.assume_role(**stsargs)
    return {
        'aws_access_key_id': response['Credentials']['AccessKeyId'],
        'aws_secret_access_key': response['Credentials']['SecretAccessKey'],
        'aws_session_token': response['Credentials']['SessionToken']}


# Used to strip out STS arguments.
def __stripargs(sts=False, **args):
    stsTuple = ('RoleArn', 'RoleSessionName', 'Policy', 'DurationSeconds', 'ExternalId', 'SerialNumber', 'TokenCode')
    clientargs = dict(args)
    stsargs = {}
    # Check if python 3 or newer. If not, then it's probably 2.
    if sys.version_info.major >= 3:
        for k,v in args.items():
            if k in stsTuple:
                stsargs[k] = v
                del clientargs[k]
    else:
        for k, v in args.iteritems():
            if k in stsTuple:
                stsargs[k] = v
                del clientargs[k]

    if sts is not True:
        return clientargs
    else:
        return stsargs
