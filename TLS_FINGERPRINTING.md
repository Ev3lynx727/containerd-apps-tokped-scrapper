# TLS Fingerprinting Documentation

## Overview

This document describes the TLS fingerprinting implementation using `curl_cffi` to bypass anti-bot detection when scraping Tokopedia's GraphQL API.

## What is TLS Fingerprinting?

TLS fingerprinting is a technique used by websites to identify clients based on their TLS handshake characteristics. Each HTTP client (browser, curl, Python requests) has a unique "fingerprint" that can be used to detect and block automated requests.

### JA3 Fingerprint Example

```
Standard Python requests:
771,4865-4866-4867-49195-49199-49196-49200-52393-52392-49171-49172-156-157-47-53,0-23-65281-10-11-35-16-5-13-18-51-45-43-27-21,29-23-24,0

Browser (Chrome):
771,4865-4867-49195-49199-49196-49200-52393-52392-49171-49172-156-157-47-53,0-23-65281-10-11-35-16-5-13-18-51-43-27-65037,29-23-24,0
```

## Implementation

### Dependencies

```bash
pip install curl_cffi>=0.6.0
```

### Source Files

| File | Purpose |
|------|---------|
| `src/fingerprint.py` | Browser fingerprinting utilities |
| `src/scraper.py` | Uses curl_cffi for GraphQL requests |

### Usage Example

```python
from src.fingerprint import stealth_post, get_headers

# Make a request with browser fingerprint
response = stealth_post(
    url="https://gql.tokopedia.com/graphql/SearchResult/getProductResult",
    json_data={
        "query": gql_query,
        "variables": {"params": params, "query": query}
    }
)
```

### Available Browsers

```python
BROWSERS = ["chrome124", "chrome120", "chrome119", "chrome110", "safari18"]
```

| Browser | Impersonation String |
|---------|---------------------|
| Chrome 124 | `chrome124` |
| Chrome 120 | `chrome120` |
| Chrome 119 | `chrome119` |
| Chrome 110 | `chrome110` |
| Safari 18 | `safari18` |

### Environment Variables

| Variable | Purpose | Default |
|----------|---------|---------|
| `FINGERPRINT_BROWSER` | Override browser selection | Random from list |

### Custom Headers

The module includes realistic browser headers:

```python
{
    "Accept": "application/json",
    "Accept-Encoding": "gzip, deflate, br",
    "Accept-Language": "id-ID,id;q=0.9,en-US;q=0.8,en;q=0.7",
    "Connection": "keep-alive",
    "Content-Type": "application/json",
    "Origin": "https://www.tokopedia.com",
    "Referer": "https://www.tokopedia.com/",
    "X-Requested-With": "com.tokopedia.tokopedia",
}
```

## API Reference

### Functions

#### `get_session(verify=False)`

Create a curl_cffi session with browser impersonation.

```python
session = get_session(verify=False)
response = session.get(url)
```

#### `get_headers()`

Get realistic headers for Tokopedia GraphQL requests.

```python
headers = get_headers()
# Returns dict with User-Agent and other headers
```

#### `stealth_get(url, params=None, timeout=30)`

Make a stealth GET request with browser fingerprinting.

```python
response = stealth_get(url, params={"key": "value"})
```

#### `stealth_post(url, json_data=None, timeout=30)`

Make a stealth POST request with browser fingerprinting.

```python
response = stealth_post(url, json_data={"query": "...", "variables": {...}})
```

## How It Works

1. **TLS Handshake**: curl_cffi performs TLS handshake with browser-like parameters
2. **JA3 Fingerprint**: Generates a JA3 fingerprint matching the target browser
3. **HTTP/2 Fingerprint**: Uses HTTP/2 characteristics matching the browser
4. **Headers**: Includes realistic browser headers (User-Agent, Accept, etc.)
5. **Origin Check**: Passes Origin/Referer checks

## Testing

### Verify Fingerprint

```python
from curl_cffi import requests

# Test fingerprint matching
r = requests.get("https://tls.browserleaks.com/json", impersonate="chrome124")
print(r.json()["ja3n_hash"])
```

### Test Tokopedia API

```bash
# Test with curl_cffi
python -c "
from src.scraper import scrape_tokopedia_v5
products = scrape_tokopedia_v5('sepatu', 3)
print(f'Found {len(products)} products')
"
```

## Troubleshooting

### Fingerprint Mismatch

If Tokopedia still blocks requests:
1. Try different browser version
2. Add cookie management
3. Consider using proxy rotation
4. Check for additional required headers

### Performance Impact

- curl_cffi adds minimal overhead (~50ms per request)
- Session reuse recommended for multiple requests
- Browser rotation increases overhead

## Limitations

1. **Not a Silver Bullet**: Some sites use additional detection methods
2. **IP-Based Blocking**: TLS fingerprinting won't help if IP is blocked
3. **Dynamic Changes**: Browsers update, fingerprints may change
4. **Pro Feature**: Random browser selection (`realworld`) requires paid version

## Alternative Solutions

| Solution | Pros | Cons |
|----------|------|------|
| curl_cffi | Open source, easy to use | Basic fingerprinting |
| CycleTLS | Go-based, customizable | More complex |
| AzureTLS | Good for Microsoft services | Limited browser support |
| Playwright | Full browser automation | Heavy resource usage |
| Official API | Reliable, supported | May require partnership |

## References

- [curl_cffi GitHub](https://github.com/lexiforest/curl_cffi)
- [curl-impersonate](https://github.com/lwthiker/curl-impersonate)
- [JA3 Fingerprinting](https://github.com/salesforce/ja3)
- [Tokopaedi Reference](https://github.com/0xmacca/tokped)

---

## Changelog

### v1.0.0 - Initial Implementation

- Added curl_cffi dependency
- Created `src/fingerprint.py` module
- Implemented browser impersonation
- Added header generation
- Integrated with scraper
