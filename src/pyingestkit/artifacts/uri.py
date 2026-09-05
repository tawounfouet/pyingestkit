from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import quote, unquote, urlsplit
from urllib.request import url2pathname

_URI_SCHEME = re.compile(r"^[A-Za-z][A-Za-z0-9+.-]*$")


@dataclass(frozen=True, slots=True)
class ArtifactURI:
    """Credential-free canonical locator for a persisted artifact object.

    ``source_uri`` answers where bytes came from. ``ArtifactURI`` answers where
    PyIngestKit persisted those bytes. Query strings, fragments and user-info are
    rejected so credentials cannot accidentally become durable artifact identity.
    """

    value: str

    def __post_init__(self) -> None:
        parsed = urlsplit(self.value)
        if not parsed.scheme or not _URI_SCHEME.fullmatch(parsed.scheme):
            raise ValueError(f"Artifact URI requires a valid scheme: {self.value!r}")
        if parsed.username is not None or parsed.password is not None:
            raise ValueError("Artifact URI must not contain embedded credentials")
        if parsed.query or parsed.fragment:
            raise ValueError("Artifact URI must not contain query strings or fragments")
        if parsed.scheme == "file" and parsed.netloc not in ("", "localhost"):
            raise ValueError("file artifact URIs must be local")
        if parsed.scheme == "s3":
            if not parsed.netloc:
                raise ValueError("s3 artifact URI requires a bucket")
            if not parsed.path.lstrip("/"):
                raise ValueError("s3 artifact URI requires an object key")

    @classmethod
    def from_path(cls, path: str | Path) -> ArtifactURI:
        return cls(Path(path).expanduser().absolute().as_uri())

    @classmethod
    def s3(cls, bucket: str, key: str) -> ArtifactURI:
        normalized_bucket = bucket.strip()
        normalized_key = key.lstrip("/")
        if not normalized_bucket or any(char.isspace() for char in normalized_bucket):
            raise ValueError("S3 bucket must not be empty or contain whitespace")
        if any(char in normalized_bucket for char in ("/", "@", ":")):
            raise ValueError("S3 bucket contains unsafe URI characters")
        if not normalized_key:
            raise ValueError("S3 object key must not be empty")
        encoded_key = quote(normalized_key, safe="/-._~")
        return cls(f"s3://{normalized_bucket}/{encoded_key}")

    @property
    def scheme(self) -> str:
        return urlsplit(self.value).scheme.lower()

    @property
    def bucket(self) -> str | None:
        parsed = urlsplit(self.value)
        return parsed.netloc if parsed.scheme.lower() == "s3" else None

    @property
    def key(self) -> str | None:
        parsed = urlsplit(self.value)
        if parsed.scheme.lower() != "s3":
            return None
        return unquote(parsed.path.lstrip("/"))

    @property
    def name(self) -> str:
        parsed = urlsplit(self.value)
        path = unquote(parsed.path)
        return path.rstrip("/").rsplit("/", 1)[-1]

    @property
    def is_local(self) -> bool:
        return self.scheme == "file"

    def as_path(self) -> Path:
        parsed = urlsplit(self.value)
        if parsed.scheme.lower() != "file":
            raise ValueError(f"Artifact URI is not local: {self.value}")
        return Path(url2pathname(unquote(parsed.path)))

    def __str__(self) -> str:
        return self.value
