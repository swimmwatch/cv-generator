import contextlib
import ipaddress
import secrets

import aiohttp
import pytest

from utils import net


@pytest.mark.parametrize(
    ("ip_str", "expected"),
    [
        # Public / globally routable examples
        ("1.1.1.1", True),
        ("8.8.8.8", True),
        ("9.9.9.9", True),
        ("185.199.108.153", True),  # github.io / GH pages anycast
        # Private RFC1918
        ("10.0.0.1", False),
        ("172.16.0.0", False),
        ("192.168.1.1", False),
        # Loopback
        ("127.0.0.1", False),
        # Link-local
        ("169.254.0.1", False),
        # Multicast (224.0.0.0/4)
        ("224.0.0.1", False),
        ("239.255.255.255", False),
        # Limited broadcast
        ("255.255.255.255", False),
        # Unspecified
        ("0.0.0.0", False),  # noqa: S104
        # Documentation (TEST-NETs)
        ("192.0.2.1", False),
        ("198.51.100.2", False),
        ("203.0.113.3", False),
        # Benchmarking (RFC 2544)
        ("198.18.0.0", False),
        ("198.19.255.255", False),
        # Future use / reserved (240.0.0.0/4 except 255.255.255.255)
        ("240.0.0.1", False),
        ("255.255.255.254", False),
        # Carrier Grade NAT (RFC 6598)
        ("100.64.0.1", False),
        ("100.127.255.254", False),
        # IETF Protocol Assignments (RFC 6890)
        ("192.0.0.1", False),
        # Deprecated 6to4 relay anycast
        ("192.88.99.1", False),
    ],
)
def test_is_public_ipv4(ip_str: str, expected: bool):
    ip = ipaddress.IPv4Address(ip_str)
    assert net.is_public_ipv4(ip) is expected


def test_random_public_ipv4_eventual_success(monkeypatch):
    """Ensure the generator keeps trying until a public IP is returned."""
    sequence = [
        "10.0.0.1",  # private
        "127.0.0.1",  # loopback
        "224.0.0.1",  # multicast
        "8.8.8.8",  # public -> should stop here
    ]
    ints = [int(ipaddress.IPv4Address(s)) for s in sequence]

    call_state = {"i": 0}

    def fake_randbits(bits: int) -> int:  # noqa: D401 - simple stub
        assert bits == 32
        val = ints[call_state["i"]]
        call_state["i"] += 1
        return val

    monkeypatch.setattr(secrets, "randbits", fake_randbits)

    result = net.random_public_ipv4()

    assert result == sequence[-1]
    assert call_state["i"] == len(sequence)
    assert ipaddress.IPv4Address(result).is_global is True


def test_random_public_ipv4_returns_public_for_many_iterations(monkeypatch):
    """Stress a longer chain of invalid draws to catch any logical leaks."""
    bad = [
        "0.0.0.0",  # noqa: S104
        "10.1.2.3",
        "192.168.0.42",
        "127.0.0.9",
        "224.1.1.1",
    ]
    good = "9.9.9.9"
    sequence = bad + [good]
    ints = [int(ipaddress.IPv4Address(s)) for s in sequence]

    idx = {"i": 0}

    def fake_randbits(bits: int) -> int:
        val = ints[idx["i"]]
        idx["i"] += 1
        return val

    monkeypatch.setattr(secrets, "randbits", fake_randbits)

    result = net.random_public_ipv4()

    assert result == good
    assert idx["i"] == len(sequence)
    assert ipaddress.IPv4Address(result).is_global


def test_random_public_ipv4_type_and_format():
    result = net.random_public_ipv4()
    parts = result.split(".")
    assert len(parts) == 4
    assert all(p.isdigit() and 0 <= int(p) <= 255 for p in parts)
    addr = ipaddress.IPv4Address(result)
    assert addr.is_global


def test_random_public_ipv4_invalid_max_attempts():
    with pytest.raises(ValueError, match="max_attempts must be > 0"):
        net.random_public_ipv4(0)
    with pytest.raises(ValueError, match="max_attempts must be > 0"):
        net.random_public_ipv4(-5)


def test_random_public_ipv4_exhaustion(monkeypatch):
    # Force only private IPs to be generated
    private_ip_int = int(ipaddress.IPv4Address("10.0.0.1"))

    def fake(bits: int) -> int:  # noqa: D401
        assert bits == 32
        return private_ip_int

    monkeypatch.setattr(secrets, "randbits", fake)

    with pytest.raises(net.RandomIPv4GenerationError):
        net.random_public_ipv4(max_attempts=5)


def test_random_public_ipv4_alias_backward_compat(monkeypatch):
    # Ensure alias still works and returns same type of value
    public_ip = "8.8.8.8"
    public_ip_int = int(ipaddress.IPv4Address(public_ip))
    calls = {"n": 0}

    def fake(bits: int) -> int:
        calls["n"] += 1
        return public_ip_int

    monkeypatch.setattr(secrets, "randbits", fake)
    assert net.random_public_ipv4_fallback() == public_ip
    assert calls["n"] == 1


class TestIsUrlReachable:
    @staticmethod
    def _make_fake_session(monkeypatch, status=None, error=None, captured=None):
        @contextlib.asynccontextmanager
        async def _fake_head(url, **kwargs):
            if error:
                raise error
            resp = aiohttp.ClientResponse.__new__(aiohttp.ClientResponse)
            resp.status = status
            yield resp

        class FakeSession:
            async def __aenter__(self):
                return self

            async def __aexit__(self, *args):
                pass

            def head(self, url, **kwargs):
                if captured is not None:
                    captured.update(kwargs)
                return _fake_head(url, **kwargs)

        monkeypatch.setattr(aiohttp, "ClientSession", FakeSession)

    async def test_returns_true_for_successful_response(self, monkeypatch):
        self._make_fake_session(monkeypatch, status=200)
        assert await net.is_url_reachable("https://example.com") is True

    async def test_returns_true_for_4xx_response(self, monkeypatch):
        self._make_fake_session(monkeypatch, status=404)
        assert await net.is_url_reachable("https://example.com") is True

    async def test_returns_false_for_5xx_response(self, monkeypatch):
        self._make_fake_session(monkeypatch, status=500)
        assert await net.is_url_reachable("https://example.com") is False

    async def test_returns_false_on_connection_error(self, monkeypatch):
        self._make_fake_session(monkeypatch, error=aiohttp.ClientError("fail"))
        assert await net.is_url_reachable("https://example.com") is False

    async def test_returns_false_on_timeout(self, monkeypatch):
        self._make_fake_session(monkeypatch, error=TimeoutError())
        assert await net.is_url_reachable("https://example.com") is False

    async def test_passes_custom_timeout(self, monkeypatch):
        captured: dict = {}
        self._make_fake_session(monkeypatch, status=200, captured=captured)
        await net.is_url_reachable("https://example.com", timeout=5)
        assert captured["timeout"].total == 5
