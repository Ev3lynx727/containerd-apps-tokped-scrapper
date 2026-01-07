"""
Browser fingerprinting for Tokopedia API requests
Provides TLS/HTTP2 fingerprint spoofing to bypass anti-bot detection
"""

import random
import os
from curl_cffi import requests

BROWSERS = ["chrome124", "chrome120", "chrome119", "chrome110", "safari18"]

DEFAULT_HEADERS = {
    "Accept": "application/json",
    "Accept-Encoding": "gzip, deflate, br",
    "Accept-Language": "id-ID,id;q=0.9,en-US;q=0.8,en;q=0.7",
    "Connection": "keep-alive",
    "Content-Type": "application/json",
    "Origin": "https://www.tokopedia.com",
    "Referer": "https://www.tokopedia.com/",
    "X-Requested-With": "com.tokopedia.tokopedia",
}


def get_browser():
    """Get random browser for fingerprint rotation"""
    browser = os.environ.get("FINGERPRINT_BROWSER")
    if browser:
        return browser
    return random.choice(BROWSERS)


def get_session(verify: bool = False):
    """Create a curl_cffi session with browser impersonation"""
    session = requests.Session()
    session.impersonate = get_browser()
    session.verify = verify
    return session


def get_headers():
    """Get realistic headers for Tokopedia GraphQL requests"""
    ua_map = {
        "chrome124": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
        "chrome120": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "chrome119": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
        "chrome110": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/110.0.0.0 Safari/537.36",
        "safari18": "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_5) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.0 Safari/605.1.15",
    }
    browser = get_browser()
    headers = DEFAULT_HEADERS.copy()
    headers["User-Agent"] = ua_map.get(browser, ua_map["chrome124"])
    return headers


def stealth_get(url: str, params: dict = None, timeout: int = 30):
    """Make a stealth GET request with browser fingerprinting"""
    session = get_session(verify=False)
    return session.get(url, params=params, headers=get_headers(), timeout=timeout)


def stealth_post(url: str, json_data: dict = None, timeout: int = 30):
    """Make a stealth POST request with browser fingerprinting"""
    session = get_session(verify=False)
    return session.post(url, json=json_data, headers=get_headers(), timeout=timeout)
