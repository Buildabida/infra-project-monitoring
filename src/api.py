"""Helpers for the websites and APIs we load data from."""

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
    """Get a JSON reply. Wait and try again if the website is slow or busy."""
    for attempt in range(1, tries + 1):
        try:
            response = requests.get(
                url, params=params, headers=HEADERS, timeout=timeout
            )
            response.raise_for_status()
            return response.json()
        except (requests.RequestException, ValueError):
            if attempt == tries:
                raise
            time.sleep(5 * attempt)


def dpwh_pages(page_size=config.DPWH_PAGE_SIZE):
    """Yield (page number, projects, reported total) for every page of the DPWH API."""
    page = 1
    while True:
        body = get_json(config.DPWH_API, {"page": page, "limit": page_size})["data"]
        yield page, body["data"], body["pagination"]["totalCount"]
        if not body["pagination"]["hasNext"]:
            return
        page += 1


def flood_pages(page_size=config.FLOOD_PAGE_SIZE):
    """Yield (page number, rows, reported total) for the flood control map layer."""
    total = get_json(
        config.FLOOD_LAYER, {"where": "1=1", "returnCountOnly": "true", "f": "json"}
    )["count"]
    for page, offset in enumerate(range(0, total, page_size), start=1):
        params = {
            "where": "1=1",
            "outFields": "*",
            "returnGeometry": "false",
            "orderByFields": "ObjectId",
            "resultOffset": offset,
            "resultRecordCount": page_size,
            "f": "json",
        }
        rows = [
            feature["attributes"]
            for feature in get_json(config.FLOOD_LAYER, params)["features"]
        ]
        yield page, rows, total


def download(url, path, tries=4):
    """Save a file from the web to a path, like a volume folder."""
    for attempt in range(1, tries + 1):
        try:
            with requests.get(
                url, headers=HEADERS, timeout=300, stream=True
            ) as response:
                response.raise_for_status()
                with open(path, "wb") as file:
                    file.writelines(response.iter_content(chunk_size=1 << 20))
            return path
        except requests.RequestException:
            if attempt == tries:
                raise
            time.sleep(5 * attempt)
