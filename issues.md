# Issues Report - Tokopedia Scraper Container

## Generated: 2026-01-07

---

## 🔴 Critical Issues

### 1. Healthcheck Failing - Missing curl

**Severity**: Critical  
**Status**: Container marked unhealthy despite app running

**Problem**:
```
OCI runtime exec failed: exec failed: unable to start container process: 
exec: "curl": executable file not found in $PATH
```

**Root Cause**: Docker healthcheck uses `curl` but it's not installed in the container image.

**Location**: `docker-compose.yml:35`
```yaml
healthcheck:
  test: ["CMD", "curl", "-k", "-f", "https://localhost:8443/health"]
```

**Impact**:
- Container shows as "unhealthy"
- Kubernetes/orchestration systems may restart or reject the container
- Monitoring alerts triggered

---

### ✅ FIX STEP 1: Change Healthcheck to Python-based

**File**: `docker-compose.yml`

**Original (lines 34-39)**:
```yaml
    healthcheck:
      test: ["CMD", "curl", "-k", "-f", "https://localhost:8443/health"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 40s
```

**Replace with**:
```yaml
    healthcheck:
      test: ["CMD", "python", "-c", "import urllib.request; urllib.request.urlopen('https://localhost:8443/health')"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 40s
```

**Verification**:
```bash
docker-compose restart enterprise-api
docker inspect --format='{{.State.Health.Status}}' containerd-apps-tokped-scrap_enterprise-api_1
# Should return "healthy"
```

---

### 2. Tokopedia GraphQL API Not Working

**Severity**: Critical  
**Status**: 🔴 IN PROGRESS - Added v5 API support

**Problem**:
```
❌ GraphQL errors: [{'message': 'Invalid request schema received. Kindly correct it.', 'extensions': {}}}
```

**Root Cause**: Tokopedia updated their GraphQL API schema - the old `ace_search_product` API now returns `totalData: 0`.

**Location**: `src/scraper.py` - GraphQL query construction

**Investigation Results**:
- Old API (`ace_search_product_v4/v3`): Returns HTTP 200 but `totalData: 0`
- New API (`searchProductV5`): Returns HTTP 200 but `totalData: 0`
- HTML Scraping: Works but returns 0 products (JS-rendered content)

**Analysis**: Tokopedia appears to have:
1. Changed GraphQL API to require authentication/device fingerprinting
2. Moved to JavaScript-only rendering for product listings
3. Added rate limiting or IP-based blocking

**Reference**: [0xmacca/tokped](https://github.com/0xmacca/tokped) - Uses curl_cffi for TLS fingerprinting

---

### ✅ FIX STEP 3 (Partially Complete): Added GraphQL v5 API Support

**Added new function**: `scrape_tokopedia_v5()` in `src/scraper.py`

**Changes**:
- Added new endpoint: `https://gql.tokopedia.com/graphql/SearchResult/getProductResult`
- Added new query: `Search_SearchProduct` with `searchProductV5`
- Updated parameter format to URL-encoded string

**Current Status**: API responds but returns 0 products

**Next Actions**:
1. Add device fingerprinting (requires curl_cffi or similar)
2. Add authentication tokens/cookies
3. Consider using official Tokopedia Partner API
4. Use third-party service like TMAPI

**Alternative Solutions**:
1. **TMAPI Service**: https://tmapi.top/docs/tokopedia/search-apis/search-items-by-keywords
2. **Official API**: https://developer.tokopedia.com/openapi/guide/
3. **Browser Automation**: Use Playwright/Selenium for JS rendering

---

### 3. HTML Scraping Fallback Broken

**Severity**: Critical  
**Status**: Fallback method also failing

**Problem**:
```
❌ HTML scraping failed: attempted relative import with no known parent package...
```

**Root Cause**: Python import path issue in scraper module.

**Location**: `src/scraper.py` - import statements

**Impact**:
- No working fallback when GraphQL fails
- Complete scraping failure

---

### ✅ FIX STEP 3: Fix Scraper Import Errors

**File**: `src/scraper.py`

#### Sub-step 3.1: Check Import Statements
```bash
head -50 src/scraper.py
```

#### Sub-step 3.2: Fix Import Paths
Ensure imports use absolute paths from project root:
```python
# WRONG
from .utils import helper

# RIGHT
from src.utils import helper
```

#### Sub-step 3.3: Verify sys.path Setup
In `server_restx.py`, ensure src is in path:
```python
import sys
import os

src_path = os.path.join(os.path.dirname(__file__), 'src')
if src_path not in sys.path:
    sys.path.insert(0, src_path)
```

#### Sub-step 3.4: Test Imports
```bash
python -c "from src.scraper import scrape_tokopedia; print('Import OK')"
```

---

## 🟠 High Priority Issues

### 4. No Input Validation on /scrape Endpoint

**Severity**: High  
**Status**: Code review finding

**Problem**: The scrape endpoint may not properly validate input parameters.

**Location**: `server_restx.py`

---

### ✅ FIX STEP 4: Add Input Validation

**File**: `server_restx.py`

**Add validation to scrape endpoint**:
```python
@api.route('/scrape')
class Scrape(Resource):
    @api.expect(scrape_request)
    @api.response(400, 'Invalid request')
    @api.response(500, 'Scraping failed')
    def post(self):
        # Validate input
        data = api.payload
        if not data:
            return {'error': 'No input data'}, 400
        
        query = data.get('query', '').strip()
        if not query:
            return {'error': 'Query is required'}, 400
        
        if len(query) < 2:
            return {'error': 'Query too short (min 2 characters)'}, 400
        
        num_products = data.get('num_products', 10)
        if not isinstance(num_products, int) or num_products < 1 or num_products > 100:
            return {'error': 'num_products must be between 1 and 100'}, 400
        
        # ... existing code
```

---

### 5. Missing API Authentication

**Severity**: High  
**Status**: Documented but not implemented

**Problem**: API is open without authentication.

**Location**: `server_restx.py` - API definition comments

**Impact**:
- No rate limiting
- No access control
- Potential abuse

---

### ✅ FIX STEP 5: Add API Key Authentication

**File**: `server_restx.py`

**Add before request hook**:
```python
API_KEY = os.environ.get('API_KEY', '')

@app.before_request
def check_api_key():
    # Skip for health endpoint
    if request.path == '/health':
        return
    
    # Skip for docs
    if request.path.startswith('/docs'):
        return
    
    # Check API key if required
    if API_KEY:
        provided_key = request.headers.get('X-API-Key', '')
        if provided_key != API_KEY:
            return {'error': 'Invalid or missing API key'}, 401
```

**Update docker-compose.yml**:
```yaml
environment:
  - API_KEY=your-secure-api-key-here
```

---

### 6. Error Handling Not Comprehensive

**Severity**: Medium  
**Status**: Partial handling

**Problem**: Some error scenarios not caught, causing unhandled exceptions.

**Location**: `server_restx.py`

---

### ✅ FIX STEP 6: Improve Error Handling

**File**: `server_restx.py`

**Add error handlers**:
```python
@app.errorhandler(400)
def bad_request(e):
    return {'error': 'Bad request', 'message': str(e)}, 400

@app.errorhandler(404)
def not_found(e):
    return {'error': 'Not found'}, 404

@app.errorhandler(500)
def internal_error(e):
    logger.error(f"Internal error: {e}")
    return {'error': 'Internal server error'}, 500

@app.errorhandler(503)
def service_unavailable(e):
    return {'error': 'Service unavailable', 'message': str(e)}, 503
```

---

## 🟡 Medium Priority Issues

### 7. No HTTPS Certificate Management

**Severity**: Medium  
**Status**: Self-signed certs used

**Problem**: Using self-signed certificates for HTTPS.

**Location**: `src/` - SSL configuration

**Solution**: Use Let's Encrypt or proper certificates in production.

---

### ✅ FIX STEP 7: Use Proper SSL Certificates

**Option A: Let's Encrypt (Production)**
```python
# Use certbot to generate certificates
# Then update server to use real certificates
```

**Option B: Keep self-signed for development**
- Document clearly in README
- Add warning in API response

---

### 8. Missing Rate Limiting

**Severity**: Medium  
**Status**: Not implemented

**Problem**: No rate limiting on API endpoints.

**Location**: Not implemented

---

### ✅ FIX STEP 8: Add Rate Limiting

**File**: `server_restx.py`

**Add simple rate limiting**:
```python
from functools import wraps
import time

# Simple in-memory rate limiter
request_times = {}

RATE_LIMIT = 60  # requests per minute

def rate_limit(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        client_ip = request.remote_addr
        current_time = time.time()
        
        if client_ip not in request_times:
            request_times[client_ip] = []
        
        # Remove requests older than 1 minute
        request_times[client_ip] = [
            t for t in request_times[client_ip] 
            if current_time - t < 60
        ]
        
        if len(request_times[client_ip]) >= RATE_LIMIT:
            return {'error': 'Rate limit exceeded'}, 429
        
        request_times[client_ip].append(current_time)
        return f(*args, **kwargs)
    return decorated_function
```

**Use on scrape endpoint**:
```python
@api.route('/scrape')
class Scrape(Resource):
    @rate_limit
    def post(self):
        # ... existing code
```

---

### 9. Logging Could Be Improved

**Severity**: Low  
**Status**: Basic logging exists

**Problem**: Logging could be more structured for production.

**Location**: Throughout codebase

---

### ✅ FIX STEP 9: Improve Logging

**File**: `server_restx.py`

**Add structured logging**:
```python
import logging
import json
from datetime import datetime

class JSONFormatter(logging.Formatter):
    def format(self, record):
        log_record = {
            'timestamp': datetime.utcnow().isoformat(),
            'level': record.levelname,
            'message': record.getMessage(),
            'module': record.module,
            'function': record.funcName,
            'line': record.lineno
        }
        if record.exc_info:
            log_record['exception'] = self.formatException(record.exc_info)
        return json.dumps(log_record)

# Configure logging
handler = logging.StreamHandler()
handler.setFormatter(JSONFormatter())
logger = logging.getLogger(__name__)
logger.addHandler(handler)
logger.setLevel(logging.INFO)
```

---

## Summary Table

| Issue | Severity | Status | Impact |
|-------|----------|--------|--------|
| Missing curl for healthcheck | Critical | ✅ **FIXED** | Container unhealthy |
| Scraper import error | Critical | ✅ **FIXED** | No fallback available |
| GraphQL API broken | Critical | ⚠️ **PARTIAL** | Scraping not working |
| Input validation | High | ✅ **FIXED** | Security improved |
| No API authentication | High | 🔴 PENDING | Security risk |
| Error handling incomplete | Medium | 🔴 PENDING | Poor errors |
| Self-signed HTTPS | Medium | 🔴 PENDING | Browser warnings |
| No rate limiting | Medium | 🔴 PENDING | Blocking risk |
| Logging improvement | Low | 🔴 PENDING | Debugging |

---

## Execution Order

| Step | Task | File | Command | Status |
|------|------|------|---------|--------|
| 1 | Fix healthcheck | `docker-compose.yml`, `Dockerfile` | `docker-compose restart enterprise-api` | ✅ DONE |
| 2 | Fix scraper imports | `server_restx.py` | `docker-compose restart enterprise-api` | ✅ DONE |
| 3 | Investigate GraphQL | `src/scraper.py` | Added v5 API support | ⚠️ PARTIAL |
| 4 | Add validation | `server_restx.py` | ✅ DONE | PENDING |
| 5 | Add authentication | `server_restx.py`, `docker-compose.yml` | Rebuild + test | PENDING |
| 6 | Error handling | `server_restx.py` | Rebuild + test | PENDING |
| 7 | SSL certificates | `server_restx.py` | Update SSL config | PENDING |
| 8 | Rate limiting | `server_restx.py` | Rebuild + test | PENDING |
| 9 | Structured logging | `server_restx.py` | Rebuild + check logs | PENDING |

---

## Verification Commands

```bash
# After each fix
docker-compose restart enterprise-api
sleep 5

# Check health
docker inspect --format='{{.State.Health.Status}}' containerd-apps-tokped-scrap_enterprise-api_1

# Test API
curl -k https://localhost:8443/health
curl -k -X POST https://localhost:8443/scrape \
  -H "Content-Type: application/json" \
  -d '{"query": "sepatu", "num_products": 3}'

# Check logs
docker logs --tail 20 containerd-apps-tokped-scrap_enterprise-api_1
```
