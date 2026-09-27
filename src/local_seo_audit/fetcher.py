"""A small, polite httpx wrapper used for every request the tool makes."""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from importlib.metadata import PackageNotFoundError, version

import httpx

try:
    _VERSION = version("local-seo-audit")
except PackageNotFoundError:  # pragma: no cover - only hit when not installed
    _VERSION = "0.2.0"

#: Sent on every request so site owners can see who is auditing them and why.
USER_AGENT = f"local-seo-audit/{_VERSION} (+https://github.com/Ricky1800/local-seo-audit)"

#: Generous but bounded: local-business sites are often on slow shared hosting.
DEFAULT_TIMEOUT = httpx.Timeout(10.0, connect=5.0)

#: Keep redirect chains from looping forever on a misconfigured server.
MAX_REDIRECTS = 8


@dataclass(frozen=True, slots=True)
class FetchResult:
    """The outcome of fetching a single URL."""

    request_url: str
    final_url: str
    status_code: int
    headers: httpx.Headers
    text: str
    elapsed_ms: float
    redirected: bool
    history_urls: list[str] = field(default_factory=list)
    error: str | None = None

    @property
    def ok(self) -> bool:
        """Whether the request completed and returned a non-error status."""
        return self.error is None and 200 <= self.status_code < 400

    @property
    def byte_size(self) -> int:
        """Size of the response body in bytes (UTF-8 encoded)."""
        return len(self.text.encode("utf-8"))


def new_client(timeout: httpx.Timeout = DEFAULT_TIMEOUT) -> httpx.Client:
    """Build the shared httpx client used for a whole audit run."""
    return httpx.Client(
        headers={
            "User-Agent": USER_AGENT,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
        },
        timeout=timeout,
        follow_redirects=True,
        max_redirects=MAX_REDIRECTS,
    )


def fetch(client: httpx.Client, url: str, *, follow_redirects: bool = True) -> FetchResult:
    """GET ``url`` with ``client``, never raising: network errors become a result."""
    start = time.perf_counter()
    try:
        response = client.get(url, follow_redirects=follow_redirects)
    except httpx.HTTPError as exc:
        elapsed_ms = (time.perf_counter() - start) * 1000
        return FetchResult(
            request_url=url,
            final_url=url,
            status_code=0,
            headers=httpx.Headers(),
            text="",
            elapsed_ms=elapsed_ms,
            redirected=False,
            history_urls=[],
            error=f"{type(exc).__name__}: {exc}",
        )
    elapsed_ms = (time.perf_counter() - start) * 1000
    return FetchResult(
        request_url=url,
        final_url=str(response.url),
        status_code=response.status_code,
        headers=response.headers,
        text=response.text,
        elapsed_ms=elapsed_ms,
        redirected=bool(response.history),
        history_urls=[str(r.url) for r in response.history],
    )
