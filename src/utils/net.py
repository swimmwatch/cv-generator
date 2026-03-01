import ipaddress
import secrets

# Special-use IPv4 networks that should not be considered globally routable
_TEST_NETS = [
    ipaddress.IPv4Network("192.0.2.0/24"),  # TEST-NET-1
    ipaddress.IPv4Network("198.51.100.0/24"),  # TEST-NET-2
    ipaddress.IPv4Network("203.0.113.0/24"),  # TEST-NET-3
]
_BENCHMARK_NET = ipaddress.IPv4Network("198.18.0.0/15")  # RFC 2544 benchmarking
_RESERVED_FUTURE_NET = ipaddress.IPv4Network("240.0.0.0/4")  # Reserved / future use
_BROADCAST_ADDR = ipaddress.IPv4Address("255.255.255.255")
_CGNAT_NET = ipaddress.IPv4Network("100.64.0.0/10")  # Carrier Grade NAT space (RFC 6598)
_IETF_PROTOCOL_ASSIGN_NET = ipaddress.IPv4Network("192.0.0.0/24")  # IETF Protocol Assignments (RFC 6890)
_DEPRECATED_6TO4_RELAY_NET = ipaddress.IPv4Network("192.88.99.0/24")  # Deprecated 6to4 relay anycast


class RandomIPv4GenerationError(ValueError):
    """Raised when a public IPv4 address cannot be generated within max attempts."""


def is_public_ipv4(ip: ipaddress.IPv4Address) -> bool:
    """Return True if an IPv4 address is globally routable (public).

    Explicitly exclude private, loopback, link-local, multicast, unspecified,
    broadcast, documentation (TEST-NETs), benchmarking, CGNAT, protocol
    assignment, deprecated 6to4 relay, reserved future-use ranges, and any
    address flagged as reserved/site-local by the stdlib.
    """
    if ip.is_private:
        return False
    if ip.is_loopback:
        return False
    if ip.is_link_local:
        return False
    if ip.is_multicast:
        return False
    if ip.is_unspecified:
        return False
    if ip == _BROADCAST_ADDR:
        return False
    if ip in _BENCHMARK_NET:
        return False
    if ip in _RESERVED_FUTURE_NET:
        return False
    if ip in _CGNAT_NET:
        return False
    if ip in _IETF_PROTOCOL_ASSIGN_NET:
        return False
    if ip in _DEPRECATED_6TO4_RELAY_NET:
        return False
    # Reserved / site-local flags (site-local deprecated but kept for completeness)
    if getattr(ip, "is_reserved", False):
        return False
    if getattr(ip, "is_site_local", False):  # pragma: no cover (usually False in stdlib)
        return False
    for net in _TEST_NETS:
        if ip in net:
            return False
    return True


def random_public_ipv4(max_attempts: int = 1000) -> str:
    """Generate a random public (globally routable) IPv4 address.

    Parameters:
        max_attempts: Maximum number of attempts before giving up. Must be > 0.

    Returns:
        A string representation of a globally routable IPv4 address.

    Raises:
        ValueError: If max_attempts <= 0.
        RandomIPv4GenerationError: If a public IPv4 cannot be generated within max_attempts.
    """
    if max_attempts <= 0:
        raise ValueError("max_attempts must be > 0")

    for _ in range(max_attempts):
        ip = ipaddress.IPv4Address(secrets.randbits(32))
        if is_public_ipv4(ip):
            return str(ip)

    raise RandomIPv4GenerationError(f"Failed to generate public IPv4 address within {max_attempts} attempts")


# Backward compatibility alias (deprecated). Remove after dependent code migrates.
random_public_ipv4_fallback = random_public_ipv4  # type: ignore[assignment]
