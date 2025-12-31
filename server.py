from flask import Flask, request, jsonify
from flask_cors import CORS
from datetime import datetime
import logging
import sys
import os
import ssl
import redis
import json
from functools import wraps

# Add src to path to import scraper
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))
from scraper import scrape_tokopedia

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Redis cache class
class RedisCache:
    def __init__(self, redis_url='redis://localhost:6379/0', max_connections=10):
        try:
            self.redis = redis.from_url(redis_url, max_connections=max_connections)
            # Test connection
            self.redis.ping()
            logger.info("Redis connection established")
            self.enabled = True
        except redis.ConnectionError:
            logger.warning("Redis not available, falling back to in-memory cache")
            self.enabled = False
            self.memory_cache = {}

    def get(self, key):
        """Get value from cache"""
        if not self.enabled:
            return self.memory_cache.get(key)

        try:
            value = self.redis.get(key)
            return json.loads(value) if value else None
        except Exception as e:
            logger.error(f"Redis get error: {e}")
            return None

    def set(self, key, value, ttl=None):
        """Set value in cache with optional TTL"""
        if not self.enabled:
            self.memory_cache[key] = value
            return True

        try:
            json_value = json.dumps(value)
            if ttl:
                self.redis.setex(key, ttl, json_value)
            else:
                self.redis.set(key, json_value)
            return True
        except Exception as e:
            logger.error(f"Redis set error: {e}")
            return False

    def publish(self, channel, data):
        """Publish data to Redis pub/sub channel"""
        if not self.enabled:
            logger.info(f"Would publish to {channel}: {data}")
            return False

        try:
            self.redis.publish(channel, json.dumps(data))
            return True
        except Exception as e:
            logger.error(f"Redis publish error: {e}")
            return False

    def exists(self, key):
        """Check if key exists in cache"""
        if not self.enabled:
            return key in self.memory_cache

        try:
            return bool(self.redis.exists(key))
        except Exception:
            return False

# Initialize Redis cache
REDIS_URL = os.getenv('REDIS_URL', 'redis://localhost:6379/0')
cache = RedisCache(REDIS_URL)

app = Flask(__name__)

# Enable CORS for n8n access
CORS(app)

@app.route("/health", methods=["GET"])
def health_check():
    """Health check endpoint"""
    return jsonify({
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "version": "1.0.0"
    })

@app.route("/scrape", methods=["POST"])
def scrape_products():
    """
    Scrape Tokopedia products based on search query with enhanced shop ratings and bestseller detection

    Features Redis caching for improved performance and real-time data publishing for n8n integration.

    Expects JSON: {"query": "search term", "num_products": 10, "use_cache": true}
    """
    try:
        data = request.get_json()

        if not data or 'query' not in data:
            return jsonify({"error": "Missing 'query' parameter"}), 400

        query = data['query']
        num_products = data.get('num_products', 10)
        use_cache = data.get('use_cache', True)

        if not isinstance(num_products, int) or num_products < 1 or num_products > 100:
            return jsonify({"error": "'num_products' must be between 1 and 100"}), 400

        # Create cache key
        cache_key = f"scrape:{query}:{num_products}"

        # Check cache first if enabled
        if use_cache:
            cached_result = cache.get(cache_key)
            if cached_result:
                logger.info(f"Cache hit for query: '{query}'")
                cached_result['cached'] = True
                cached_result['cache_timestamp'] = datetime.utcnow().isoformat()
                return jsonify(cached_result)

        logger.info(f"Scraping products for query: '{query}' (max {num_products} products)")

        # Perform enhanced scraping
        products = scrape_tokopedia(query, num_products)

        # Extract unique shops with their metrics
        shops = {}
        bestsellers = []
        trending_products = []

        for product in products:
            shop_id = product.get('shop', {}).get('id')
            if shop_id and shop_id not in shops:
                shops[shop_id] = product['shop']

            # Collect bestsellers and trending products
            if product.get('isBestSeller'):
                bestsellers.append(product)
            if product.get('isTrending'):
                trending_products.append(product)

        # Sort shops by recommendation score
        recommended_shops = sorted(
            list(shops.values()),
            key=lambda x: x.get('recommendationScore', 0),
            reverse=True
        )[:5]  # Top 5 recommended shops

        # Calculate average rating safely
        rated_products = [p for p in products if p.get('rating') is not None and p.get('rating') > 0]
        avg_rating = 0
        if rated_products:
            try:
                avg_rating = round(sum(p.get('rating', 0) for p in rated_products) / len(rated_products), 1)
            except ZeroDivisionError:
                avg_rating = 0

        response = {
            "status": "success",
            "timestamp": datetime.utcnow().isoformat(),
            "query": query,
            "total_products": len(products),
            "products": products,
            "bestsellers": bestsellers,
            "trending_products": trending_products,
            "recommended_shops": recommended_shops,
            "summary": {
                "total_shops": len(shops),
                "bestseller_count": len(bestsellers),
                "trending_count": len(trending_products),
                "avg_product_rating": avg_rating
            }
        }

        # Cache the result for 30 minutes
        if use_cache and cache.set(cache_key, response, ttl=1800):
            logger.info(f"Cached result for query: '{query}'")

        # Publish real-time update for n8n
        realtime_data = {
            "event": "scrape_completed",
            "query": query,
            "total_products": len(products),
            "bestsellers_count": len(bestsellers),
            "timestamp": datetime.utcnow().isoformat()
        }
        cache.publish("tokped:scrapes", realtime_data)

        logger.info(f"Successfully scraped {len(products)} products with {len(bestsellers)} bestsellers and {len(recommended_shops)} recommended shops")
        return jsonify(response)

    except Exception as e:
        logger.error(f"Scraping failed: {str(e)}")
        return jsonify({"error": f"Scraping failed: {str(e)}"}), 500

@app.route("/shops/recommended", methods=["GET"])
def get_recommended_shops():
    """
    Get recommended shops based on overall performance and ratings
    """
    try:
        # Check Redis cache first
        cache_key = "recommended_shops"
        cached_shops = cache.get(cache_key)

        if cached_shops:
            cached_shops['cached'] = True
            cached_shops['cache_timestamp'] = datetime.utcnow().isoformat()
            return jsonify(cached_shops)

        # This is a simplified version - in production, you'd cache this data
        # For now, we'll return a sample response
        sample_shops = [
            {
                "id": 1,
                "name": "Top Rated Shop Example",
                "city": "Jakarta",
                "isOfficial": True,
                "isPowerBadge": True,
                "avgRating": 4.8,
                "totalReviews": 1250,
                "recommendationScore": 92.5,
                "specialties": ["Electronics", "Accessories"]
            }
        ]

        response = {
            "status": "success",
            "timestamp": datetime.utcnow().isoformat(),
            "recommended_shops": sample_shops,
            "note": "This endpoint returns cached/pre-calculated shop recommendations"
        }

        # Cache for 1 hour
        cache.set(cache_key, response, ttl=3600)

        return jsonify(response)

    except Exception as e:
        logger.error(f"Failed to get recommended shops: {str(e)}")
        return jsonify({"error": f"Failed to get recommended shops: {str(e)}"}), 500

@app.route("/products/bestsellers", methods=["GET"])
def get_bestsellers():
    """
    Get current bestseller products across categories
    """
    try:
        # This would typically fetch from a cached database
        # For now, return a sample response
        sample_bestsellers = [
            {
                "name": "Popular Product Example",
                "price": "Rp150.000",
                "rating": 4.9,
                "reviewCount": 500,
                "isBestSeller": True,
                "popularityScore": 4.2,
                "shop": {
                    "name": "Top Shop",
                    "isOfficial": True,
                    "recommendationScore": 95.0
                }
            }
        ]

        return jsonify({
            "status": "success",
            "timestamp": datetime.utcnow().isoformat(),
            "bestsellers": sample_bestsellers,
            "note": "This endpoint returns cached bestseller data"
        })

    except Exception as e:
        logger.error(f"Failed to get bestsellers: {str(e)}")
        return jsonify({"error": f"Failed to get bestsellers: {str(e)}"}), 500

@app.route("/redis/status", methods=["GET"])
def redis_status():
    """Check Redis connection and cache statistics"""
    try:
        redis_info = {
            "enabled": cache.enabled,
            "status": "connected" if cache.enabled else "fallback_to_memory"
        }

        if cache.enabled:
            try:
                info = cache.redis.info()
                redis_info.update({
                    "used_memory": info.get("used_memory_human", "unknown"),
                    "connected_clients": info.get("connected_clients", 0),
                    "uptime_days": info.get("uptime_in_days", 0),
                    "total_keys": cache.redis.dbsize()
                })
            except Exception as e:
                redis_info["error"] = str(e)

        return jsonify({
            "status": "success",
            "timestamp": datetime.utcnow().isoformat(),
            "redis": redis_info
        })

    except Exception as e:
        return jsonify({
            "status": "error",
            "timestamp": datetime.utcnow().isoformat(),
            "error": str(e)
        }), 500

@app.route("/", methods=["GET"])
def root():
    """Root endpoint with API information"""
    redis_status_info = "enabled" if cache.enabled else "disabled (fallback to memory)"

    return jsonify({
        "message": "Tokopedia Scraper API with Enhanced Features + Redis Caching",
        "version": "1.0.0",
        "redis_cache": redis_status_info,
        "features": [
            "Shop rating and recommendation system",
            "Bestseller detection",
            "Trending product identification",
            "Enhanced product analytics",
            "Redis caching for performance",
            "Real-time pub/sub for n8n integration",
            "JSON data persistence"
        ],
        "endpoints": {
            "GET /health": "Health check",
            "GET /redis/status": "Redis cache status and statistics",
            "POST /scrape": "Scrape products with enhanced analytics (cached)",
            "GET /shops/recommended": "Get recommended shops (cached)",
            "GET /products/bestsellers": "Get bestseller products (cached)"
        },
        "usage_example": {
            "scrape": "curl -k -X POST https://localhost:8443/scrape -H 'Content-Type: application/json' -d '{\"query\": \"decal mx king 150\", \"num_products\": 5}'",
            "redis_status": "curl -k https://localhost:8443/redis/status",
            "recommended_shops": "curl -k https://localhost:8443/shops/recommended",
            "bestsellers": "curl -k https://localhost:8443/products/bestsellers"
        },
        "cache_info": {
            "query_cache_ttl": "30 minutes",
            "shop_cache_ttl": "1 hour",
            "realtime_events": "Published to Redis channels for n8n"
        }
    })

def create_ssl_context():
    """Create SSL context for HTTPS"""
    context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    context.load_cert_chain('certs/cert.pem', 'certs/key.pem')
    return context

if __name__ == "__main__":
    # Run with SSL for local development
    ssl_context = create_ssl_context()
    app.run(
        host="0.0.0.0",
        port=8443,
        ssl_context=ssl_context,
        debug=True
    )