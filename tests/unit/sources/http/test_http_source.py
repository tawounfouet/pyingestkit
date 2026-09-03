from __future__ import annotations

import unittest

import httpx

from pyingestkit.retry import RetryPolicy
from pyingestkit.sources.http import HttpSource, HttpStatusError, HttpxClient


class HttpSourceTests(unittest.TestCase):
    def test_503_is_retried_then_succeeds(self) -> None:
        calls = 0
        sleeps: list[float] = []

        def handler(request: httpx.Request) -> httpx.Response:
            nonlocal calls
            calls += 1
            if calls < 3:
                return httpx.Response(503, request=request)
            return httpx.Response(200, request=request, content=b"ok")

        client = HttpxClient(transport=httpx.MockTransport(handler))
        source = HttpSource(
            "https://example.org/data",
            client=client,
            retry=RetryPolicy(
                max_attempts=3,
                initial_delay_seconds=0.1,
                max_delay_seconds=1,
                jitter=False,
                sleep=sleeps.append,
            ),
        )
        try:
            response = source.fetch_response()
        finally:
            client.close()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(calls, 3)
        self.assertEqual(sleeps, [0.1, 0.2])

    def test_404_is_not_retried(self) -> None:
        calls = 0

        def handler(request: httpx.Request) -> httpx.Response:
            nonlocal calls
            calls += 1
            return httpx.Response(404, request=request)

        client = HttpxClient(transport=httpx.MockTransport(handler))
        source = HttpSource(
            "https://example.org/missing",
            client=client,
            retry=RetryPolicy(max_attempts=3, sleep=lambda seconds: None),
        )
        try:
            with self.assertRaises(HttpStatusError):
                source.fetch_response()
        finally:
            client.close()
        self.assertEqual(calls, 1)

    def test_post_is_not_retried_by_default(self) -> None:
        calls = 0

        def handler(request: httpx.Request) -> httpx.Response:
            nonlocal calls
            calls += 1
            return httpx.Response(503, request=request)

        client = HttpxClient(transport=httpx.MockTransport(handler))
        source = HttpSource(
            "https://example.org/submit",
            method="POST",
            client=client,
            retry=RetryPolicy(max_attempts=3, sleep=lambda seconds: None),
        )
        try:
            with self.assertRaises(HttpStatusError):
                source.fetch_response()
        finally:
            client.close()
        self.assertEqual(calls, 1)

    def test_retry_after_header_is_respected_and_bounded(self) -> None:
        calls = 0
        sleeps: list[float] = []

        def handler(request: httpx.Request) -> httpx.Response:
            nonlocal calls
            calls += 1
            if calls == 1:
                return httpx.Response(429, request=request, headers={"Retry-After": "20"})
            return httpx.Response(200, request=request, content=b"ok")

        client = HttpxClient(transport=httpx.MockTransport(handler))
        source = HttpSource(
            "https://example.org/rate-limited",
            client=client,
            retry=RetryPolicy(
                max_attempts=2,
                initial_delay_seconds=0.1,
                max_delay_seconds=5,
                jitter=False,
                sleep=sleeps.append,
            ),
        )
        try:
            response = source.fetch_response()
        finally:
            client.close()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(sleeps, [5.0])

    def test_redirects_are_followed_by_default(self) -> None:
        def handler(request: httpx.Request) -> httpx.Response:
            if request.url.path == "/start":
                return httpx.Response(302, request=request, headers={"Location": "/final"})
            return httpx.Response(200, request=request, content=b"done")

        client = HttpxClient(transport=httpx.MockTransport(handler))
        source = HttpSource("https://example.org/start", client=client)
        try:
            response = source.fetch_response()
        finally:
            client.close()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.url, "https://example.org/final")


if __name__ == "__main__":
    unittest.main()
