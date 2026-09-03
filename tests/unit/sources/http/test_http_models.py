from __future__ import annotations

import unittest

from pyingestkit.sources.http import HttpRequest, HttpResponse


class HttpModelsTests(unittest.TestCase):
    def test_request_normalizes_method_and_redacts_repr(self) -> None:
        request = HttpRequest(
            method="get",
            url="https://user:password@example.org/data?token=secret&year=2026",
            headers={"Authorization": "Bearer top-secret", "Accept": "application/json"},
        )
        self.assertEqual(request.method, "GET")
        rendered = repr(request)
        self.assertNotIn("password", rendered)
        self.assertNotIn("top-secret", rendered)
        self.assertNotIn("token=secret", rendered)
        self.assertIn("REDACTED", rendered)

    def test_request_rejects_unbounded_timeout(self) -> None:
        with self.assertRaises(ValueError):
            HttpRequest(method="GET", url="https://example.org", timeout_seconds=0)

    def test_response_does_not_repr_body_or_secret_headers(self) -> None:
        response = HttpResponse(
            status_code=200,
            headers={"Set-Cookie": "session=secret", "Content-Type": "application/json"},
            content=b'{"secret":"payload"}',
            url="https://example.org/data",
        )
        rendered = repr(response)
        self.assertNotIn("session=secret", rendered)
        self.assertNotIn("payload", rendered)
        self.assertEqual(response.content_length, len(response.content))
        self.assertTrue(response.is_success)


if __name__ == "__main__":
    unittest.main()
