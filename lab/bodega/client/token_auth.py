"""Authentication tools for the Django REST Framework."""

import requests


class TokenAuth(requests.auth.AuthBase):
    """Custom requests authentication class.

    Performs token authentication in the style that Django REST Framework
    expects.
    """

    def __init__(self, token):
        self.token = token

    def __call__(self, request):
        """Authenticate by setting the 'Authorization' header.

        For example, with a value like 'Token abcd1234'.
        """
        request.headers['Authorization'] = 'Token %s' % self.token
        return request

    def __repr__(self):
        """Represent the TokenAuth without sharing the actual token."""
        return 'TokenAuth("***")'

    def __str__(self):
        """Share the representation above."""
        return repr(self)
