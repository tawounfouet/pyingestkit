"""Unit tests for Anti-SSRF validation, IP boundaries, and DNS resolution security."""

from __future__ import annotations

import pytest

from pyingestkit.adapters.http._ssrf import (
    AntiSsrfValidator,
    SsrfSecurityError,
)
from pyingestkit.adapters.http.source import HttpAccessPolicy, HttpSourceConnector
from pyingestkit.adapters.http.transport import HttpResponseV2
from pyingestkit.domain.acquisition import AcquisitionRequest, AcquisitionStatus
from pyingestkit.domain.runtime import CorrelationContext
from pyingestkit.domain.shared import IngestionRunId
from pyingestkit.domain.sources import Source


class _StaticClient:
    def __init__(self, response: HttpResponseV2) -> None:
        self.response = response
        self.calls: list[str] = []

    def send(self, request):
        self.calls.append(request.url)
        return self.response


def _request(url: str = "https://safe.example.test/data.json") -> AcquisitionRequest:
    run_id = IngestionRunId.new()
    return AcquisitionRequest(
        source=Source.http(url=url),
        ingestion_run_id=run_id,
        correlation=CorrelationContext(ingestion_run_id=str(run_id)),
    )


def test_ssrf_blocks_loopback_ipv4_and_ipv6() -> None:
    validator = AntiSsrfValidator()
    with pytest.raises(SsrfSecurityError, match="loopback_address"):
        validator.validate_ip("127.0.0.1")
    with pytest.raises(SsrfSecurityError, match="loopback_address"):
        validator.validate_ip("127.255.255.254")
    with pytest.raises(SsrfSecurityError, match="loopback_address"):
        validator.validate_ip("::1")
    with pytest.raises(SsrfSecurityError, match="loopback_address"):
        validator.validate_ip("::ffff:127.0.0.1")


def test_ssrf_blocks_cloud_metadata_and_link_local() -> None:
    validator = AntiSsrfValidator()
    # AWS / GCP metadata
    with pytest.raises(SsrfSecurityError, match="link_local_or_cloud_metadata"):
        validator.validate_ip("169.254.169.254")
    with pytest.raises(SsrfSecurityError, match="link_local_or_cloud_metadata"):
        validator.validate_ip("169.254.1.1")
    with pytest.raises(SsrfSecurityError, match="link_local_or_cloud_metadata"):
        validator.validate_ip("fe80::1")
    with pytest.raises(SsrfSecurityError, match="link_local_or_cloud_metadata"):
        validator.validate_ip("::ffff:169.254.169.254")


def test_ssrf_blocks_private_rfc1918_by_default() -> None:
    validator = AntiSsrfValidator()
    # 10.0.0.0/8
    with pytest.raises(SsrfSecurityError, match="private_rfc1918_network"):
        validator.validate_ip("10.0.0.1")
    # 172.16.0.0/12
    with pytest.raises(SsrfSecurityError, match="private_rfc1918_network"):
        validator.validate_ip("172.16.0.5")
    with pytest.raises(SsrfSecurityError, match="private_rfc1918_network"):
        validator.validate_ip("172.31.255.254")
    # 192.168.0.0/16
    with pytest.raises(SsrfSecurityError, match="private_rfc1918_network"):
        validator.validate_ip("192.168.1.1")
    # IPv6 ULA (Unique Local Address)
    with pytest.raises(SsrfSecurityError, match="private_rfc1918_network"):
        validator.validate_ip("fc00::1")


def test_ssrf_blocks_multicast_broadcast_and_special() -> None:
    validator = AntiSsrfValidator()
    with pytest.raises(SsrfSecurityError, match="multicast_or_broadcast"):
        validator.validate_ip("224.0.0.1")
    with pytest.raises(SsrfSecurityError, match="multicast_or_broadcast"):
        validator.validate_ip("255.255.255.255")
    with pytest.raises(SsrfSecurityError, match="reserved_special_network"):
        validator.validate_ip("0.0.0.0")
    with pytest.raises(SsrfSecurityError, match="reserved_special_network"):
        validator.validate_ip("100.64.0.1")  # Carrier-grade NAT


def test_ssrf_allows_public_ip_addresses() -> None:
    validator = AntiSsrfValidator()
    assert str(validator.validate_ip("8.8.8.8")) == "8.8.8.8"
    assert str(validator.validate_ip("1.1.1.1")) == "1.1.1.1"
    assert str(validator.validate_ip("93.184.216.34")) == "93.184.216.34"
    assert str(validator.validate_ip("2606:4700:4700::1111")) == "2606:4700:4700::1111"


def test_ssrf_allow_private_networks_exemption() -> None:
    validator = AntiSsrfValidator(allow_private_networks=True)
    # RFC 1918 is now permitted
    assert str(validator.validate_ip("10.0.0.1")) == "10.0.0.1"
    assert str(validator.validate_ip("192.168.1.100")) == "192.168.1.100"

    # BUT loopback and cloud metadata remain strictly BLOCKED
    with pytest.raises(SsrfSecurityError, match="loopback_address"):
        validator.validate_ip("127.0.0.1")
    with pytest.raises(SsrfSecurityError, match="link_local_or_cloud_metadata"):
        validator.validate_ip("169.254.169.254")


def test_ssrf_allowed_ip_ranges_specific_cidr() -> None:
    validator = AntiSsrfValidator(allowed_ip_ranges=("10.50.0.0/16",))
    # 10.50.x.x is allowed via explicit CIDR
    assert str(validator.validate_ip("10.50.1.2")) == "10.50.1.2"
    # Other 10.x.x.x remain blocked
    with pytest.raises(SsrfSecurityError, match="private_rfc1918_network"):
        validator.validate_ip("10.60.1.2")


def test_ssrf_dns_resolver_integration_and_poisoning_rejection() -> None:
    # Resolver returns one public IP and one malicious internal IP (e.g. DNS rebinding/poisoning)
    def poisoned_resolver(host: str, port: int) -> tuple[str, ...]:
        return ("93.184.216.34", "169.254.169.254")

    validator = AntiSsrfValidator(dns_resolver=poisoned_resolver)
    with pytest.raises(SsrfSecurityError, match="link_local_or_cloud_metadata"):
        validator.resolve_and_validate("poisoned.example.com", 443)


def test_ssrf_connector_blocks_request_to_private_ip() -> None:
    policy = HttpAccessPolicy(
        allowed_hosts=("intranet.corp",),
        allow_private_networks=False,
    )
    # Mock resolver returning RFC 1918 address
    validator = AntiSsrfValidator(
        allow_private_networks=False,
        dns_resolver=lambda host, port: ("10.0.0.15",),
    )
    client = _StaticClient(HttpResponseV2(200, "https://intranet.corp/data", (), b"secret"))
    connector = HttpSourceConnector(
        policy=policy,
        client=client,
        validator=validator,
    )
    result = connector.acquire(_request("https://intranet.corp/data"))

    assert result.status is AcquisitionStatus.FAILED
    assert result.failure is not None
    assert result.failure.error_code == "acquisition.http.ssrf_blocked"
    assert len(client.calls) == 0  # Socket was NEVER contacted


def test_ssrf_connector_blocks_redirect_to_cloud_metadata() -> None:
    policy = HttpAccessPolicy(
        allowed_hosts=("api.example.test", "metadata.example.test"),
    )
    # Redirect response targeting metadata host
    client = _StaticClient(
        HttpResponseV2(
            302,
            "https://api.example.test/fetch",
            (("Location", "https://metadata.example.test/latest/meta-data"),),
            b"",
        )
    )

    def dns_resolver(host: str, port: int) -> tuple[str, ...]:
        if host == "metadata.example.test":
            return ("169.254.169.254",)
        return ("93.184.216.34",)

    validator = AntiSsrfValidator(dns_resolver=dns_resolver)
    connector = HttpSourceConnector(
        policy=policy,
        client=client,
        validator=validator,
    )
    result = connector.acquire(_request("https://api.example.test/fetch"))

    assert result.status is AcquisitionStatus.FAILED
    assert result.failure is not None
    assert result.failure.error_code == "acquisition.http.redirect_forbidden"
