"""
authentication operations

Authentication instances are used to interact with the remote
authentication service, retreiving storage system routing information
and session tokens.

See COPYING for license information.
"""

from httplib  import HTTPSConnection, HTTPConnection
from utils    import parse_url, THTTPConnection, THTTPSConnection
from errors   import ResponseError, AuthenticationError, AuthenticationFailed
from consts   import user_agent, us_authurl, uk_authurl
from sys      import version_info


class BaseAuthentication(object):
    """
    The base authentication class from which all others inherit.
    """
    def __init__(self, username, api_key, authurl=us_authurl, timeout=15,
                 useragent=user_agent):
        self.authurl = authurl
        self.headers = dict()
        self.headers['x-auth-user'] = username
        self.headers['x-auth-key'] = api_key
        self.headers['User-Agent'] = useragent
        self.timeout = timeout
        (self.host, self.port, self.uri, self.is_ssl) = parse_url(self.authurl)
        if version_info[0] <= 2 and version_info[1] < 6:
            self.conn_class = self.is_ssl and THTTPSConnection or \
                THTTPConnection
        else:
            self.conn_class = self.is_ssl and HTTPSConnection or HTTPConnection

    def authenticate(self):
        """
        Initiates authentication with the remote service and returns a
        two-tuple containing the storage system URL and session token.

        Note: This is a dummy method from the base class. It must be
        overridden by sub-classes.
        """
        return (None, None, None)


class MockAuthentication(BaseAuthentication):
    """
    Mock authentication class for testing
    """
    def authenticate(self):
        return ('http://localhost/v1/account', None, 'xxxxxxxxx')


class Authentication(BaseAuthentication):
    """
    Authentication, routing, and session token management.
    """
    def authenticate(self):
        """
        Initiates authentication with the remote service and returns a
        two-tuple containing the storage system URL and session token.
        """
        conn = self.conn_class(self.host, self.port, timeout=self.timeout)
        #conn = self.conn_class(self.host, self.port)
        conn.request('GET', '/' + self.uri, headers=self.headers)
        response = conn.getresponse()
        response.read()

        # A status code of 401 indicates that the supplied credentials
        # were not accepted by the authentication service.
        if response.status == 401:
            raise AuthenticationFailed()

        # Raise an error for any response that is not 2XX
        if response.status // 100 != 2:
            raise ResponseError(response.status, response.reason)

        storage_url = cdn_url = auth_token = None

        for hdr in response.getheaders():
            if hdr[0].lower() == "x-storage-url":
                storage_url = hdr[1]
            if hdr[0].lower() == "x-cdn-management-url":
                cdn_url = hdr[1]
            if hdr[0].lower() == "x-storage-token":
                auth_token = hdr[1]
            if hdr[0].lower() == "x-auth-token":
                auth_token = hdr[1]

        conn.close()

        if not (auth_token and storage_url):
            raise AuthenticationError("Invalid response from the " \
                    "authentication service.")

        return (storage_url, cdn_url, auth_token)

# vim:set ai ts=4 sw=4 tw=0 expandtab:
