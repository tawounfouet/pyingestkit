from __future__ import annotations

import unittest

import pyingestkit.retry as retry_api
import pyingestkit.sources.http as http_api
from pyingestkit.sources import Source


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

    def test_http_source_is_framework_source(self) -> None:
        from pyingestkit.sources.http import HttpSource

        self.assertTrue(issubclass(HttpSource, Source))
        self.assertTrue(callable(HttpSource.fetch))
        self.assertTrue(callable(HttpSource.fetch_response))

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
