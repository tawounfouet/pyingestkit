from __future__ import annotations

import unittest

import httpx

from pyingestkit.sources.http import HttpRequest, HttpTimeoutError, HttpTransportError, HttpxClient


class HttpxClientTests(unittest.TestCase):
    def test_mock_transport_returns_framework_response(self) -> None:
        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(200, headers={"Content-Type": "text/plain"}, content=b"hello")

        client = HttpxClient(transport=httpx.MockTransport(handler))
        try:
            response = client.send(HttpRequest(method="GET", url="https://example.org/data"))
        finally:
            client.close()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content, b"hello")
        self.assertEqual(response.content_type, "text/plain")

    def test_timeout_is_mapped_to_framework_exception(self) -> None:
        def handler(request: httpx.Request) -> httpx.Response:
            raise httpx.ReadTimeout("slow", request=request)

        client = HttpxClient(transport=httpx.MockTransport(handler))
        try:
            with self.assertRaises(HttpTimeoutError):
                client.send(HttpRequest(method="GET", url="https://example.org/data"))
        finally:
            client.close()

    def test_transport_error_is_mapped_to_framework_exception(self) -> None:
        def handler(request: httpx.Request) -> httpx.Response:
            raise httpx.ConnectError("offline", request=request)

        client = HttpxClient(transport=httpx.MockTransport(handler))
        try:
            with self.assertRaises(HttpTransportError):
                client.send(HttpRequest(method="GET", url="https://example.org/data"))
        finally:
            client.close()


if __name__ == "__main__":
    unittest.main()
