""" See COPYING for license information. """

__version__ = "1.7.11"
user_agent = "python-cloudfiles/%s" % __version__
us_authurl = 'https://auth.api.rackspacecloud.com/v1.0'
uk_authurl = 'https://lon.auth.api.rackspacecloud.com/v1.0'
default_authurl = us_authurl
default_cdn_ttl = 86400
cdn_log_retention = False

meta_name_limit = 128
meta_value_limit = 256
object_name_limit = 1024
container_name_limit = 256
