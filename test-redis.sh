#!/bin/bash
# Test script for Redis integration

echo "Testing Redis Integration..."

# Check if containers are running
echo "Checking containers..."
docker ps | grep -E "(redis|scraper)"

# Test Redis connection
echo "Testing Redis connection..."
docker exec $(docker ps -q --filter "name=redis") redis-cli ping

# Test API health
echo "Testing API health..."
curl -k https://localhost:8443/health

# Test Redis status endpoint
echo "Testing Redis status..."
curl -k https://localhost:8443/redis/status

# Test scraping with caching
echo "Testing scrape with caching..."
curl -k -X POST https://localhost:8443/scrape \
  -H "Content-Type: application/json" \
  -d '{"query": "test", "num_products": 3}'

echo "Testing cache hit..."
curl -k -X POST https://localhost:8443/scrape \
  -H "Content-Type: application/json" \
  -d '{"query": "test", "num_products": 3}'

echo "Redis integration test completed!"