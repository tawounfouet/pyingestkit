"""Declarative acquisition-source values."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from urllib.parse import urlsplit

from pyingestkit.domain.resources import CredentialReference
from pyingestkit.domain.shared.validation import (
    require_non_blank,
    validate_credential_safe_locator,
    validate_metadata,
    validate_optional_text,
)


class SourceKind(StrEnum):
    """Portable source categories owned by PyIngestKit."""

    FILE = "file"
    HTTP = "http"
    OBJECT = "object"
    DATABASE = "database"
    CUSTOM = "custom"


@dataclass(frozen=True, slots=True)
class Source:
    """Side-effect-free declaration of acquisition origin and semantics."""

    kind: SourceKind
    locator: str | None = None
    connector_id: str | None = None
    credential: CredentialReference | None = None
    query: str | None = None
    options: tuple[tuple[str, str], ...] = ()
    metadata: tuple[tuple[str, str], ...] = ()

    def __post_init__(self) -> None:
        if not isinstance(self.kind, SourceKind):
            raise TypeError("Source kind must be a SourceKind.")
        validate_optional_text(self.locator, "Source locator")
        validate_optional_text(self.connector_id, "Source connector_id")
        validate_optional_text(self.query, "Source query")
        if self.credential is not None and not isinstance(
            self.credential,
            CredentialReference,
        ):
            raise TypeError("Source credential must be a CredentialReference.")
        validate_metadata(self.options, name="Source options")
        validate_metadata(self.metadata, name="Source metadata")
        self._validate_kind_contract()

    @classmethod
    def file(
        cls,
        *,
        path: str,
        metadata: tuple[tuple[str, str], ...] = (),
    ) -> Source:
        """Declare a local-file source without opening the path."""
        require_non_blank(path, "Source.file path")
        return cls(kind=SourceKind.FILE, locator=path, metadata=metadata)

    @classmethod
    def http(
        cls,
        *,
        url: str,
        credential: CredentialReference | None = None,
        options: tuple[tuple[str, str], ...] = (),
        metadata: tuple[tuple[str, str], ...] = (),
    ) -> Source:
        """Declare an HTTP(S) source without performing network I/O."""
        validate_credential_safe_locator(url, "Source.http url")
        parsed = urlsplit(url)
        if parsed.scheme not in {"http", "https"} or not parsed.netloc:
            raise ValueError("Source.http url must use http or https and include a host.")
        return cls(
            kind=SourceKind.HTTP,
            locator=url,
            credential=credential,
            options=options,
            metadata=metadata,
        )

    @classmethod
    def object(
        cls,
        *,
        uri: str,
        credential: CredentialReference | None = None,
        options: tuple[tuple[str, str], ...] = (),
        metadata: tuple[tuple[str, str], ...] = (),
    ) -> Source:
        """Declare an object-store source without constructing a provider client."""
        validate_credential_safe_locator(uri, "Source.object uri")
        parsed = urlsplit(uri)
        if not parsed.scheme:
            raise ValueError("Source.object uri must include a scheme.")
        if parsed.scheme in {"http", "https"}:
            raise ValueError("Use Source.http for HTTP(S) acquisition.")
        return cls(
            kind=SourceKind.OBJECT,
            locator=uri,
            credential=credential,
            options=options,
            metadata=metadata,
        )

    @classmethod
    def database(
        cls,
        *,
        connection: str,
        query: str,
        credential: CredentialReference | None = None,
        options: tuple[tuple[str, str], ...] = (),
        metadata: tuple[tuple[str, str], ...] = (),
    ) -> Source:
        """Declare database acquisition through a logical connection identifier."""
        require_non_blank(connection, "Source.database connection")
        require_non_blank(query, "Source.database query")
        if "://" in connection:
            raise ValueError(
                "Source.database connection must be a logical identifier, not a credential-bearing DSN."
            )
        return cls(
            kind=SourceKind.DATABASE,
            locator=connection,
            credential=credential,
            query=query,
            options=options,
            metadata=metadata,
        )

    @classmethod
    def custom(
        cls,
        *,
        connector_id: str,
        locator: str | None = None,
        credential: CredentialReference | None = None,
        options: tuple[tuple[str, str], ...] = (),
        metadata: tuple[tuple[str, str], ...] = (),
    ) -> Source:
        """Declare acquisition delegated to an explicitly selected connector."""
        require_non_blank(connector_id, "Source.custom connector_id")
        if locator is not None:
            validate_credential_safe_locator(locator, "Source.custom locator")
        return cls(
            kind=SourceKind.CUSTOM,
            locator=locator,
            connector_id=connector_id,
            credential=credential,
            options=options,
            metadata=metadata,
        )

    def fingerprint_payload(self) -> dict[str, object]:
        """Return dependency-neutral semantic material for definition hashing."""
        return {
            "kind": self.kind.value,
            "locator": self.locator,
            "connector_id": self.connector_id,
            "credential": (
                {
                    "credential_id": self.credential.credential_id,
                    "provider": self.credential.provider,
                }
                if self.credential is not None
                else None
            ),
            "query": self.query,
            "options": sorted(self.options),
            "metadata": sorted(self.metadata),
        }

    def _validate_kind_contract(self) -> None:
        if self.kind in {SourceKind.FILE, SourceKind.HTTP, SourceKind.OBJECT}:
            if self.locator is None:
                raise ValueError(f"{self.kind.value} Source requires locator.")
            if self.query is not None:
                raise ValueError(f"{self.kind.value} Source must not define query.")

        if self.kind is SourceKind.DATABASE:
            if self.locator is None or self.query is None:
                raise ValueError("database Source requires connection locator and query.")
            if "://" in self.locator:
                raise ValueError(
                    "database Source locator must be a logical connection identifier."
                )

        if self.kind is SourceKind.CUSTOM and self.connector_id is None:
            raise ValueError("custom Source requires connector_id.")

        if self.kind is not SourceKind.CUSTOM and self.connector_id is not None:
            raise ValueError("connector_id is reserved for custom Source declarations.")
