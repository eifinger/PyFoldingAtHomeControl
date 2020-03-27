"""FoldingAtHomeControl Exceptions."""


class FoldingAtHomeControlAuthenticationFailed(Exception):
    """Authentication Failed."""

    pass


class FoldingAtHomeControlAuthenticationRequired(Exception):
    """Authentication Required."""

    pass


class FoldingAtHomeControlConnectionFailed(Exception):
    """Connection failed."""

    pass
