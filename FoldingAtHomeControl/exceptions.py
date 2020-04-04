"""FoldingAtHomeControl Exceptions."""


class FoldingAtHomeControlException(Exception):
    """Base class for FoldingAtHomeControl exceptions"""

    pass


class FoldingAtHomeControlAuthenticationFailed(FoldingAtHomeControlException):
    """Authentication Failed."""

    pass


class FoldingAtHomeControlAuthenticationRequired(FoldingAtHomeControlException):
    """Authentication Required."""

    pass


class FoldingAtHomeControlConnectionFailed(FoldingAtHomeControlException):
    """Connection failed."""

    pass


class FoldingAtHomeControlNotConnected(FoldingAtHomeControlException):
    """Socket is not connected."""

    pass
