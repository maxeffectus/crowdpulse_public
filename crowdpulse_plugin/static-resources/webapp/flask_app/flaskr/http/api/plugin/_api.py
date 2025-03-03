import logging
from typing import Literal

from .._base_api import BaseApi
from ... import NoAuthHandler
from ....common import format_uuid

_logger = logging.getLogger(__name__)


class PluginApi(BaseApi):

    def __init__(self, port: int):
        super().__init__(f"http://127.0.0.1:{port}")

    def send_credentials(self, user: str, token: str):
        self.http_post('/plugin/token', data={'user': user, 'token': token})

    def send_diagnostics_event(self, level: Literal['info', 'warning', 'error'], caption: str, description: str):
        self.http_post(
            '/plugin/sendDiagEvent',
            data={
                'level': level,
                'caption': caption,
                'description': description,
                },
            )

    def send_analytics_event(
            self,
            type_: Literal['tigre.engagementBelowLevel', 'tigre.engagementAboveLevel'],
            camera_id: str,
            caption: str = '',
            description: str = '',
            **attributes,
            ):
        self.http_post(
            f'/device/{format_uuid(camera_id, with_curly=True)}/sendEvent',
            data={
                'type': type_,
                'caption': caption,
                'description': description,
                'attributes': {**attributes},
                })

    def list_active_devices(self):
        return self.http_get('/device/listActive')

    def http_get(self, path, params=None, **kwargs):
        return super().http_get(path, params, with_credentials=False, **kwargs)

    def _http_request(self, method, path, **kwargs):
        response = self._request(method, path, **kwargs)
        if len(response.content) > 1000:
            resp_logger = _logger.getChild('http_resp.large')
        else:
            resp_logger = _logger.getChild('http_resp.small')
        resp_logger.debug("%s %s: JSON response:\n%s", method, path, response.json)
        if response.status_code != 200:
            raise PluginHttpError(
                f"{method} {path} responded with code {response.status_code}: {response.json}")
        return self._retrieve_data(response, response.json)

    def http_url(self, path, with_credentials: bool):
        if with_credentials:
            raise NotImplementedError("Credentials are not supported by the plugin")
        path = path.lstrip('/')
        return f"{self._base_url}/{path}"

    def _make_auth_handler(self):
        return NoAuthHandler()

    def _request(self, method: str, path: str, ssl_enabled=False, params=None, **kwargs):
        return super()._request(method, path, ssl_enabled=False, params=None, **kwargs)


class PluginHttpError(Exception):
    pass
