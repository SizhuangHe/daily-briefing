"""Text cleaning and processing utilities."""

import re

from bs4 import BeautifulSoup


def clean_html(text: str) -> str:
    """Strip HTML tags and clean up whitespace from text."""
    if not text:
        return ""
    soup = BeautifulSoup(text, "html.parser")
    clean = soup.get_text(separator=" ")
    # Collapse multiple whitespace / newlines into single space
    clean = re.sub(r"\s+", " ", clean).strip()
    return clean
