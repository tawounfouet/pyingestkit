from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

import httpx

from pyingestkit import Job, Pipeline, RunContext, Step
from pyingestkit.artifacts import LocalArtifactStore
from pyingestkit.metadata import SQLiteMetadataStore
from pyingestkit.provenance import sha256_bytes
from pyingestkit.runtime import Runner
from pyingestkit.sources.http import HttpSource, HttpxClient

_PAYLOAD = b"raw-http-payload\n"


class FetchHttp(Step):
    def __init__(self, source: HttpSource) -> None:
        self.source = source

    def execute(self, context: RunContext, data: object) -> object:
        del data
        return self.source.fetch(context)


class HttpRawJob(Job):
    id = "demo.http_raw"

    def __init__(self, source: HttpSource) -> None:
        self.source = source

    def pipeline(self) -> Pipeline:
        return Pipeline([FetchHttp(self.source)])


class HttpRawProvenanceTests(unittest.TestCase):
    def test_http_bytes_become_raw_manifest_and_metadata_without_secrets(self) -> None:
        def handler(request: httpx.Request) -> httpx.Response:
            self.assertEqual(request.headers["Authorization"], "Bearer auth-secret")
            self.assertEqual(request.headers["Cookie"], "sid=cookie-secret")
            self.assertIn("query-token-secret", str(request.url))
            self.assertIn("param-api-secret", str(request.url))
            return httpx.Response(
                200,
                headers={
                    "Content-Type": "application/octet-stream",
                    "ETag": '"dataset-v7"',
                    "Last-Modified": "Wed, 02 Sep 2026 10:00:00 GMT",
                    "Set-Cookie": "session=response-cookie-secret",
                    "X-Auth-Token": "response-token-secret",
                },
                content=_PAYLOAD,
                request=request,
            )

        transport = httpx.MockTransport(handler)
        source = HttpSource(
            "https://api.example.test/files/data.bin?token=query-token-secret",
            params={"api_key": "param-api-secret", "page": 2},
            headers={
                "Authorization": "Bearer auth-secret",
                "Cookie": "sid=cookie-secret",
                "X-API-Key": "header-api-secret",
            },
            client=HttpxClient(transport=transport),
        )

        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp) / ".pyingest"
            metadata = SQLiteMetadataStore.for_workspace(workspace)
            result = Runner(LocalArtifactStore(workspace), metadata_store=metadata).run(
                HttpRawJob(source)
            )

            self.assertTrue(result.succeeded)
            records = metadata.list_artifacts(result.run_id)
            self.assertEqual(len(records), 1)
            record = records[0]
            self.assertEqual(record.status_code, 200)
            self.assertEqual(record.content_type, "application/octet-stream")
            self.assertEqual(record.etag, '"dataset-v7"')
            self.assertEqual(record.last_modified, "Wed, 02 Sep 2026 10:00:00 GMT")
            self.assertEqual(record.sha256, sha256_bytes(_PAYLOAD))
            self.assertEqual(record.size_bytes, len(_PAYLOAD))
            self.assertIn("page=2", record.source_uri)
            self.assertIn("REDACTED", record.source_uri)
            self.assertIn("REDACTED", record.resolved_url or "")
            self.assertEqual(Path(record.path).read_bytes(), _PAYLOAD)

            manifest_path = (
                workspace / "runs" / "demo" / "http_raw" / result.run_id / "manifest.json"
            )
            payload = json.loads(manifest_path.read_text(encoding="utf-8"))
            artifact = payload["artifacts"][0]
            expected_keys = {
                "source_uri",
                "resolved_url",
                "status_code",
                "content_type",
                "etag",
                "last_modified",
                "retrieved_at",
                "size_bytes",
                "sha256",
            }
            self.assertTrue(expected_keys.issubset(artifact))
            self.assertEqual(artifact["status_code"], 200)
            self.assertEqual(artifact["sha256"], sha256_bytes(_PAYLOAD))

            serialized = manifest_path.read_text(encoding="utf-8")
            persisted = "\n".join(
                [
                    serialized,
                    record.source_uri,
                    record.resolved_url or "",
                    record.etag or "",
                    record.last_modified or "",
                ]
            )
            for secret in (
                "auth-secret",
                "cookie-secret",
                "query-token-secret",
                "param-api-secret",
                "header-api-secret",
                "response-cookie-secret",
                "response-token-secret",
            ):
                self.assertNotIn(secret, persisted)
            for forbidden_header in ("Authorization", "Cookie", "X-API-Key", "Set-Cookie"):
                self.assertNotIn(forbidden_header, serialized)


if __name__ == "__main__":
    unittest.main()
