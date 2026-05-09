"""
Shared helpers for database / Redis URLs in Docker, Dokploy, and local dev.

Keeps ``development`` and ``production`` settings aligned without circular imports.
"""

import socket
from urllib.parse import urlparse, urlunparse


def resolved_tcp_host(hostname: str, *, fallback: str = "127.0.0.1") -> str:
    """
    Docker / Dokploy use service hostnames like ``db``. On a normal PC those names do not
    resolve unless Docker DNS is in play. Fall back to localhost so the same ``.env`` works
    when Postgres / Redis are published on the host loopback.
    """
    if not hostname:
        return fallback
    lowered = hostname.lower()
    if lowered in ("localhost", "127.0.0.1", "::1"):
        return hostname
    try:
        socket.gethostbyname(hostname)
    except OSError:
        return fallback
    return hostname


def redis_url_local_fallback(url: str, *, fallback_host: str = "127.0.0.1") -> str:
    """Same idea as ``resolved_tcp_host``, but for ``redis://`` URLs (including password in netloc)."""
    parsed = urlparse(url)
    if not parsed.hostname:
        return url
    try:
        socket.gethostbyname(parsed.hostname)
        return url
    except OSError:
        port = parsed.port or 6379
        netloc = parsed.netloc
        if "@" in netloc:
            userinfo, _, _hostport = netloc.rpartition("@")
            new_netloc = f"{userinfo}@{fallback_host}:{port}"
        else:
            new_netloc = f"{fallback_host}:{port}"
        return urlunparse((parsed.scheme, new_netloc, parsed.path, "", parsed.query, parsed.fragment))
