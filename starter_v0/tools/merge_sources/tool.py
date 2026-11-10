from __future__ import annotations

import re
from collections import deque
from typing import Any
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from tools._shared import domain, err


DEDUPE_MODES = {"auto", "url", "title"}
TRACKING_QUERY_KEYS = {"fbclid", "gclid", "mc_cid", "mc_eid"}


def _normalize_url(value: Any) -> str:
    if not isinstance(value, str) or not value.strip():
        return ""

    try:
        parsed = urlsplit(value.strip())
        scheme = parsed.scheme.lower()
        hostname = (parsed.hostname or "").lower()
        if scheme not in {"http", "https"} or not hostname:
            return ""

        if hostname.startswith("www."):
            hostname = hostname[4:]

        port = parsed.port
        default_port = (scheme == "http" and port == 80) or (scheme == "https" and port == 443)
        netloc = hostname if port is None or default_port else f"{hostname}:{port}"

        path = parsed.path.rstrip("/")
        query_items = [
            (key, query_value)
            for key, query_value in parse_qsl(parsed.query, keep_blank_values=True)
            if not key.lower().startswith("utm_") and key.lower() not in TRACKING_QUERY_KEYS
        ]
        query_items.sort(key=lambda pair: (pair[0].lower(), pair[1]))
        return urlunsplit((scheme, netloc, path, urlencode(query_items, doseq=True), ""))
    except (TypeError, ValueError):
        return ""


def _normalize_title(value: Any) -> str:
    if not isinstance(value, str):
        return ""
    normalized = " ".join(value.split()).casefold()
    return re.sub(r"[\s.!?:;,\-]+$", "", normalized)


def _dedupe_key(item: dict[str, Any], mode: str) -> str:
    normalized_url = _normalize_url(item.get("url"))
    normalized_title = _normalize_title(item.get("title"))

    if mode == "url":
        return f"url:{normalized_url}" if normalized_url else ""
    if mode == "title":
        return f"title:{normalized_title}" if normalized_title else ""
    if normalized_url:
        return f"url:{normalized_url}"
    return f"title:{normalized_title}" if normalized_title else ""


def _has_value(value: Any) -> bool:
    return value is not None and value != "" and value != [] and value != {}


def _item_richness(item: dict[str, Any]) -> tuple[int, int, int]:
    populated_fields = sum(1 for value in item.values() if _has_value(value))
    summary_length = len(item.get("summary") or "") if isinstance(item.get("summary"), str) else 0
    title_length = len(item.get("title") or "") if isinstance(item.get("title"), str) else 0
    return populated_fields, summary_length, title_length


def _merge_duplicate(first: dict[str, Any], second: dict[str, Any]) -> dict[str, Any]:
    if _item_richness(second) > _item_richness(first):
        richer, other = second, first
    else:
        richer, other = first, second

    merged = dict(richer)
    for key, value in other.items():
        if not _has_value(merged.get(key)) and _has_value(value):
            merged[key] = value
    return merged


def _source_key(item: dict[str, Any]) -> str:
    source = item.get("source")
    if isinstance(source, str) and source.strip():
        return source.strip().casefold()
    url = item.get("url")
    inferred = domain(url) if isinstance(url, str) else ""
    return inferred.casefold() or "unknown"


def _round_robin_sources(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    groups: dict[str, deque[dict[str, Any]]] = {}
    for item in items:
        groups.setdefault(_source_key(item), deque()).append(item)

    diversified: list[dict[str, Any]] = []
    while groups:
        exhausted: list[str] = []
        for source, source_items in groups.items():
            diversified.append(source_items.popleft())
            if not source_items:
                exhausted.append(source)
        for source in exhausted:
            groups.pop(source)
    return diversified


def merge_sources(
    items: list[dict[str, Any]] | None = None,
    dedupe_by: str = "auto",
    max_items: int = 10,
    prefer_source_diversity: bool = True,
) -> dict[str, Any]:
    """Normalize, deduplicate, and optionally diversify existing research items."""
    try:
        if items is None:
            items = []
        if not isinstance(items, list):
            raise TypeError("items must be a list of objects")
        if not isinstance(dedupe_by, str) or dedupe_by not in DEDUPE_MODES:
            raise ValueError("dedupe_by must be one of: auto, url, title")
        if isinstance(max_items, bool) or not isinstance(max_items, int):
            raise TypeError("max_items must be an integer")
        if not 1 <= max_items <= 50:
            raise ValueError("max_items must be between 1 and 50")
        if not isinstance(prefer_source_diversity, bool):
            raise TypeError("prefer_source_diversity must be a boolean")

        unique_by_key: dict[str, dict[str, Any]] = {}
        key_order: list[str] = []
        invalid_items_skipped = 0
        duplicates_removed = 0

        for raw_item in items:
            if not isinstance(raw_item, dict):
                invalid_items_skipped += 1
                continue

            item = dict(raw_item)
            normalized_url = _normalize_url(item.get("url"))
            if normalized_url:
                item["url"] = normalized_url

            key = _dedupe_key(item, dedupe_by)
            if not key:
                invalid_items_skipped += 1
                continue

            if key in unique_by_key:
                unique_by_key[key] = _merge_duplicate(unique_by_key[key], item)
                duplicates_removed += 1
            else:
                unique_by_key[key] = item
                key_order.append(key)

        merged_items = [unique_by_key[key] for key in key_order]
        ordered_items = _round_robin_sources(merged_items) if prefer_source_diversity else merged_items
        returned_items = ordered_items[:max_items]
        source_count = len({_source_key(item) for item in returned_items})

        return {
            "tool": "merge_sources",
            "dedupe_by": dedupe_by,
            "original_count": len(items),
            "returned_count": len(returned_items),
            "duplicates_removed": duplicates_removed,
            "invalid_items_skipped": invalid_items_skipped,
            "source_count": source_count,
            "items": returned_items,
        }
    except Exception as exc:
        return err("merge_sources", exc)
