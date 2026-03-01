"""Canonical URL normalization for news deduplication."""

from urllib.parse import parse_qs, urlencode, urlparse, urlunparse


def normalize_url(url: str) -> str:
    """Normalize a URL by removing tracking parameters and fragments.

    Strips common tracking query params (utm_*, ref, fbclid, etc.),
    removes fragments, lowercases scheme and host, and removes trailing slashes.
    """
    parsed = urlparse(url)

    # Lowercase scheme and host
    scheme = parsed.scheme.lower()
    netloc = parsed.netloc.lower()

    # Remove trailing slash from path
    path = parsed.path.rstrip("/") or "/"

    # Remove tracking query parameters
    tracking_params = {
        "utm_source",
        "utm_medium",
        "utm_campaign",
        "utm_term",
        "utm_content",
        "ref",
        "fbclid",
        "gclid",
        "mc_cid",
        "mc_eid",
    }
    params = parse_qs(parsed.query, keep_blank_values=True)
    filtered_params = {
        k: v for k, v in params.items() if k.lower() not in tracking_params
    }
    query = urlencode(filtered_params, doseq=True)

    # Remove fragment
    return urlunparse((scheme, netloc, path, parsed.params, query, ""))
