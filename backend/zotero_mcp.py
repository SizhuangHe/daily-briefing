#!/usr/bin/env python3
"""
Zotero MCP Server.

Exposes Zotero library operations as MCP tools for Claude Code.
Uses pyzotero for API access. Credentials via environment variables.
"""

import json
import logging
import os
import re
import sys
from datetime import datetime, timezone

from mcp.server.fastmcp import FastMCP
from pyzotero import zotero

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
    stream=sys.stderr,
)
logger = logging.getLogger(__name__)

ZOTERO_API_KEY = os.environ.get("ZOTERO_API_KEY", "")
ZOTERO_LIBRARY_ID = os.environ.get("ZOTERO_LIBRARY_ID", "")
ZOTERO_LIBRARY_TYPE = os.environ.get("ZOTERO_LIBRARY_TYPE", "user")

if not ZOTERO_API_KEY or not ZOTERO_LIBRARY_ID:
    logger.error("ZOTERO_API_KEY and ZOTERO_LIBRARY_ID must be set")
    sys.exit(1)

mcp = FastMCP("zotero")


def _get_zot() -> zotero.Zotero:
    """Create a Zotero API client."""
    return zotero.Zotero(ZOTERO_LIBRARY_ID, ZOTERO_LIBRARY_TYPE, ZOTERO_API_KEY)


def _summarize_item(item: dict) -> dict:
    """Extract key fields from a Zotero item for display."""
    data = item.get("data", {})
    creators = data.get("creators", [])
    author_names = []
    for c in creators:
        if c.get("name"):
            author_names.append(c["name"])
        elif c.get("lastName"):
            name = c.get("lastName", "")
            if c.get("firstName"):
                name = f"{c['firstName']} {name}"
            author_names.append(name)

    return {
        "key": data.get("key", ""),
        "title": data.get("title", ""),
        "authors": author_names,
        "year": data.get("date", "")[:4] if data.get("date") else "",
        "itemType": data.get("itemType", ""),
        "tags": [t.get("tag", "") for t in data.get("tags", [])],
        "abstractNote": data.get("abstractNote", "")[:300],
        "url": data.get("url", ""),
        "DOI": data.get("DOI", ""),
        "dateAdded": data.get("dateAdded", ""),
    }


@mcp.tool()
def add_paper_by_id(identifier: str) -> str:
    """Add a paper to Zotero by arXiv ID or DOI. Auto-fetches metadata.

    Args:
        identifier: An arXiv ID (e.g. "2301.07041") or DOI (e.g. "10.1234/example")
    """
    zot = _get_zot()

    # Detect identifier type
    identifier = identifier.strip()

    # Normalize arXiv ID: strip "arXiv:" prefix if present
    if identifier.lower().startswith("arxiv:"):
        identifier = identifier[6:]

    # Check if it's a DOI (contains slash and typically starts with 10.)
    is_doi = "/" in identifier and (identifier.startswith("10.") or identifier.lower().startswith("doi:"))
    if identifier.lower().startswith("doi:"):
        identifier = identifier[4:].strip()

    try:
        if is_doi:
            # Use Zotero's web translators via DOI
            # pyzotero doesn't have a direct DOI lookup, so we create manually
            # Try the Zotero content negotiation approach
            from urllib.request import Request, urlopen
            from urllib.error import URLError

            # Use DOI content negotiation to get metadata as CSL-JSON
            url = f"https://doi.org/{identifier}"
            req = Request(url, headers={"Accept": "application/vnd.citationstyles.csl+json"})
            try:
                with urlopen(req, timeout=15) as resp:
                    csl = json.loads(resp.read())
            except URLError as e:
                return json.dumps({"error": f"Failed to resolve DOI: {e}"})

            # Map CSL-JSON to Zotero item
            item_type = "journalArticle"
            if csl.get("type") in ("paper-conference", "proceedings-article"):
                item_type = "conferencePaper"

            template = zot.item_template(item_type)
            template["title"] = csl.get("title", identifier)
            template["DOI"] = identifier
            template["url"] = f"https://doi.org/{identifier}"
            template["abstractNote"] = csl.get("abstract", "")
            template["publicationTitle"] = csl.get("container-title", "")

            # Date
            date_parts = csl.get("issued", {}).get("date-parts", [[]])
            if date_parts and date_parts[0]:
                parts = date_parts[0]
                template["date"] = "-".join(str(p) for p in parts)

            # Authors
            creators = []
            for author in csl.get("author", []):
                creators.append({
                    "creatorType": "author",
                    "firstName": author.get("given", ""),
                    "lastName": author.get("family", ""),
                })
            if creators:
                template["creators"] = creators

            resp = zot.create_items([template])
            if resp.get("successful"):
                key = list(resp["successful"].values())[0]["key"]
                return json.dumps({
                    "status": "success",
                    "key": key,
                    "title": template["title"],
                    "method": "DOI",
                })
            else:
                return json.dumps({"error": "Failed to create item", "details": resp.get("failed", {})})

        else:
            # arXiv paper
            arxiv_id = identifier

            # Fetch metadata from arXiv API
            from urllib.request import urlopen
            from urllib.error import URLError
            import xml.etree.ElementTree as ET

            api_url = f"http://export.arxiv.org/api/query?id_list={arxiv_id}"
            try:
                with urlopen(api_url, timeout=15) as resp:
                    xml_data = resp.read()
            except URLError as e:
                return json.dumps({"error": f"Failed to fetch arXiv metadata: {e}"})

            root = ET.fromstring(xml_data)
            ns = {"atom": "http://www.w3.org/2005/Atom", "arxiv": "http://arxiv.org/schemas/atom"}

            entry = root.find("atom:entry", ns)
            if entry is None:
                return json.dumps({"error": f"No arXiv paper found for ID: {arxiv_id}"})

            title = entry.findtext("atom:title", "", ns).strip().replace("\n", " ")
            abstract = entry.findtext("atom:summary", "", ns).strip().replace("\n", " ")
            published = entry.findtext("atom:published", "", ns)[:10]  # YYYY-MM-DD

            authors = []
            for author_el in entry.findall("atom:author", ns):
                name = author_el.findtext("atom:name", "", ns)
                parts = name.rsplit(" ", 1)
                if len(parts) == 2:
                    authors.append({"creatorType": "author", "firstName": parts[0], "lastName": parts[1]})
                else:
                    authors.append({"creatorType": "author", "name": name})

            # Check for DOI in arXiv metadata
            doi_el = entry.find("arxiv:doi", ns)
            doi = doi_el.text if doi_el is not None else ""

            # Find primary category
            primary_cat = entry.find("arxiv:primary_category", ns)
            category = primary_cat.get("term", "") if primary_cat is not None else ""

            # Create as preprint
            template = zot.item_template("preprint")
            template["title"] = title
            template["abstractNote"] = abstract
            template["date"] = published
            template["url"] = f"https://arxiv.org/abs/{arxiv_id}"
            template["repository"] = "arXiv"
            template["archiveID"] = f"arXiv:{arxiv_id}"
            if doi:
                template["DOI"] = doi
            if authors:
                template["creators"] = authors

            resp = zot.create_items([template])
            if resp.get("successful"):
                key = list(resp["successful"].values())[0]["key"]
                return json.dumps({
                    "status": "success",
                    "key": key,
                    "title": title,
                    "arxiv_id": arxiv_id,
                    "category": category,
                    "method": "arXiv",
                })
            else:
                return json.dumps({"error": "Failed to create item", "details": resp.get("failed", {})})

    except Exception as e:
        return json.dumps({"error": str(e)})


@mcp.tool()
def search_papers(query: str, limit: int = 20) -> str:
    """Search papers in your Zotero library.

    Args:
        query: Search query string (matches title, authors, abstract, etc.)
        limit: Maximum number of results (default 20)
    """
    zot = _get_zot()
    try:
        items = zot.items(q=query, limit=limit, sort="date", direction="desc")
        results = [_summarize_item(item) for item in items if item.get("data", {}).get("itemType") != "attachment"]
        return json.dumps({"count": len(results), "results": results})
    except Exception as e:
        return json.dumps({"error": str(e)})


@mcp.tool()
def add_tags(item_key: str, tags: list[str]) -> str:
    """Add tags to an existing Zotero item. Preserves existing tags.

    Args:
        item_key: The Zotero item key (from search_papers or add_paper_by_id)
        tags: List of tag strings to add
    """
    zot = _get_zot()
    try:
        item = zot.item(item_key)
        data = item["data"]
        existing_tags = {t["tag"] for t in data.get("tags", [])}
        new_tags = [{"tag": t} for t in tags if t not in existing_tags]

        if not new_tags:
            return json.dumps({"status": "no_change", "message": "All tags already exist"})

        data["tags"] = data.get("tags", []) + new_tags
        zot.update_item(data)
        all_tags = [t["tag"] for t in data["tags"]]
        return json.dumps({"status": "success", "key": item_key, "tags": all_tags})
    except Exception as e:
        return json.dumps({"error": str(e)})


@mcp.tool()
def list_recent(limit: int = 10) -> str:
    """List recently added items in your Zotero library.

    Args:
        limit: Number of items to return (default 10, max 100)
    """
    zot = _get_zot()
    try:
        limit = min(limit, 100)
        items = zot.items(sort="dateAdded", direction="desc", limit=limit)
        results = [_summarize_item(item) for item in items if item.get("data", {}).get("itemType") != "attachment"]
        return json.dumps({"count": len(results), "items": results})
    except Exception as e:
        return json.dumps({"error": str(e)})


if __name__ == "__main__":
    mcp.run(transport="stdio")
