from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
import json
from pathlib import Path
import re
import time

import requests

from core.config import Settings
from core.utils import ensure_parent, normalize_whitespace

SOURCE_ENDPOINT = "https://api.crossref.org/works"


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
    """Parse a Crossref API response payload into normalized PaperRecords.

    Only records with a DOI, a title, and a non-empty abstract are kept. JATS/HTML
    markup is removed from abstracts so downstream cleaning starts from plain text.
    """
    items = (payload.get("message") or {}).get("items") or []
    records: list[PaperRecord] = []

    for item in items:
        if not isinstance(item, dict):
            continue

        doi = normalize_whitespace(str(item.get("DOI") or "")).rstrip(".").strip()
        if not doi:
            continue

        title = _first_text(item.get("title"))
        summary = _strip_markup(_first_text(item.get("abstract")))
        title = normalize_whitespace(title)
        summary = normalize_whitespace(summary)
        if not title or not summary:
            continue

        authors = [
            normalize_whitespace(author.get("name") or _compose_author_name(author))
            for author in (item.get("author") or [])
            if isinstance(author, dict)
        ]
        authors = [author for author in authors if author]

        categories = [
            normalize_whitespace(str(subject))
            for subject in (item.get("subject") or [])
        ]
        categories = list(dict.fromkeys(category for category in categories if category))

        published = _parse_date_value(item.get("published") or {})
        updated = _parse_date_value(item.get("created") or item.get("deposited") or item.get("indexed") or {})
        if not published:
            continue

        url = normalize_whitespace(str(item.get("URL") or ""))
        abs_url = url or f"https://doi.org/{doi}"
        pdf_url = _find_pdf_link(item.get("link") or [])

        records.append(
            PaperRecord(
                paper_id=doi,
                title=title,
                summary=summary,
                authors=authors,
                categories=categories,
                primary_category=categories[0] if categories else "",
                published=published,
                updated=updated or published,
                abs_url=abs_url,
                pdf_url=pdf_url or url or abs_url,
                comment=f"Crossref record {doi}",
            )
        )

    return records


def fetch_source_records(settings: Settings) -> list[PaperRecord]:
    """Fetch Crossref records, preferring an existing local snapshot.

    The curated snapshot is treated as the source of truth once present so the
    lab stays deterministic. The live Crossref API is only used when no snapshot
    exists yet, and transient errors fall back to the snapshot as a safety net.
    """
    snapshot_path = settings.paths.raw_api_response
    if snapshot_path.exists():
        payload = json.loads(snapshot_path.read_text(encoding="utf-8"))
    else:
        payload = _fetch_api_payload(settings)
        if payload is None:
            raise RuntimeError("Crossref API unavailable and no local raw snapshot exists.")
        _write_payload(snapshot_path, payload)

    records = parse_crossref_payload(payload)
    deduped, seen = [], set()
    for record in records:
        key = record.paper_id.lower()
        if key in seen:
            continue
        seen.add(key)
        deduped.append(record)

    _write_payload(settings.paths.raw_records_json, [record.__dict__ for record in deduped])
    return deduped


def load_raw_records(path: Path) -> list[PaperRecord]:
    """Read a persisted list of record dictionaries from ``path``."""
    payload = json.loads(path.read_text(encoding="utf-8"))
    return [PaperRecord(**item) for item in payload]


def _fetch_api_payload(settings: Settings, max_retries: int = 3) -> dict | None:
    params = {
        "query": settings.source_query,
        "filter": settings.source_filter,
        "rows": settings.max_results,
        "select": "DOI,title,abstract,author,subject,published,created,deposited,indexed,URL,link",
    }
    for attempt in range(max_retries + 1):
        try:
            response = requests.get(SOURCE_ENDPOINT, params=params, timeout=20)
            if response.status_code in {429, 503}:
                _backoff(attempt)
                continue
            if response.status_code == 200:
                return response.json()
            if response.status_code >= 500:
                _backoff(attempt)
                continue
            break
        except requests.RequestException:
            _backoff(attempt)
    return None


def _backoff(attempt: int) -> None:
    time.sleep(min(2**attempt, 8))


def _write_payload(path: Path, payload) -> None:
    ensure_parent(path)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")


def _first_text(value) -> str:
    if isinstance(value, str):
        return value
    if isinstance(value, (list, tuple)) and value:
        return str(value[0] or "")
    return ""


def _strip_markup(text: str) -> str:
    text = re.sub(r"<[^>]+>", " ", text)
    return text.replace("&amp;", "&").replace("&lt;", "<").replace("&gt;", ">")


def _parse_date_value(value) -> str:
    if isinstance(value, dict):
        date_parts = value.get("date-parts") or []
        if date_parts and date_parts[0]:
            year, *rest = date_parts[0]
            month = rest[0] if rest else 1
            day = rest[1] if len(rest) > 1 else 1
            return date(int(year), int(month), int(day)).isoformat()
        raw = value.get("date-time") or ""
        return _iso_date(raw)
    if isinstance(value, str):
        return _iso_date(value)
    return ""


def _iso_date(value: str) -> str:
    value = normalize_whitespace(value)
    if not value:
        return ""
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00")).date().isoformat()
    except ValueError:
        match = re.search(r"\d{4}-\d{2}-\d{2}", value)
        return match.group(0) if match else ""


def _compose_author_name(author: dict) -> str:
    given = normalize_whitespace(str(author.get("given") or ""))
    family = normalize_whitespace(str(author.get("family") or ""))
    return f"{given} {family}".strip()


def _find_pdf_link(links: list) -> str:
    for link in links:
        if not isinstance(link, dict):
            continue
        if normalize_whitespace(str(link.get("content-type") or "")).lower() == "application/pdf":
            return normalize_whitespace(str(link.get("URL") or ""))
    return ""
