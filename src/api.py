"""Helpers for the websites and APIs we load data from."""

import os
import time

import requests

from src import config

HEADERS = {"User-Agent": config.USER_AGENT}


def check(url):
    """Return "OK", "HTTP <code>" or "BLOCKED (<error>)" for one link."""
    try:
        response = requests.get(url, headers=HEADERS, timeout=20)
    except requests.RequestException as error:
        return f"BLOCKED ({type(error).__name__})"
    return "OK" if response.ok else f"HTTP {response.status_code}"


def get_json(url, params=None, tries=4, timeout=120):
    """Get a JSON reply. Return it as it came (bytes) and as Python data.

    Wait and try again if the website is slow, busy or answers with an error.
    """
    for attempt in range(1, tries + 1):
        try:
            response = requests.get(
                url, params=params, headers=HEADERS, timeout=timeout
            )
            response.raise_for_status()
            data = response.json()
            if isinstance(data, dict) and "error" in data:
                raise ValueError(f"{url} answered with an error: {data['error']}")
            return response.content, data
        except (requests.RequestException, ValueError):
            if attempt == tries:
                raise
            time.sleep(5 * attempt)


def dpwh_pages(page_size=config.DPWH_PAGE_SIZE):
    """Yield (page number, reply as it came, rows, total) for every page of the DPWH API.

    Stop with an error if a page is short or the total changes during the load,
    so bronze is never replaced with part of the data.
    """
    page, seen, expected_total = 1, 0, None
    while True:
        content, reply = get_json(config.DPWH_API, {"page": page, "limit": page_size})
        rows, paging = reply["data"]["data"], reply["data"]["pagination"]
        if int(paging["page"]) != page or int(paging["limit"]) != page_size:
            raise ValueError(f"Unexpected DPWH paging on page {page}: {paging}")
        total = int(paging["totalCount"])
        if expected_total is None:
            expected_total = total
        elif total != expected_total:
            raise RuntimeError(
                f"The DPWH total changed during the load, from {expected_total} to {total}."
            )
        expected_rows = min(page_size, expected_total - seen)
        if len(rows) != expected_rows:
            raise RuntimeError(
                f"DPWH page {page} has {len(rows)} rows. We expected {expected_rows}."
            )
        seen += len(rows)
        yield page, content, len(rows), expected_total
        if not paging["hasNext"]:
            break
        if seen >= expected_total:
            raise RuntimeError(f"DPWH says there are more pages after all {seen} rows.")
        page += 1
    if seen != expected_total:
        raise RuntimeError(f"DPWH sent {seen} of {expected_total} rows.")


def flood_pages(page_size=config.FLOOD_PAGE_SIZE):
    """Yield (page number, reply as it came, rows, total) for the flood control map layer.

    Each row is a whole map feature: its attributes and its point. Stop with an error
    if a page is short, so bronze is never replaced with part of the data.
    """
    _, reply = get_json(
        config.FLOOD_LAYER, {"where": "1=1", "returnCountOnly": "true", "f": "json"}
    )
    total = int(reply["count"])
    seen = 0
    for page, offset in enumerate(range(0, total, page_size), start=1):
        params = {
            "where": "1=1",
            "outFields": "*",
            "returnGeometry": "true",
            "orderByFields": "ObjectId",
            "resultOffset": offset,
            "resultRecordCount": page_size,
            "f": "json",
        }
        content, reply = get_json(config.FLOOD_LAYER, params)
        rows = reply["features"]
        expected_rows = min(page_size, total - offset)
        if len(rows) != expected_rows:
            raise RuntimeError(
                f"Flood page {page} has {len(rows)} rows. We expected {expected_rows}."
            )
        seen += len(rows)
        yield page, content, len(rows), total
    if seen != total:
        raise RuntimeError(f"The flood layer sent {seen} of {total} rows.")


def download(url, path, tries=4):
    """Save a file from the web to a path, like a volume folder.

    It downloads to a temporary file first, then renames it. So a cut download never
    looks like a whole file.
    """
    temporary = f"{path}.part"
    for attempt in range(1, tries + 1):
        try:
            with requests.get(
                url, headers=HEADERS, timeout=300, stream=True
            ) as response:
                response.raise_for_status()
                with open(temporary, "wb") as file:
                    file.writelines(response.iter_content(chunk_size=1 << 20))
            os.replace(temporary, path)
            return path
        except (OSError, requests.RequestException):
            if os.path.exists(temporary):
                os.remove(temporary)
            if attempt == tries:
                raise
            time.sleep(5 * attempt)
