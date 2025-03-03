import json
import ssl
import urllib.parse
import urllib.request
from abc import ABCMeta
from abc import abstractmethod
from contextlib import closing
from http.client import HTTPResponse as BaseHttpResponse, HTTPConnection
from http.client import HTTPSConnection as BaseHttpsConnection
from sqlite3 import connect
from typing import Any, Protocol
from typing import Iterable
from typing import Mapping
from typing import Optional
from typing import Union

DEFAULT_HTTP_TIMEOUT = 30


def http_request(
        method: str,
        url: str,
        content: Optional[Union[Iterable[Mapping[str, Any]], Mapping[str, Any], bytes]] = None,
        *,
        headers: Optional[Mapping[str, Any]] = None,
        timeout: float = DEFAULT_HTTP_TIMEOUT,
        auth_handler: Optional['AuthHandler'] = None,
        ssl_enabled: bool = True,
        ) -> 'HttpResponse':
    if timeout is None:
        raise RuntimeError("Timeout must not be None; otherwise a request may be endless")
    if headers is None:
        headers = {}
    headers = {'Connection': 'Keep-Alive', **headers}
    request = _HttpRequest(method, url, content, headers)
    parsed_url = urllib.parse.urlparse(url)

    with closing(
            _https_connection(
                hostname=parsed_url.hostname,
                port=parsed_url.port,
                auth_handler=auth_handler,
                timeout=timeout) if ssl_enabled else
            _http_connection(
                hostname=parsed_url.hostname,
                port=parsed_url.port,
                timeout=timeout,
                )
            ) as connection:
        try:
            return connection.send_request(request)
        except (ConnectionError, ssl.SSLEOFError, ssl.SSLZeroReturnError):
            raise HttpConnectionError()
        except TimeoutError:
            raise HttpReadTimeout()


def _https_connection(hostname, port, auth_handler, timeout):
    return _HttpsConnection(
        hostname,
        port,
        ssl._create_unverified_context(),  # Out of the box Mediaserver has got a self-signed SSL certificate.
        auth_handler,
        timeout=timeout,
        )


def _http_connection(hostname, port, timeout):
    return _HTTPConnection(
        host=hostname,
        port=port,
        timeout=timeout,
        )


class _HttpRequest:

    def __init__(
            self,
            method: str,
            url: str,
            content: Optional[Union[Iterable[Mapping[str, Any]], Mapping[str, Any], bytes]] = None,
            headers: Optional[Mapping[str, str]] = None,
            ):
        self.method = method
        self.url = url
        if headers is None:
            headers = {}
        if content is not None:
            if isinstance(content, bytes):
                headers = {**{'Content-Type': 'application/octet-stream', **headers}}
            elif isinstance(content, (Iterable, Mapping)):
                content = json.dumps(content)
                headers = {**{'Content-Type': 'application/json', **headers}}
            else:
                raise RuntimeError(f"Unsupported content type: {content.__class__.__name__}")
        else:
            headers = {**{'Content-Length': 0, **headers}}  # To avoid adding Transfer-Encoding
        self.headers = headers
        self.content = content


class HttpResponse:

    def __init__(self, response: BaseHttpResponse, request_method: str, url: str):
        self.status_code: int = response.status
        self.reason: str = response.reason
        self.headers = response.headers
        self.request_method = request_method
        self.url = url
        self.content = response.read()
        try:
            self.json = json.loads(self.content.decode('utf-8'))
        except ValueError:
            self.json = None


class AuthHandler(metaclass=ABCMeta):

    def __init__(self, username: str, password: str):
        self.username = username
        self.password = password

    @abstractmethod
    def authorize_request(self, request: _HttpRequest):
        pass

    @abstractmethod
    def make_authorization_header(self) -> str:
        pass

    def handle_failed_request(self, request: _HttpRequest, response: HttpResponse):
        raise CannotHandleRequest("Handling not supported")

    def with_credentials(self, username: str, password: str):
        return self.__class__(username, password)

    @abstractmethod
    def subsume_from_master(self, master: 'AuthHandler'):
        pass


class TokenProvider(Protocol):

    def obtain_token(self, username: str, password: str) -> str:
        ...

    @staticmethod
    def must_be_subsumed() -> bool:
        ...


class HttpBearerAuthHandler(AuthHandler):

    def __init__(self, username: str, password: str, token_provider: TokenProvider):
        super().__init__(username, password)
        self._token_provider = token_provider
        self._token: Optional[str] = None
        self._refresh_old_token = True

    def authorize_request(self, request):
        request.headers['Authorization'] = self.make_authorization_header()

    def make_authorization_header(self) -> str:
        return f'Bearer {self.get_token()}'

    def get_token(self) -> str:
        if self._token is None:
            self.refresh_token()
        return self._token

    def refresh_token(self):
        self._token = self._token_provider.obtain_token(self.username, self.password)

    def subsume_from_master(self, master: 'HttpBearerAuthHandler'):
        """Copy username and password, leaving token the same.

        If, after merging, the slave decides to reject the token, a new token
        will be re-issued by the slave.
        """
        # It is just a coincidence that all available authentication types have
        # username and password.
        self.username = master.username
        self.password = master.password
        if master._token_provider.must_be_subsumed():
            self._token_provider = master._token_provider


class NoAuthHandler(AuthHandler):

    def __init__(self):
        super().__init__('no', 'auth')

    def subsume_from_master(self, master: AuthHandler):
        pass

    def authorize_request(self, request):
        pass

    def make_authorization_header(self) -> str:
        pass


class _HTTPConnection(HTTPConnection):

    def __init__(self, host, port, timeout):
        super().__init__(host, port, timeout)

    def send_request(self, request: '_HttpRequest') -> 'HttpResponse':
        super().request(request.method, request.url, request.content, request.headers)
        response = HttpResponse(super().getresponse(), request.method, request.url)
        return response


class _HttpsConnection(BaseHttpsConnection):

    def __init__(
            self,
            host: str,
            port: int,
            ssl_context: ssl.SSLContext,
            auth_handler: Optional['AuthHandler'] = None,
            timeout: Optional[float] = None,
            ):
        super().__init__(host, port, timeout=timeout, context=ssl_context)
        self._auth_handler = auth_handler

    def send_request(self, request: _HttpRequest) -> HttpResponse:
        if self._auth_handler is not None:
            try:
                self._auth_handler.authorize_request(request)
            except _CannotAuthorizeRequest:
                pass
        super().request(request.method, request.url, request.content, request.headers)
        response = HttpResponse(super().getresponse(), request.method, request.url)
        if response.status_code in (401, 403) and self._auth_handler is not None:
            try:
                self._auth_handler.handle_failed_request(request, response)
            except CannotHandleRequest:
                return response
            super().request(request.method, request.url, request.content, request.headers)
            response = HttpResponse(super().getresponse(), request.method, request.url)
        return response


class HttpReadTimeout(Exception):
    pass


class HttpConnectionError(Exception):
    pass


class CannotHandleRequest(Exception):
    pass


class _CannotAuthorizeRequest(CannotHandleRequest):
    pass


class NonJsonResponse(Exception):
    pass
