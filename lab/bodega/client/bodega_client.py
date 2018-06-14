"""REST API Client helper methods for Bodega web application(s)."""
import copy
import logging
import os

from enum import Enum
import requests
import yaml

from token_auth import TokenAuth

log = logging.getLogger(__name__)


class BodegaClientException(Exception):
    pass


class BodegaClientOperationFailure(BodegaClientException):
    pass


class BodegaClientTimeoutError(BodegaClientException):
    pass


class BodegaClientValueError(ValueError, BodegaClientException):
    pass


class OrderStatus(Enum):
    OPEN = 1
    FULFILLED = 2
    CLOSED = 3


class BodegaClient():
    """Client class for Bodega.

    This class assists in carrying out RESTful operations against Rubrik Bodega
    Web application. In general, this class is supposed to provide thin
    wrapping around CRUD operations exposed by Bodega.
    """

    def __init__(self, bodega_url=None, auth_token=None):
        self._get_bodega_credentials(bodega_url, auth_token)

    def _get_bodega_credentials(self, bodega_url=None, auth_token=None):
        if bodega_url and auth_token:
            log.debug('Client was initialized with both bodega_url and ' +
                      'auth_token, will not look in .bodega.conf.yml')
        else:
            log.debug('Client was not initialized with both bodega_url ' +
                      'and auth_token, will retrieve from .bodega.conf.yml')

            validation_url = bodega_url

            end_user_login_profile_file = os.environ.get(
                'BODEGA_CONF',
                os.path.join(os.path.expanduser('~'), '.bodega.conf.yml'))

            try:
                with open(end_user_login_profile_file, 'r') as bodega_profile:
                    bodega_auth_credentials = yaml.safe_load(bodega_profile)
                bodega_url = bodega_auth_credentials['url']
                auth_token = bodega_auth_credentials['token']
            except Exception:
                log.exception("Error loading configuration file %s" %
                              repr(end_user_login_profile_file), exc_info=True)
                raise

            if validation_url and validation_url != bodega_url:
                raise BodegaClientValueError(
                    'Given Bodega url (%s) does not match url found in the '
                    'config file (%s). Using a different Bodega instance is '
                    'currently not supported at this time.' %
                    (bodega_url, self.BODEGA_URL))

        self.BODEGA_TOKEN = TokenAuth(auth_token)
        self.BODEGA_URL = bodega_url

    def _endpoint_api_url(self, endpoint):
        return self.BODEGA_URL.rstrip('/') + '/' + endpoint.lstrip('/')

    def request(self, method, relative_uri, **kwargs):
        """Make an HTTP request on the and return the decoded JSON response."""
        endpoint_url = self._endpoint_api_url(relative_uri)

        new_kwargs = copy.copy(kwargs)
        new_kwargs['auth'] = self.BODEGA_TOKEN
        new_kwargs['verify'] = False

        response = requests.request(method, endpoint_url, **new_kwargs)
        log.debug('Make a request to %s with kwargs %s'
                  % (response.url, new_kwargs))

        response.raise_for_status()

        return response.json()

    def delete(self, relative_uri, **kwargs):
        """Make an HTTP DELETE request and return the decoded JSON response."""
        return self.request('DELETE', relative_uri, **kwargs)

    def get(self, relative_uri, **kwargs):
        """Make an HTTP GET request and return the decoded JSON response."""
        return self.request('GET', relative_uri, **kwargs)

    def patch(self, relative_uri, **kwargs):
        """Make an HTTP PATCH request and return the decoded JSON response."""
        return self.request('PATCH', relative_uri, **kwargs)

    def post(self, relative_uri, **kwargs):
        """Make an HTTP POST request and return the decoded JSON response."""
        return self.request('POST', relative_uri, **kwargs)

    def get_order(self, sid):
        return self.get('/orders/%s' % sid)

    def extend_order(self, sid, extend_delta, message=None):
        comment = 'Order has been extended for %s' % extend_delta
        if message:
            comment = '\n'.join([message, comment])
        return self.post('/order_updates/',
                         data={'order_sid': sid,
                               'comment': comment,
                               'time_limit_delta': extend_delta})

    def close_order(self, sid, message=None):
        comment = 'Closed order %s' % sid
        if message:
            comment = '\n'.join([message, comment])

        return self.post('/order_updates/',
                         data={'order_sid': sid,
                               'comment': comment,
                               'new_status': 'CLOSED'})
