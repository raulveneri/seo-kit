"""Small, bounded HTTPS client for auditing public sites and fixed API hosts."""

import http.client
import ipaddress
import socket
import ssl
import time
from dataclasses import dataclass
from urllib.parse import urljoin, urlsplit


USER_AGENT = "seo-kit-audit/1.0 (+bounded SEO audit)"


def checked_url(url):
    parsed = urlsplit(url)
    if parsed.scheme != "https" or not parsed.hostname or parsed.username or parsed.password or parsed.port not in (None, 443):
        raise ValueError("only public HTTPS URLs on port 443 are allowed")
    if parsed.fragment:
        url = url.split("#", 1)[0]
    return url


def public_address(host):
    addresses = {item[4][0] for item in socket.getaddrinfo(host, 443, type=socket.SOCK_STREAM)}
    if not addresses or any(not ipaddress.ip_address(address).is_global for address in addresses):
        raise ValueError("target DNS must resolve only to public addresses")
    return sorted(addresses)[0]


class PinnedHTTPSConnection(http.client.HTTPSConnection):
    def __init__(self, host, address, timeout):
        super().__init__(host, timeout=timeout, context=ssl.create_default_context())
        self.address = address

    def connect(self):
        raw = socket.create_connection((self.address, 443), self.timeout)
        self.sock = self._context.wrap_socket(raw, server_hostname=self.host)


@dataclass
class Response:
    url: str
    status: int
    headers: dict
    body: bytes
    redirects: list


class SafeClient:
    def __init__(self, *, max_requests=300, max_bytes=2_000_000, timeout=10, delay=0.2, deadline=None):
        self.max_requests = max_requests
        self.max_bytes = max_bytes
        self.timeout = timeout
        self.delay = delay
        self.requests = 0
        self.last_request = 0.0
        self.deadline = deadline
        self.disk_guard = None

    def remaining_time(self):
        if self.deadline is None:
            return self.timeout
        remaining = self.deadline - time.monotonic()
        if remaining <= 0:
            raise ValueError('time budget exhausted')
        return min(self.timeout, remaining)

    def fetch(self, url, *, method="GET", body=None, headers=None, allow_redirects=True, authorize=None):
        url = checked_url(url)
        original_origin = urlsplit(url).netloc.lower()
        redirects = []
        for _ in range(6):
            if self.disk_guard is not None and not self.disk_guard():
                raise ValueError('disk budget exhausted')
            if authorize is not None and not authorize(url):
                raise ValueError('request disallowed by crawl policy')
            if self.requests >= self.max_requests:
                raise ValueError("request budget exhausted")
            self.remaining_time()
            parsed = urlsplit(url)
            address = public_address(parsed.hostname)
            wait = self.delay - (time.monotonic() - self.last_request)
            if wait > 0:
                if self.deadline is not None and wait >= self.deadline - time.monotonic():
                    raise ValueError('time budget exhausted before the next permitted request')
                time.sleep(wait)
            connection = PinnedHTTPSConnection(parsed.hostname, address, self.remaining_time())
            request_headers = {"User-Agent": USER_AGENT, "Accept": "text/html,application/xml,application/json,*/*;q=0.5", "Accept-Encoding": "identity", **(headers or {})}
            path = parsed.path or "/"
            if parsed.query:
                path += "?" + parsed.query
            try:
                self.requests += 1
                self.last_request = time.monotonic()
                connection.request(method, path, body=body, headers=request_headers)
                response = connection.getresponse()
                if hasattr(response, 'read1'):
                    chunks, size = [], 0
                    while size <= self.max_bytes:
                        remaining = self.remaining_time()
                        stream_socket = getattr(connection, 'sock', None) or getattr(getattr(getattr(response, 'fp', None), 'raw', None), '_sock', None)
                        if stream_socket:
                            stream_socket.settimeout(remaining)
                        chunk = response.read1(min(65536, self.max_bytes + 1 - size))
                        self.remaining_time()
                        if not chunk:
                            break
                        chunks.append(chunk)
                        size += len(chunk)
                    data = b''.join(chunks)
                else:
                    data = response.read(self.max_bytes + 1)
                if len(data) > self.max_bytes:
                    raise ValueError("response size limit exceeded")
                response_headers = {}
                for key, value in response.getheaders():
                    key = key.lower()
                    response_headers[key] = response_headers[key] + ', ' + value if key in response_headers else value
                if response_headers.get("content-encoding", "identity").lower() != "identity":
                    raise ValueError("compressed response is not supported by the bounded client")
                result = Response(url, response.status, response_headers, data, redirects.copy())
            except http.client.HTTPException as error:
                raise ValueError(f'invalid HTTP response: {type(error).__name__}') from error
            finally:
                connection.close()
            if result.status not in (301, 302, 303, 307, 308) or not allow_redirects:
                return result
            location = result.headers.get("location")
            if not location:
                return result
            target = checked_url(urljoin(url, location))
            if urlsplit(target).netloc.lower() != original_origin:
                raise ValueError("redirect left the allowed origin")
            redirects.append({"from": url, "status": result.status, "to": target})
            url = target
            if result.status == 303:
                method, body = "GET", None
        raise ValueError("redirect limit exceeded")
