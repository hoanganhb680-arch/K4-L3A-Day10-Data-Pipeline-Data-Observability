from __future__ import annotations

from dataclasses import asdict, dataclass, fields
from datetime import date, datetime
from html import unescape
from pathlib import Path
import logging
import re

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from core.config import Settings
from core.utils import ensure_parent, normalize_whitespace, read_json, write_json


@dataclass(frozen=True)
class PaperRecord:
    paper_id: str
    title: str
    summary: str
    authors: list[str]
    categories: list[str]
    primary_category: str
    published: str
    updated: str
    abs_url: str
    pdf_url: str
    comment: str


def parse_crossref_payload(payload: dict) -> list[PaperRecord]:
    """Extract usable records without assuming optional Crossref fields exist."""
    message = payload.get("message", {}) if isinstance(payload, dict) else {}
    items = message.get("items", []) if isinstance(message, dict) else []
    records = []
    for item in items if isinstance(items, list) else []:
        if not isinstance(item, dict):
            continue
        paper_id = clean_text(item.get("DOI")).lower()
        titles = item.get("title", [])
        title = clean_text(titles[0] if isinstance(titles, list) and titles else titles)
        if not paper_id or not title:
            continue
        authors = []
        for author in as_list(item.get("author")):
            if isinstance(author, dict):
                name = clean_text(f"{clean_text(author.get('given'))} {clean_text(author.get('family'))}")
                authors.append(name or clean_text(author.get("name")))
        categories = [clean_text(value) for value in as_list(item.get("subject"))]
        categories = [value for value in categories if value]
        published = next((value for key in ("published", "published-online", "published-print", "issued", "created")
                          if (value := _crossref_date(item.get(key)))), "")
        updated = next((value for key in ("indexed", "deposited", "created")
                        if (value := _crossref_date(item.get(key)))), published)
        pdf_url = next((clean_text(link.get("URL")) for link in as_list(item.get("link"))
                        if isinstance(link, dict) and link.get("content-type") == "application/pdf"), "")
        records.append(PaperRecord(
            paper_id=paper_id, title=title, summary=clean_text(item.get("abstract")),
            authors=[name for name in authors if name], categories=categories,
            primary_category=categories[0] if categories else "", published=published,
            updated=updated, abs_url=clean_text(item.get("URL")) or f"https://doi.org/{paper_id}",
            pdf_url=pdf_url, comment=clean_text(item.get("type")),
        ))
    return records


def clean_text(value) -> str:
    """Remove JATS/HTML markup, decode entities, and collapse whitespace."""
    if not isinstance(value, str):
        return ""
    return normalize_whitespace(unescape(re.sub(r"<[^>]*>", " ", value)))


def as_list(value) -> list:
    return value if isinstance(value, list) else [value] if value is not None else []


def _crossref_date(value) -> str:
    if not isinstance(value, dict):
        return ""
    try:
        parts = value.get("date-parts", [[]])[0]
        if parts:
            return date(int(parts[0]), int(parts[1]) if len(parts) > 1 else 1,
                        int(parts[2]) if len(parts) > 2 else 1).isoformat()
        return datetime.fromisoformat(value.get("date-time", "").replace("Z", "+00:00")).date().isoformat()
    except (TypeError, ValueError, IndexError, AttributeError):
        return ""


def fetch_source_records(settings: Settings) -> list[PaperRecord]:
    """Prefer the local snapshot; refresh with bounded retries and safe fallback."""
    snapshot = settings.paths.raw_api_response
    if snapshot.exists() and not settings.refresh_source:
        records = parse_crossref_payload(read_json(snapshot))
    else:
        retry = Retry(total=3, backoff_factor=1, status_forcelist=[429, 500, 502, 503, 504],
                      allowed_methods=["GET"], respect_retry_after_header=True)
        try:
            with requests.Session() as session:
                session.mount("https://", HTTPAdapter(max_retries=retry))
                response = session.get(
                    "https://api.crossref.org/works",
                    params={"query": settings.source_query, "filter": settings.source_filter,
                            "rows": settings.max_results}, timeout=(10, 45),
                    headers={"User-Agent": "Day10DataObservabilityLab/0.1"},
                )
                response.raise_for_status()
                records = parse_crossref_payload(response.json())
                if not records:
                    raise ValueError("Crossref returned no usable records.")
                # Preserve the successful response bytes, not a reserialized payload.
                ensure_parent(snapshot)
                temporary = snapshot.with_suffix(".json.tmp")
                temporary.write_bytes(response.content)
                temporary.replace(snapshot)
        except (requests.RequestException, ValueError):
            if not snapshot.exists():
                raise RuntimeError("Crossref fetch failed and no local snapshot is available.") from None
            logging.getLogger(__name__).warning("Crossref refresh failed; using the unchanged local snapshot.")
            records = parse_crossref_payload(read_json(snapshot))
    if not records:
        raise ValueError("The source snapshot contains no usable papers.")
    write_json(settings.paths.raw_records_json, [asdict(record) for record in records])
    return records


def load_raw_records(path: Path) -> list[PaperRecord]:
    """Load trusted parsed records, tolerating absent optional fields."""
    payload = read_json(path)
    if not isinstance(payload, list):
        raise ValueError("Raw records must be a JSON list.")
    records = []
    for item in payload:
        if not isinstance(item, dict):
            continue
        values = {field.name: item.get(field.name, [] if field.name in {"authors", "categories"} else "")
                  for field in fields(PaperRecord)}
        if clean_text(values["paper_id"]) and clean_text(values["title"]):
            records.append(PaperRecord(**values))
    return records
