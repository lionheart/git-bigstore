"""
Cloud Files python client API.

Working with result sets:

    >>> import cloudfiles
    >>> # conn = cloudfiles.get_connection(username='jsmith', \
                 api_key='1234567890')
    >>> conn = cloudfiles.get_connection('jsmith', '1234567890')
    >>> # NOTE: For Uk Customers please pass in Default UK Auth URL like EX
    >>> conn = cloudfiles.get_connection('username', 'api_key', \
    >>>                                  authurl = cloudfiles.uk_authurl)
    >>> # This will force connectivity to the UK's Auth Service
    >>> containers = conn.get_all_containers()
    >>> type(containers)
    <class 'cloudfiles.container.ContainerResults'>
    >>> len(containers)
    2
    >>> for container in containers:
    >>>     print container.name
    fruit
    vegitables
    >>> print containers[0].name
    fruit
    >>> fruit_container = containers[0]
    >>> objects = fruit_container.get_objects()
    >>> for storage_object in objects:
    >>>     print storage_object.name
    apple
    orange
    bannana
    >>>

Setting the argument servicenet=True to get_conection will use the
Rackspace ServiceNet network to access Cloud Files (and not the public
network) :

    >>> import cloudfiles
    >>> conn = cloudfiles.get_connection('jsmith', '1234567890', \
        servicenet=True)
    >>> conn.connection_args[0]
    'snet-storage4.clouddrive.com'

If you define the environment variable RACKSPACE_SERVICENET it will
automatically connect via the servicenet network.

Creating Containers and adding Objects to them:

    >>> pic_container = conn.create_container('pictures')
    >>> my_dog = pic_container.create_object('fido.jpg')
    >>> my_dog.load_from_filename('images/IMG-0234.jpg')
    >>> text_obj = pic_container.create_object('sample.txt')
    >>> text_obj.write('This is not the object you are looking for.\\n')
    >>> text_obj.read()
    'This is not the object you are looking for.'

Object instances support streaming through the use of a generator:

    >>> deb_iso = pic_container.get_object('debian-40r3-i386-netinst.iso')
    >>> f = open('/tmp/debian.iso', 'w')
    >>> for chunk in deb_iso.stream():
    ..     f.write(chunk)
    >>> f.close()

Marking a Container as CDN-enabled/public with a TTL of 30 days

    >>> pic_container.make_public(2592000)
    >>> pic_container.public_uri()
    'http://c0001234.cdn.cloudfiles.rackspacecloud.com'
    >>> my_dog.public_uri()
    'http://c0001234.cdn.cloudfiles.rackspacecloud.com/fido.jpg'

Set the logs retention on CDN-enabled/public Container

    >>> pic_container.log_retention(True)

See COPYING for license information.
"""

import warnings

from cloudfiles.connection     import Connection, ConnectionPool
from cloudfiles.container      import Container
from cloudfiles.storage_object import Object
from cloudfiles.consts         import __version__, \
us_authurl, uk_authurl

warnings.warn("python-cloudfiles has been deprecated as of August 1, 2013. "
              "Please see https://github.com/openstack/python-swiftclient.",
              DeprecationWarning)

def get_connection(*args, **kwargs):
    """
    Helper function for creating connection instances.

    @type username: string
    @param username: a Mosso username
    @type api_key: string
    @param api_key: a Mosso API key
    @rtype: L{Connection}
    @returns: a connection object
    """
    return Connection(*args, **kwargs)
