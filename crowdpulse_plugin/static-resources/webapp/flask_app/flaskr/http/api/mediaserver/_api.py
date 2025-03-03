import logging
import urllib
from collections.abc import Collection
from typing import Literal, Mapping, Any, Sequence
from urllib.parse import urlparse

from ._analytics import AnalyticsTrack
from ._mediaserver_http_exceptions import (
    MediaserverApiReadTimeout,
    MediaserverApiConnectionError,
    Forbidden,
    TooManyAttempts,
    BadRequest,
    Unauthorized,
    OldSessionToken,
    NotFound,
    MediaserverApiHttpError,
)
from .._base_api import BaseApi
from ... import (
    HttpReadTimeout,
    HttpConnectionError,
    HttpBearerAuthHandler,
    NoAuthHandler,
)

_logger = logging.getLogger(__name__)

_DEFAULT_API_USER = 'admin'
_INITIAL_API_PASSWORD = 'admin'


class MediaserverApiV3(BaseApi):

    def __init__(self, base_url: str, auth_type: Literal['no_auth', 'bearer'] = 'bearer'):
        parsed = urlparse(base_url)
        self._auth_type = auth_type
        self._scheme = 'https'
        if parsed.port is not None:
            self._netloc = parsed.netloc
        else:
            self._netloc = parsed.netloc + ':7001'
        user = parsed.username or _DEFAULT_API_USER
        password = parsed.password or _INITIAL_API_PASSWORD
        self._user = user
        self._password = password
        super().__init__(base_url)

    def _make_auth_handler(self):
        if self._auth_type == 'bearer':
            return HttpBearerAuthHandler(self._user, self._password, self._make_token_provider())
        elif self._auth_type == 'no_auth':
            return NoAuthHandler()
        raise NotImplementedError(f"Unknown auth type {self._auth_type} provided")

    def _make_token_provider(self):
        return self.__class__(
            self.http_url('', with_credentials=False),
            auth_type='no_auth',
            )

    def is_online(self):
        try:
            self.http_get('/api/ping')
        except MediaserverApiConnectionError:
            return False
        else:
            return True

    def get_user_by_name(self, name: str) -> Mapping[str, Any]:
        return self.http_get(f'rest/v3/users/{name}')

    def list_devices(self) -> Collection[Mapping[str, Any]]:
        return self.http_get('/rest/v3/devices')

    def obtain_token(self, username: str, password: str):
        url = f'rest/v3/login/sessions'
        try:
            response = self.http_post(
                url,
                data={
                    'username': username,
                    'password': password,
                    })
        except Forbidden as e:
            if "Too many attempts, try again later" in str(e):
                raise TooManyAttempts(url)
            raise
        return response['token']

    def list_analytics_objects_tracks(self, camera_id=None, start_time=None, end_time=None, **params) -> Sequence[AnalyticsTrack]:
        submitted_params = {}
        if camera_id is not None:
            submitted_params = {'deviceId': camera_id}
        if start_time is not None:
            submitted_params = {'startTime': start_time}
        if end_time is not None:
            submitted_params = {**submitted_params, 'endTime': end_time}
        submitted_params = {**submitted_params, **params}
        response = self.http_get('/ec2/analyticsLookupObjectTracks', params=submitted_params)
        result = [AnalyticsTrack(track) for track in response]
        result = sorted(result, key=lambda k: k.time_period().start_ms)
        return result

    def _http_request(self, method, path, **kwargs):
        try:
            response = self._request(method, path, **kwargs)
        except HttpReadTimeout as e:
            raise MediaserverApiReadTimeout(self._netloc, '%r: %s %r: %s' % (self, method, path, e))
        except HttpConnectionError as e:
            raise MediaserverApiConnectionError(self._netloc, '%r: %s %r: %s' % (self, method, path, e))
        if len(response.content) > 1000:
            resp_logger = _logger.getChild('http_resp.large')
        else:
            resp_logger = _logger.getChild('http_resp.small')
        resp_logger.debug("%s %s: JSON response:\n%s", method, path, response.json)
        self._raise_for_status(response, response.json)
        return self._retrieve_data(response, response.json)

    def http_url(self, path, with_credentials=False):
        path = path.lstrip('/')
        if with_credentials:
            return f'{self._scheme}://{self._userinfo()}@{self._netloc}/{path}'
        else:
            return f'{self._scheme}://{self._netloc}/{path}'

    def _userinfo(self):
        return ':'.join((
            self._quote_userinfo_part(self._user),
            self._quote_userinfo_part(self._password),
            ))

    @staticmethod
    def _quote_userinfo_part(s):
        """Encode username and password correctly.

        See: RFC 3986
        See: https://serverfault.com/a/1001324/208965
        userinfo    = *( unreserved / pct-encoded / sub-delims / ":" )
        unreserved  = ALPHA / DIGIT / "-" / "." / "_" / "~"
        pct-encoded = "%" HEXDIG HEXDIG
        sub-delims  = "!" / "$" / "&" / "'" / "(" / ")"

        I.e., sub-delims are allowed and may not be quoted.
        """
        return urllib.parse.quote(s, safe="!$&'()*+,;=")

    def _raise_for_status(self, response, response_json):
        if isinstance(response_json, dict):
            vms_error_dict = response_json
        else:
            vms_error_dict = {}
        vms_error_code = int(vms_error_dict.get('error', 0))
        vms_error_string = vms_error_dict.get('errorString', '')
        if vms_error_code:
            _logger.warning(
                "Mediaserver API responded with an error. "
                "Status code: %d. "
                "Error: %r",
                response.status_code,
                vms_error_dict)
        if response.status_code == 400:
            raise BadRequest(self._netloc, response, vms_error_dict)
        auth_result = response.headers.get('x-auth-result', '')
        if response.status_code == 401:
            raise Unauthorized(self._netloc, response, vms_error_dict)
        # Old API returns either 3 or 4 for requests failed due to insufficient user rights.
        # In tests there are no endpoints that returns vms error 3 and HTTP 200 OK on Forbidden
        # request. New API must return error code 4.
        if response.status_code == 403 or vms_error_code == 4:
            if auth_result == 'Auth_WrongSessionToken':
                raise OldSessionToken(self._netloc, response, vms_error_dict)
            raise Forbidden(self._netloc, response, vms_error_dict)
        if response.status_code == 404 or vms_error_code == 9:
            raise NotFound(self._netloc, response, vms_error_dict)
        # New API returns 422 status code instead of 401 if invalid credentials were passed.
        if response.status_code == 422:
            if 'Wrong password' in vms_error_string:
                raise Unauthorized(self._netloc, response, vms_error_dict)
            else:
                # New API returns 422 status in case when some parameter has an inappropriate value or missed
                raise BadRequest(self._netloc, response, vms_error_dict)
        if 400 <= response.status_code < 600 or vms_error_code != 0:
            raise MediaserverApiHttpError(self._netloc, response, vms_error_dict)
