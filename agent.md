# Agent Instructions

## Purpose
This file contains instructions for AI agents working on the Tokopedia Scraper project.

---

## Project Overview

Tokopedia Scraper is a containerized Flask-RESTX API that scrapes product data from Tokopedia e-commerce site. It uses:
- **Docker Compose** for orchestration (Redis + API container)
- **Flask-RESTX** for REST API with Swagger docs
- **Redis** for caching
- **GraphQL + HTML Scraping** as fallback methods

---

## Current State

- Container runs on port 8443 (HTTPS)
- Container status: **UNHEALTHY** (healthcheck failing)
- Scraping functionality: **BROKEN** (GraphQL errors)

---

## Critical Tasks (Fix First)

### 1. Fix Container Healthcheck

The healthcheck uses `curl` but curl is not installed.

**Approach A - Install curl in Dockerfile:**
```dockerfile
RUN apt-get update && apt-get install -y curl && rm -rf /var/lib/apt/lists/*
```

**Approach B - Use Python healthcheck (Recommended):**
Modify `docker-compose.yml`:
```yaml
healthcheck:
  test: ["CMD", "python", "-c", "import urllib.request; urllib.request.urlopen('https://localhost:8443/health')"]
  interval: 30s
  timeout: 10s
  retries: 3
  start_period: 40s
```

---

### 2. Fix Scraper Import Error

The HTML scraping fallback fails with import error.

**Steps:**
1. Check `src/scraper.py` import statements
2. Ensure `sys.path` includes `src` directory
3. Fix relative imports or module structure
4. Test import with: `python -c "from src.scraper import scrape_tokopedia"`

---

### 3. Investigate Tokopedia GraphQL API Changes

The GraphQL API returns: `Invalid request schema received`

**Investigation Steps:**
1. Check current Tokopedia network requests in browser
2. Look for updated GraphQL queries
3. Check if authentication/headers required
4. Search for recent changes in Tokopedia API

**Resources:**
- Check `Tokopedia-API-Collection.postman_collection.json`
- Review `newman/` directory for test results
- Check `next_step.md` for recent investigation notes

**Search query for codesearch tool:**
```
Tokopedia GraphQL searchProducts query structure 2024 2025
```

---

## Development Workflow

### Running the Application

```bash
# Start services
docker-compose up -d

# View logs
docker-compose logs -f enterprise-api

# Check health
curl -k https://localhost:8443/health

# Test scraping
curl -k -X POST https://localhost:8443/scrape \
  -H "Content-Type: application/json" \
  -d '{"query": "sepatu", "num_products": 5}'
```

### Rebuilding Container

```bash
docker-compose build enterprise-api
docker-compose up -d enterprise-api
```

### Adding Dependencies

Edit `requirements.txt`, then rebuild:
```bash
docker-compose build --no-cache enterprise-api
```

---

## Code Structure

```
/home/ev3lynx/containerd-apps-tokped-scrap/
├── src/                    # Source code
│   ├── scraper.py         # Main scraping logic
│   └── ...
├── server_restx.py         # Flask-RESTX API entry point
├── docker-compose.yml      # Service orchestration
├── Dockerfile             # Container image definition
├── requirements.txt       # Python dependencies
└── issues.md              # Known issues (this file documents)
```

---

## Key Files to Understand

| File | Purpose |
|------|---------|
| `server_restx.py` | Flask API endpoints |
| `src/scraper.py` | Core scraping logic |
| `docker-compose.yml` | Container configuration |
| `Dockerfile` | Image build instructions |
| `requirements.txt` | Dependencies |

---

## Testing Checklist

When making changes, verify:

- [ ] Container starts without errors
- [ ] Healthcheck passes (curl or Python check)
- [ ] HTTPS endpoint responds
- [ ] `/health` returns valid JSON
- [ ] `/scrape` accepts requests
- [ ] Redis connection works
- [ ] Logs are clean (no crash traces)

---

## Security Considerations

1. **API Authentication** - Add API key or OAuth
2. **Rate Limiting** - Prevent abuse
3. **Input Validation** - Sanitize all user inputs
4. **HTTPS** - Use proper certificates
5. **Secrets** - Never commit credentials

---

## Useful Commands

```bash
# List containers
docker ps

# Container logs
docker logs containerd-apps-tokped-scrap_enterprise-api_1

# Follow logs
docker logs -f containerd-apps-tokped-scrap_enterprise-api_1

# Inspect container
docker inspect containerd-apps-tokped-scrap_enterprise-api_1

# Check health status
docker inspect --format='{{.State.Health.Status}}' containerd-apps-tokped-scrap_enterprise-api_1

# Restart container
docker-compose restart enterprise-api

# Stop all
docker-compose down
```

---

## Investigation Priorities

1. **Immediate**: Fix healthcheck to get container healthy
2. **Short-term**: Fix scraper imports to enable debugging
3. **Medium-term**: Investigate and fix GraphQL API
4. **Long-term**: Add authentication, rate limiting, monitoring

---

## Documentation Links

- `README.md` - Project documentation
- `next_step.md` - Implementation roadmap
- `next_implementation.md` - Technical details
- `current_plan.md` - Planning document
- `n8n_api_setup.md` - n8n integration guide
