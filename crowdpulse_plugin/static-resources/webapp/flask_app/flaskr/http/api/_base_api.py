import json
import logging
import time
import urllib
from abc import ABCMeta, abstractmethod
from pprint import pformat
from urllib.parse import urlparse

from .. import NonJsonResponse, http_request

_logger = logging.getLogger(__name__)

DEFAULT_HTTP_TIMEOUT = 10


class BaseApi(metaclass=ABCMeta):

    def __init__(self, base_url: str):
        self._base_url = base_url
        self.auth_handler = self._make_auth_handler()

    @abstractmethod
    def _http_request(self, method, path, **kwargs):
        pass

    @abstractmethod
    def http_url(self, path, with_credentials: bool):
        pass

    @abstractmethod
    def _make_auth_handler(self):
        pass

    def http_get(self, path, params=None, with_credentials=True, **kwargs):
        params_str = pformat(params, indent=4)
        if '\n' in params_str or len(params_str) > 60:
            params_str = '\n' + params_str
        _logger.debug(
            'GET %s, params: %s',
            self.http_url(path, with_credentials), params_str)
        assert 'data' not in kwargs
        assert 'json' not in kwargs
        return self._http_request('GET', path, params=params, **kwargs)

    def http_post(self, path, data, timeout: float = DEFAULT_HTTP_TIMEOUT, **kwargs):
        return self._make_json_request('POST', path, data, timeout, **kwargs)

    def _make_json_request(self, method, path, data, timeout, with_credentials=False, **kwargs):
        data_str = json.dumps(data)
        if len(data_str) > 60:
            data_str = '\n' + json.dumps(data, indent=4)
        _logger.debug(
            '%s %s, timeout: %s sec, payload:\n%s',
            method, self.http_url(path, with_credentials=with_credentials), timeout, data_str)
        return self._http_request(method, path, json=data, timeout=timeout, **kwargs)

    def _request(self, method: str, path: str, ssl_enabled=True, params=None, **kwargs):
        if params:
            # Server, which uses QUrlQuery doesn't support spaces, encoded as "+".
            # See https://doc.qt.io/qt-5/qurlquery.html#handling-of-spaces-and-plus.
            params = urllib.parse.urlencode(params, quote_via=urllib.parse.quote)
            path = f'{path}?{params}'
        if 'json' in kwargs:
            content = kwargs['json']
        elif 'data' in kwargs:
            content = kwargs['data']
        else:
            content = None
        headers = kwargs.get('headers', {})
        started_at = time.perf_counter()
        url = self.http_url(path, with_credentials=False)
        response = http_request(
            method,
            url,
            content,
            headers=headers,
            auth_handler=self.auth_handler,
            ssl_enabled=ssl_enabled,
        )
        _logger.info(
            "HTTP API %(method)s %(url)s, "
            "took %(duration).3f sec, "
            "status %(status)s"
            "", {
                'method': method,
                'url': url,
                'path': path,
                'duration': time.perf_counter() - started_at,
                'status': response.status_code,
            })
        return response

    def _retrieve_data(self, response, response_json):
        if not response.content:
            _logger.warning("Empty response.")
            return None
        if response_json is None:
            raise NonJsonResponse(self._base_url, response, {})
        if isinstance(response_json, dict) and 'reply' in response_json:
            return response_json['reply']
        return response_json
