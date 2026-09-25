from __future__ import annotations

import dataclasses
import json
import logging
import re
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

import requests

from core.config import Settings

logger = logging.getLogger(__name__)


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


def parse_date(date_parts: list) -> str:
    """Helper to parse Crossref date-parts into ISO format string."""
    try:
        parts = date_parts[0]
        year = int(parts[0])
        month = int(parts[1]) if len(parts) > 1 else 1
        day = int(parts[2]) if len(parts) > 2 else 1
        return datetime(year, month, day).isoformat()
    except (IndexError, TypeError, ValueError):
        return ""


def clean_html_tags(text: str) -> str:
    """Remove HTML/XML tags from text."""
    if not text:
        return ""
    text = re.sub(r'<[^>]+>', '', text)
    return text.strip()


def parse_crossref_payload(payload: dict) -> list[PaperRecord]:
    """parse Crossref payload thanh list PaperRecord."""
    records = []
    items = payload.get("message", {}).get("items", [])
    
    for item in items:
        # DOI
        paper_id = item.get("DOI", "")
        if not paper_id:
            continue
            
        # Title
        title_list = item.get("title", [])
        title = title_list[0] if title_list else ""
        
        # Summary/Abstract
        abstract = item.get("abstract", "")
        summary = clean_html_tags(abstract)
        
        if not title or not summary:
            continue
            
        # Authors
        authors = []
        for author in item.get("author", []):
            given = author.get("given", "")
            family = author.get("family", "")
            if given and family:
                authors.append(f"{given} {family}")
            elif family:
                authors.append(family)
                
        # Categories
        categories = item.get("subject", [])
        primary_category = categories[0] if categories else "unknown"
        
        # Published date
        published = ""
        if "published" in item and "date-parts" in item["published"]:
            published = parse_date(item["published"]["date-parts"])
        elif "published-online" in item and "date-parts" in item["published-online"]:
             published = parse_date(item["published-online"]["date-parts"])
        elif "published-print" in item and "date-parts" in item["published-print"]:
             published = parse_date(item["published-print"]["date-parts"])
        elif "created" in item and "date-time" in item["created"]:
            published = item["created"]["date-time"]
            
        if not published:
            published = datetime.now().isoformat()
            
        # Updated date
        updated = ""
        if "created" in item and "date-time" in item["created"]:
            updated = item["created"]["date-time"]
        else:
            updated = published
            
        # URLs
        abs_url = item.get("URL", "")
        pdf_url = ""
        if "link" in item:
            for link in item["link"]:
                if link.get("content-type") == "application/pdf":
                    pdf_url = link.get("URL", "")
                    break
                    
        records.append(PaperRecord(
            paper_id=paper_id,
            title=title,
            summary=summary,
            authors=authors,
            categories=categories,
            primary_category=primary_category,
            published=published,
            updated=updated,
            abs_url=abs_url,
            pdf_url=pdf_url,
            comment=""
        ))
        
    return records


def fetch_source_records(settings: Settings) -> list[PaperRecord]:
    """goi source API, luu raw response, parse thanh records."""
    payload = None
    
    # Check if we should use the local snapshot or fetch from API
    if not settings.refresh_source and settings.paths.raw_api_response.exists():
        logger.info(f"Using local snapshot from {settings.paths.raw_api_response}")
        with open(settings.paths.raw_api_response, "r", encoding="utf-8") as f:
            payload = json.load(f)
    else:
        logger.info(f"Fetching from {settings.source_api}...")
        url = "https://api.crossref.org/works"
        params = {
            "query": settings.source_query,
            "filter": settings.source_filter,
            "rows": settings.max_results,
            "select": "DOI,title,abstract,author,subject,published,published-online,published-print,created,URL,link"
        }
        
        try:
            response = requests.get(url, params=params, timeout=15)
            if response.status_code == 429:
                logger.warning("429 Too Many Requests from Crossref. Falling back to local snapshot if available.")
                if settings.paths.raw_api_response.exists():
                    with open(settings.paths.raw_api_response, "r", encoding="utf-8") as f:
                        payload = json.load(f)
                else:
                    response.raise_for_status()
            else:
                response.raise_for_status()
                payload = response.json()
                
                # Save raw response
                settings.paths.raw_api_response.parent.mkdir(parents=True, exist_ok=True)
                with open(settings.paths.raw_api_response, "w", encoding="utf-8") as f:
                    json.dump(payload, f, indent=2, ensure_ascii=False)
                    
        except Exception as e:
            logger.error(f"Error fetching from Crossref API: {e}")
            logger.info("Falling back to local snapshot...")
            if settings.paths.raw_api_response.exists():
                with open(settings.paths.raw_api_response, "r", encoding="utf-8") as f:
                    payload = json.load(f)
            else:
                raise
                
    if payload is None:
        raise ValueError("Could not fetch data or load from snapshot.")
        
    records = parse_crossref_payload(payload)
    
    # Save raw records
    settings.paths.raw_records_json.parent.mkdir(parents=True, exist_ok=True)
    with open(settings.paths.raw_records_json, "w", encoding="utf-8") as f:
        records_dicts = [dataclasses.asdict(r) for r in records]
        json.dump(records_dicts, f, indent=2, ensure_ascii=False)
        
    return records


def load_raw_records(path: Path) -> list[PaperRecord]:
    """doc JSON snapshot va map thanh `PaperRecord`."""
    if not path.exists():
        raise FileNotFoundError(f"Raw records file not found at {path}")
        
    with open(path, "r", encoding="utf-8") as f:
        records_dicts = json.load(f)
        
    return [PaperRecord(**d) for d in records_dicts]
