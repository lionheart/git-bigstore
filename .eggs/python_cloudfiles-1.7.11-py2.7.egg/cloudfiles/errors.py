"""
exception classes

See COPYING for license information.
"""

class Error(StandardError):
    """
    Base class for all errors and exceptions
    """
    pass


class ResponseError(Error):
    """
    Raised when the remote service returns an error.
    """
    def __init__(self, status, reason):
        self.status = status
        self.reason = reason
        Error.__init__(self)

    def __str__(self):
        return '%d: %s' % (self.status, self.reason)

    def __repr__(self):
        return '%d: %s' % (self.status, self.reason)


class NoSuchContainer(Error):
    """
    Raised on a non-existent Container.
    """
    pass


class NoSuchObject(Error):
    """
    Raised on a non-existent Object.
    """
    pass


class ContainerNotEmpty(Error):
    """
    Raised when attempting to delete a Container that still contains Objects.
    """
    def __init__(self, container_name):
        self.container_name = container_name
        Error.__init__(self)

    def __str__(self):
        return "Cannot delete non-empty Container %s" % self.container_name

    def __repr__(self):
        return "%s(%s)" % (self.__class__.__name__, self.container_name)


class ContainerExists(Error):
    """
    Raised when attempting to create a Container when the container already
    exists.
    """
    pass


class InvalidContainerName(Error):
    """
    Raised for invalid storage container names.
    """
    pass


class InvalidObjectName(Error):
    """
    Raised for invalid storage object names.
    """
    pass


class InvalidMetaName(Error):
    """
    Raised for invalid metadata names.
    """
    pass


class InvalidMetaValue(Error):
    """
    Raised for invalid metadata value.
    """
    pass


class InvalidUrl(Error):
    """
    Not a valid url for use with this software.
    """
    pass


class InvalidObjectSize(Error):
    """
    Not a valid storage_object size attribute.
    """
    pass


class IncompleteSend(Error):
    """
    Raised when there is a insufficient amount of data to send.
    """
    pass


class ContainerNotPublic(Error):
    """
    Raised when public features of a non-public container are accessed.
    """
    pass


class CDNNotEnabled(Error):
    """
    CDN is not enabled for this account.
    """
    pass


class AuthenticationFailed(Error):
    """
    Raised on a failure to authenticate.
    """
    pass


class AuthenticationError(Error):
    """
    Raised when an unspecified authentication error has occurred.
    """
    pass
