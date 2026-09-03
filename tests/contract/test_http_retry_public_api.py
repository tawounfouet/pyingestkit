from __future__ import annotations

import unittest

import pyingestkit.retry as retry_api
import pyingestkit.sources.http as http_api


class HttpRetryPublicApiTests(unittest.TestCase):
    def test_http_namespace_contract(self) -> None:
        self.assertEqual(
            set(http_api.__all__),
            {
                "HttpClient",
                "HttpError",
                "HttpRequest",
                "HttpResponse",
                "HttpSource",
                "HttpStatusError",
                "HttpTimeoutError",
                "HttpTransportError",
                "HttpxClient",
                "QueryValue",
            },
        )

    def test_retry_namespace_contract(self) -> None:
        self.assertEqual(
            set(retry_api.__all__),
            {
                "DEFAULT_RETRY_METHODS",
                "DEFAULT_RETRY_STATUS_CODES",
                "RetryAttempt",
                "RetryPolicy",
                "parse_retry_after",
            },
        )


if __name__ == "__main__":
    unittest.main()
