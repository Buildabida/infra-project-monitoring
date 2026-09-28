"""Helpers for the websites and APIs we load data from."""

import requests

from buildabida import config

HEADERS = {"User-Agent": config.USER_AGENT}


def check(url):
    """Return "OK", "HTTP <code>" or "BLOCKED (<error>)" for one link."""
    try:
        response = requests.get(url, headers=HEADERS, timeout=20)
    except requests.RequestException as error:
        return f"BLOCKED ({type(error).__name__})"
    return "OK" if response.ok else f"HTTP {response.status_code}"
