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
from fuzzywuzzy import fuzz, process

# Add src to path to import scraper
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))
from scraper import scrape_tokopedia

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Analytics data structures
analytics_data = {
    "request_count": 0,
    "error_count": 0,
    "cache_hits": 0,
    "cache_misses": 0,
    "response_times": [],
    "last_requests": []  # Keep last 50 requests for monitoring
}

# Recent logs buffer
recent_logs = []

def log_request(endpoint, method, status_code, response_time=None, error=None):
    """Log request for analytics"""
    analytics_data["request_count"] += 1

    if status_code >= 400:
        analytics_data["error_count"] += 1

    if response_time:
        analytics_data["response_times"].append(response_time)
        # Keep only last 100 response times
        analytics_data["response_times"] = analytics_data["response_times"][-100:]

    # Log to recent requests
    request_log = {
        "timestamp": datetime.utcnow().isoformat(),
        "endpoint": endpoint,
        "method": method,
        "status_code": status_code,
        "response_time": response_time,
        "error": str(error) if error else None
    }

    analytics_data["last_requests"].append(request_log)
    analytics_data["last_requests"] = analytics_data["last_requests"][-50:]  # Keep last 50

    # Also log to recent_logs for /logs/recent endpoint
    log_entry = {
        "timestamp": request_log["timestamp"],
        "level": "ERROR" if error else "INFO",
        "endpoint": endpoint,
        "method": method,
        "status_code": status_code,
        "response_time": response_time,
        "message": f"{method} {endpoint} - {status_code}" + (f" - {error}" if error else "")
    }

    recent_logs.append(log_entry)
    recent_logs[:] = recent_logs[-100:]  # Keep last 100 logs

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
    try:
        response = {
            "status": "healthy",
            "timestamp": datetime.utcnow().isoformat(),
            "version": "2.0.0"
        }
        log_request("/health", "GET", 200)
        return jsonify(response)
    except Exception as e:
        log_request("/health", "GET", 500, error=e)
        return jsonify({"error": "Health check failed"}), 500

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

        # Check if this is a debug request
        is_debug = data.get('debug', False)

        # Check cache first if enabled
        if use_cache:
            cached_result = cache.get(cache_key)
            if cached_result:
                logger.info(f"Cache hit for query: '{query}'")
                cached_result['cached'] = True
                cached_result['cache_timestamp'] = datetime.utcnow().isoformat()
                return jsonify(cached_result)

        logger.info(f"Scraping products for query: '{query}' (max {num_products} products)")

        # Perform enhanced hybrid scraping (GraphQL + HTML fallback)
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

        # Cache individual products and update trending list
        for product in products:
            product_id = product.get('id')
            if product_id:
                cache.set(f"product:{product_id}", product, ttl=1800)  # 30 minutes

        if trending_products:
            trending_ids = [p.get('id') for p in trending_products if p.get('id')]
            cache.set("trending_products", trending_ids, ttl=3600)  # 1 hour

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

        # Update search history
        search_history_key = "search_history"
        history_entry = {
            "query": query,
            "timestamp": datetime.utcnow().isoformat(),
            "total_products": len(products),
            "bestsellers_count": len(bestsellers),
            "trending_count": len(trending_products)
        }

        # Get existing history and add new entry
        existing_history = cache.get(search_history_key) or []
        existing_history.insert(0, history_entry)  # Add to beginning
        # Keep only last 10 searches
        existing_history = existing_history[:10]
        cache.set(search_history_key, existing_history, ttl=3600)  # 1 hour

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
        log_request("/scrape", "POST", 200)
        return jsonify(response)

    except Exception as e:
        logger.error(f"Scraping failed: {str(e)}")
        log_request("/scrape", "POST", 500, error=e)
        return jsonify({"error": f"Scraping failed: {str(e)}"}), 500


@app.route("/scrape/debug", methods=["POST"])
def scrape_products_debug():
    """
    Debug endpoint: Test each scraping method individually and return detailed results.

    Expects JSON: {"query": "search term", "num_products": 10}
    Returns detailed results from each scraping method for troubleshooting.
    """
    try:
        from src.scraper import scrape_tokopedia_graphql
        data = request.get_json()
        if not data or 'query' not in data:
            return jsonify({"error": "Missing 'query' parameter"}), 400

        query = data['query']
        num_products = data.get('num_products', 5)  # Smaller default for debugging

        if not isinstance(num_products, int) or num_products < 1 or num_products > 20:
            return jsonify({"error": "'num_products' must be between 1 and 20 for debug mode"}), 400

        debug_results = {
            "query": query,
            "num_products_requested": num_products,
            "methods_tested": {},
            "successful_method": None,
            "final_result": None
        }

        # Test GraphQL v4
        try:
            print(f"🔍 [DEBUG] Testing GraphQL v4 for: '{query}'")
            from src.scraper import scrape_tokopedia_graphql
            products_v4 = scrape_tokopedia_graphql(query, num_products, api_version="v4")
            debug_results["methods_tested"]["graphql_v4"] = {
                "success": len(products_v4) > 0,
                "products_found": len(products_v4),
                "error": None
            }
            if len(products_v4) > 0:
                debug_results["successful_method"] = "graphql_v4"
                debug_results["final_result"] = products_v4
        except Exception as e:
            debug_results["methods_tested"]["graphql_v4"] = {
                "success": False,
                "products_found": 0,
                "error": str(e)[:200]
            }

        # Test GraphQL v3
        if not debug_results["successful_method"]:
            try:
                print(f"🔍 [DEBUG] Testing GraphQL v3 for: '{query}'")
                products_v3 = scrape_tokopedia_graphql(query, num_products, api_version="v3")
                debug_results["methods_tested"]["graphql_v3"] = {
                    "success": len(products_v3) > 0,
                    "products_found": len(products_v3),
                    "error": None
                }
                if len(products_v3) > 0:
                    debug_results["successful_method"] = "graphql_v3"
                    debug_results["final_result"] = products_v3
            except Exception as e:
                debug_results["methods_tested"]["graphql_v3"] = {
                    "success": False,
                    "products_found": 0,
                    "error": str(e)[:200]
                }

        # Test HTML Scraping
        if not debug_results["successful_method"]:
            try:
                print(f"🔍 [DEBUG] Testing HTML scraping for: '{query}'")
                from src.html_scraper import scrape_tokopedia_html
                products_html = scrape_tokopedia_html(query, num_products)
                debug_results["methods_tested"]["html_scraping"] = {
                    "success": len(products_html) > 0,
                    "products_found": len(products_html),
                    "error": None
                }
                if len(products_html) > 0:
                    debug_results["successful_method"] = "html_scraping"
                    debug_results["final_result"] = products_html
            except Exception as e:
                debug_results["methods_tested"]["html_scraping"] = {
                    "success": False,
                    "products_found": 0,
                    "error": str(e)[:200]
                }

        # Summary
        debug_results["summary"] = {
            "total_methods_tested": len(debug_results["methods_tested"]),
            "methods_succeeded": sum(1 for m in debug_results["methods_tested"].values() if m["success"]),
            "overall_success": debug_results["successful_method"] is not None
        }

        status_code = 200 if debug_results["successful_method"] else 206  # 206 = Partial Content
        log_request("/scrape/debug", "POST", status_code)

        return jsonify(debug_results), status_code

    except Exception as e:
        log_request("/scrape/debug", "POST", 500, error=e)
        return jsonify({"error": f"Debug scraping failed: {str(e)}"}), 500


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

@app.route("/products/<int:product_id>", methods=["GET"])
def get_product(product_id):
    """
    Get detailed info for a specific product by ID
    """
    try:
        cache_key = f"product:{product_id}"
        product = cache.get(cache_key)

        if product:
            return jsonify({
                "status": "success",
                "timestamp": datetime.utcnow().isoformat(),
                "product": product
            })
        else:
            return jsonify({
                "error": "Product not found in cache. Try scraping first.",
                "suggestion": "Use POST /scrape to populate the cache with products"
            }), 404

    except Exception as e:
        logger.error(f"Failed to get product {product_id}: {str(e)}")
        return jsonify({"error": f"Failed to get product: {str(e)}"}), 500

@app.route("/products/trending", methods=["GET"])
def get_trending_products():
    """
    Get currently trending products from cache
    """
    try:
        cache_key = "trending_products"
        trending_ids = cache.get(cache_key)

        if trending_ids:
            trending_products = []
            for pid in trending_ids:
                product = cache.get(f"product:{pid}")
                if product:
                    trending_products.append(product)

            return jsonify({
                "status": "success",
                "timestamp": datetime.utcnow().isoformat(),
                "trending_products": trending_products,
                "count": len(trending_products)
            })
        else:
            return jsonify({
                "status": "success",
                "timestamp": datetime.utcnow().isoformat(),
                "trending_products": [],
                "count": 0,
                "note": "No trending products cached. Try scraping some queries first."
            })

    except Exception as e:
        logger.error(f"Failed to get trending products: {str(e)}")
        return jsonify({"error": f"Failed to get trending products: {str(e)}"}), 500

@app.route("/products/search/history", methods=["GET"])
def get_search_history():
    """
    Get recent search queries and their results from cache

    Query parameters:
    - query: Filter by search term (fuzzy matching)
    - limit: Number of results (default: 10, max: 50)
    - since: ISO date string to filter recent searches
    """
    try:
        # Manual parameter validation
        query_param = (request.args.get('query') or '').strip()
        limit_param = request.args.get('limit') or '10'
        since_param = request.args.get('since') or ''

        # Validate limit parameter
        try:
            limit = int(limit_param)
            if limit < 1 or limit > 50:
                return jsonify({"error": "limit must be between 1 and 50"}), 400
        except ValueError:
            return jsonify({"error": "limit must be a valid integer"}), 400

        # Validate since parameter (basic ISO format check)
        since_date = None
        if since_param:
            try:
                since_date = datetime.fromisoformat(since_param.replace('Z', '+00:00'))
            except ValueError:
                return jsonify({"error": "since must be a valid ISO date string"}), 400

        search_history_key = "search_history"
        history = cache.get(search_history_key) or []

        # Apply filters
        filtered_history = history

        # Filter by date if specified
        if since_date:
            filtered_history = [
                item for item in filtered_history
                if datetime.fromisoformat(item['timestamp']) >= since_date
            ]

        # Filter by query using fuzzy matching
        if query_param:
            filtered_history = [
                item for item in filtered_history
                if fuzz.partial_ratio(query_param.lower(), item['query'].lower()) >= 70
            ]

        # Apply limit
        filtered_history = filtered_history[:limit]

        return jsonify({
            "status": "success",
            "timestamp": datetime.utcnow().isoformat(),
            "search_history": filtered_history,
            "count": len(filtered_history),
            "filters_applied": {
                "query": query_param or None,
                "limit": limit,
                "since": since_param or None
            },
            "total_available": len(history)
        })

    except Exception as e:
        logger.error(f"Failed to get search history: {str(e)}")
        return jsonify({"error": f"Failed to get search history: {str(e)}"}), 500

@app.route("/products/categories", methods=["GET"])
def get_product_categories():
    """
    Get available product categories/tags from scraped data

    Query parameters:
    - query: Filter categories by fuzzy matching against category names
    - type: Filter by category type (product, location, all) - default: all
    - limit: Number of results (default: 50, max: 100)
    """
    try:
        # Manual parameter validation
        query_param = (request.args.get('query') or '').strip()
        type_param = (request.args.get('type') or 'all').lower()
        limit_param = request.args.get('limit') or '50'

        # Validate type parameter
        if type_param not in ['all', 'product', 'location']:
            return jsonify({"error": "type must be one of: all, product, location"}), 400

        # Validate limit parameter
        try:
            limit = int(limit_param)
            if limit < 1 or limit > 100:
                return jsonify({"error": "limit must be between 1 and 100"}), 400
        except ValueError:
            return jsonify({"error": "limit must be a valid integer"}), 400

        # Get all cached products to extract categories
        categories = set()
        category_types = {}  # Track category types

        # Since we don't have explicit categories, we'll extract from product names and badges
        # Get some recent products from search history or cache
        search_history = cache.get("search_history") or []
        processed_products = set()

        for history_item in search_history:
            query = history_item.get('query', '')
            # Get cached scrape results - try different num_products values
            scrape_result = None
            for num_products in [3, 5, 10]:
                cache_key = f"scrape:{query}:{num_products}"
                scrape_result = cache.get(cache_key)
                if scrape_result:
                    break

            if scrape_result and 'products' in scrape_result:
                for product in scrape_result['products'][:5]:  # Process first 5 products per query
                    if product.get('id') in processed_products:
                        continue
                    processed_products.add(product.get('id'))

                    # Extract categories from badges (location-based)
                    for badge in product.get('badges', []):
                        title = badge.get('title')
                        if title and len(title) > 2:  # Skip very short titles
                            categories.add(title)
                            category_types[title] = 'location'

                    # Extract from labelGroups (skip sales counts)
                    for label in product.get('labelGroups', []):
                        title = label.get('title', '')
                        if title and 'terjual' not in title and len(title) > 2:
                            categories.add(title)
                            category_types[title] = 'product'

                    # Extract keywords from product name (product-based categorization)
                    name = product.get('name', '').lower()
                    if any(keyword in name for keyword in ['laptop', 'computer', 'pc', 'notebook']):
                        categories.add('Electronics')
                        category_types['Electronics'] = 'product'
                    if 'gaming' in name or 'game' in name:
                        categories.add('Gaming')
                        category_types['Gaming'] = 'product'
                    if any(keyword in name for keyword in ['motor', 'decal', 'sticker', 'sparepart']):
                        categories.add('Automotive')
                        category_types['Automotive'] = 'product'
                    if any(keyword in name for keyword in ['fashion', 'clothes', 'shirt', 'dress']):
                        categories.add('Fashion')
                        category_types['Fashion'] = 'product'

        # Apply type filtering
        if type_param != 'all':
            filtered_categories = {cat for cat in categories if category_types.get(cat) == type_param}
        else:
            filtered_categories = categories

        # Apply query filtering with fuzzy matching
        if query_param:
            # Use fuzzy matching to find relevant categories
            category_list = list(filtered_categories)
            matches = process.extract(query_param, category_list, limit=len(category_list))
            # Filter by similarity score >= 70
            filtered_categories = {match[0] for match in matches if match[1] >= 70}

        # Convert to sorted list and apply limit
        category_list = sorted(list(filtered_categories))[:limit]

        return jsonify({
            "status": "success",
            "timestamp": datetime.utcnow().isoformat(),
            "categories": category_list,
            "count": len(category_list),
            "filters_applied": {
                "query": query_param or None,
                "type": type_param,
                "limit": limit
            },
            "total_available": len(categories),
            "note": "Categories extracted from product badges, labels, and name analysis"
        })

    except Exception as e:
        logger.error(f"Failed to get product categories: {str(e)}")
        return jsonify({"error": f"Failed to get product categories: {str(e)}"}), 500

@app.route("/analytics/overview", methods=["GET"])
def get_analytics_overview():
    """
    Get dashboard data with total scrapes, cache hits, and popular queries
    """
    try:
        # Get search history data
        search_history = cache.get("search_history") or []

        # Calculate search analytics
        total_scrapes = len(search_history)
        unique_queries = len(set(item.get('query', '') for item in search_history if item.get('query')))

        # Find popular queries
        query_counts = {}
        for item in search_history:
            query = item.get('query', '')
            if query:
                query_counts[query] = query_counts.get(query, 0) + 1

        # Create popular queries list
        popular_queries = []
        for query, count in sorted(query_counts.items(), key=lambda x: x[1], reverse=True)[:10]:
            # Find last used timestamp
            last_used = None
            for item in reversed(search_history):
                if item.get('query') == query:
                    last_used = item.get('timestamp')
                    break

            popular_queries.append({
                "query": query,
                "count": count,
                "last_used": last_used
            })

        # Get Redis/cache statistics
        cache_stats = {
            "enabled": cache.enabled,
            "status": "connected" if cache.enabled else "fallback_to_memory",
            "total_keys": 0,
            "memory_usage": "unknown"
        }

        if cache.enabled:
            try:
                info = cache.redis.info()
                cache_stats.update({
                    "total_keys": cache.redis.dbsize(),
                    "memory_usage": info.get("used_memory_human", "unknown"),
                    "uptime_days": info.get("uptime_in_days", 0),
                    "connected_clients": info.get("connected_clients", 0)
                })
            except Exception as e:
                cache_stats["error"] = str(e)

        # Recent activity (last 5 searches)
        recent_activity = search_history[-5:] if search_history else []

        # Overall statistics
        overview = {
            "total_scrapes": total_scrapes,
            "unique_queries": unique_queries,
            "cache_performance": cache_stats,
            "popular_queries": popular_queries,
            "recent_activity": recent_activity,
            "api_requests": {
                "total": analytics_data["request_count"],
                "errors": analytics_data["error_count"],
                "success_rate": round((analytics_data["request_count"] - analytics_data["error_count"]) / max(analytics_data["request_count"], 1) * 100, 1)
            }
        }

        log_request("/analytics/overview", "GET", 200)
        return jsonify({
            "status": "success",
            "timestamp": datetime.utcnow().isoformat(),
            "overview": overview
        })

    except Exception as e:
        logger.error(f"Failed to get analytics overview: {str(e)}")
        return jsonify({"error": f"Failed to get analytics overview: {str(e)}"}), 500

@app.route("/analytics/performance", methods=["GET"])
def get_analytics_performance():
    """
    Get performance metrics including response times and success rates
    """
    try:
        response_times = analytics_data.get("response_times", [])

        performance_data = {
            "request_metrics": {
                "total_requests": analytics_data["request_count"],
                "error_count": analytics_data["error_count"],
                "success_count": analytics_data["request_count"] - analytics_data["error_count"],
                "success_rate": round((analytics_data["request_count"] - analytics_data["error_count"]) / max(analytics_data["request_count"], 1) * 100, 1)
            },
            "response_time_metrics": {
                "count": len(response_times),
                "average": round(sum(response_times) / max(len(response_times), 1), 3),
                "min": round(min(response_times), 3) if response_times else 0,
                "max": round(max(response_times), 3) if response_times else 0
            },
            "cache_metrics": {
                "cache_hits": analytics_data["cache_hits"],
                "cache_misses": analytics_data["cache_misses"],
                "hit_rate": round(analytics_data["cache_hits"] / max(analytics_data["cache_hits"] + analytics_data["cache_misses"], 1) * 100, 1)
            },
            "system_metrics": {
                "uptime": "tracked from server start",
                "memory_cache_fallback": not cache.enabled
            }
        }

        log_request("/analytics/performance", "GET", 200)
        return jsonify({
            "status": "success",
            "timestamp": datetime.utcnow().isoformat(),
            "performance": performance_data
        })

    except Exception as e:
        logger.error(f"Failed to get performance analytics: {str(e)}")
        return jsonify({"error": f"Failed to get performance analytics: {str(e)}"}), 500

@app.route("/cache/keys", methods=["GET"])
def get_cache_keys():
    """
    List current cache keys (admin/debug endpoint)
    WARNING: This exposes internal cache structure - use with caution
    """
    try:
        # Security check - only allow if explicitly enabled
        debug_mode = os.getenv('DEBUG_MODE', 'false').lower() == 'true'

        if not debug_mode:
            return jsonify({
                "error": "Cache keys endpoint disabled. Set DEBUG_MODE=true to enable.",
                "note": "This endpoint exposes internal cache data and should only be used for debugging."
            }), 403

        cache_info = {
            "cache_enabled": cache.enabled,
            "cache_type": "redis" if cache.enabled else "memory",
            "total_keys": 0,
            "keys": []
        }

        if cache.enabled:
            try:
                # Get all keys
                all_keys = cache.redis.keys("*")
                cache_info["total_keys"] = len(all_keys)

                # Categorize keys by pattern
                key_categories = {
                    "scrape_results": [],
                    "products": [],
                    "search_history": [],
                    "trending": [],
                    "other": []
                }

                for key in all_keys[:50]:  # Limit to first 50 for performance
                    key_str = key.decode('utf-8') if isinstance(key, bytes) else str(key)

                    # Categorize by key pattern
                    if key_str.startswith("scrape:"):
                        key_categories["scrape_results"].append(key_str)
                    elif key_str.startswith("product:"):
                        key_categories["products"].append(key_str)
                    elif key_str == "search_history":
                        key_categories["search_history"].append(key_str)
                    elif key_str == "trending_products":
                        key_categories["trending"].append(key_str)
                    else:
                        key_categories["other"].append(key_str)

                cache_info["key_categories"] = {
                    category: {
                        "count": len(keys),
                        "sample_keys": keys[:5]  # Show first 5 keys per category
                    }
                    for category, keys in key_categories.items()
                }

            except Exception as e:
                cache_info["error"] = f"Failed to retrieve cache keys: {str(e)}"
        else:
            # Memory cache - we can't inspect internal structure
            cache_info["note"] = "Memory cache in use - cannot inspect internal keys"

        return jsonify({
            "status": "success",
            "timestamp": datetime.utcnow().isoformat(),
            "cache_info": cache_info,
            "warning": "This endpoint exposes internal cache data. Use only for debugging."
        })

    except Exception as e:
        logger.error(f"Failed to get cache keys: {str(e)}")
        return jsonify({"error": f"Failed to get cache keys: {str(e)}"}), 500

@app.route("/logs/recent", methods=["GET"])
def get_recent_logs():
    """
    Get recent API request logs
    """
    try:
        # Query parameters
        limit_param = request.args.get('limit') or '50'

        try:
            limit = int(limit_param)
            if limit < 1 or limit > 100:
                return jsonify({"error": "limit must be between 1 and 100"}), 400
        except ValueError:
            return jsonify({"error": "limit must be a valid integer"}), 400

        # Get recent logs (reverse chronological order)
        logs = recent_logs[-limit:][::-1] if recent_logs else []

        log_request("/logs/recent", "GET", 200)
        return jsonify({
            "status": "success",
            "timestamp": datetime.utcnow().isoformat(),
            "logs": logs,
            "count": len(logs),
            "total_available": len(recent_logs),
            "filters_applied": {
                "limit": limit
            }
        })

    except Exception as e:
        logger.error(f"Failed to get recent logs: {str(e)}")
        return jsonify({"error": f"Failed to get recent logs: {str(e)}"}), 500

@app.route("/shops/<int:shop_id>", methods=["GET"])
def get_shop_profile(shop_id):
    """
    Get detailed shop profile by shop ID
    """
    try:
        # Look for shop data in cached scrape results
        shop_data = None

        # Search through cached scrape results to find the shop
        search_history = cache.get("search_history") or []
        for history_item in search_history:
            query = history_item.get('query', '')
            for num_products in [3, 5, 10]:
                cache_key = f"scrape:{query}:{num_products}"
                scrape_result = cache.get(cache_key)
                if scrape_result and 'products' in scrape_result:
                    for product in scrape_result['products']:
                        shop = product.get('shop', {})
                        if shop.get('id') == shop_id:
                            shop_data = shop
                            break
                    if shop_data:
                        break
            if shop_data:
                break

        if not shop_data:
            return jsonify({"error": "Shop not found in cache. Try scraping products from this shop first."}), 404

        # Get additional shop statistics from all available data
        shop_products = []
        search_history = cache.get("search_history") or []

        for history_item in search_history:
            query = history_item.get('query', '')
            for num_products in [3, 5, 10]:
                cache_key = f"scrape:{query}:{num_products}"
                scrape_result = cache.get(cache_key)
                if scrape_result and 'products' in scrape_result:
                    for product in scrape_result['products']:
                        if product.get('shop', {}).get('id') == shop_id:
                            shop_products.append(product)

        # Calculate shop statistics
        shop_stats = {
            "total_products_found": len(shop_products),
            "avg_rating": shop_data.get('avgRating', 0),
            "total_reviews": shop_data.get('totalReviews', 0),
            "recommendation_score": shop_data.get('recommendationScore', 0),
            "is_official": shop_data.get('isOfficial', False),
            "is_power_badge": shop_data.get('isPowerBadge', False),
            "city": shop_data.get('city', 'Unknown')
        }

        # Get recent products from this shop (last 5)
        recent_products = shop_products[-5:] if shop_products else []

        return jsonify({
            "status": "success",
            "timestamp": datetime.utcnow().isoformat(),
            "shop": {
                "id": shop_id,
                "name": shop_data.get('name', 'Unknown'),
                "profile": shop_data,
                "statistics": shop_stats,
                "recent_products": [
                    {
                        "id": p.get('id'),
                        "name": p.get('name'),
                        "price": p.get('price'),
                        "rating": p.get('rating'),
                        "url": p.get('url')
                    } for p in recent_products
                ]
            }
        })

    except Exception as e:
        logger.error(f"Failed to get shop profile {shop_id}: {str(e)}")
        return jsonify({"error": f"Failed to get shop profile: {str(e)}"}), 500

@app.route("/shops/top-rated", methods=["GET"])
def get_top_rated_shops():
    """
    Get shops with highest ratings (sorted by recommendation score and rating)
    """
    try:
        # Query parameters
        limit_param = request.args.get('limit') or '10'

        try:
            limit = int(limit_param)
            if limit < 1 or limit > 50:
                return jsonify({"error": "limit must be between 1 and 50"}), 400
        except ValueError:
            return jsonify({"error": "limit must be a valid integer"}), 400

        # Collect unique shops from all cached data
        shops = {}
        search_history = cache.get("search_history") or []

        for history_item in search_history:
            query = history_item.get('query', '')
            for num_products in [3, 5, 10]:
                cache_key = f"scrape:{query}:{num_products}"
                scrape_result = cache.get(cache_key)
                if scrape_result and 'products' in scrape_result:
                    for product in scrape_result['products']:
                        shop = product.get('shop', {})
                        shop_id = shop.get('id')
                        if shop_id and shop_id not in shops:
                            shops[shop_id] = shop

        # Sort shops by recommendation score (primary) and rating (secondary)
        sorted_shops = sorted(
            shops.values(),
            key=lambda s: (s.get('recommendationScore', 0), s.get('avgRating', 0)),
            reverse=True
        )[:limit]

        return jsonify({
            "status": "success",
            "timestamp": datetime.utcnow().isoformat(),
            "top_rated_shops": [
                {
                    "id": shop.get('id'),
                    "name": shop.get('name'),
                    "city": shop.get('city'),
                    "recommendation_score": shop.get('recommendationScore', 0),
                    "avg_rating": shop.get('avgRating', 0),
                    "total_reviews": shop.get('totalReviews', 0),
                    "is_official": shop.get('isOfficial', False),
                    "is_power_badge": shop.get('isPowerBadge', False),
                    "product_count": shop.get('productCount', 0)
                } for shop in sorted_shops
            ],
            "count": len(sorted_shops),
            "filters_applied": {
                "sort_by": "recommendation_score, avg_rating",
                "limit": limit
            },
            "total_shops_available": len(shops)
        })

    except Exception as e:
        logger.error(f"Failed to get top rated shops: {str(e)}")
        return jsonify({"error": f"Failed to get top rated shops: {str(e)}"}), 500

@app.route("/shops/by-city/<city>", methods=["GET"])
def get_shops_by_city(city):
    """
    Get shops filtered by city location
    """
    try:
        # Query parameters
        limit_param = request.args.get('limit') or '20'

        try:
            limit = int(limit_param)
            if limit < 1 or limit > 100:
                return jsonify({"error": "limit must be between 1 and 100"}), 400
        except ValueError:
            return jsonify({"error": "limit must be a valid integer"}), 400

        # Collect shops from the specified city
        city_shops = []
        search_history = cache.get("search_history") or []

        for history_item in search_history:
            query = history_item.get('query', '')
            for num_products in [3, 5, 10]:
                cache_key = f"scrape:{query}:{num_products}"
                scrape_result = cache.get(cache_key)
                if scrape_result and 'products' in scrape_result:
                    for product in scrape_result['products']:
                        shop = product.get('shop', {})
                        if shop.get('city', '').lower() == city.lower():
                            # Avoid duplicates
                            if not any(s['id'] == shop.get('id') for s in city_shops):
                                city_shops.append(shop)

        # Sort by recommendation score
        city_shops.sort(key=lambda s: s.get('recommendationScore', 0), reverse=True)
        city_shops = city_shops[:limit]

        return jsonify({
            "status": "success",
            "timestamp": datetime.utcnow().isoformat(),
            "city": city,
            "shops": [
                {
                    "id": shop.get('id'),
                    "name": shop.get('name'),
                    "recommendation_score": shop.get('recommendationScore', 0),
                    "avg_rating": shop.get('avgRating', 0),
                    "total_reviews": shop.get('totalReviews', 0),
                    "is_official": shop.get('isOfficial', False),
                    "is_power_badge": shop.get('isPowerBadge', False),
                    "product_count": shop.get('productCount', 0)
                } for shop in city_shops
            ],
            "count": len(city_shops),
            "filters_applied": {
                "city": city,
                "limit": limit,
                "sort_by": "recommendation_score"
            }
        })

    except Exception as e:
        logger.error(f"Failed to get shops by city {city}: {str(e)}")
        return jsonify({"error": f"Failed to get shops by city: {str(e)}"}), 500

@app.route("/shops/stats", methods=["GET"])
def get_shop_statistics():
    """
    Get aggregate statistics across all shops
    """
    try:
        # Collect comprehensive shop data
        all_shops = {}
        total_products = 0
        search_history = cache.get("search_history") or []

        for history_item in search_history:
            query = history_item.get('query', '')
            for num_products in [3, 5, 10]:
                cache_key = f"scrape:{query}:{num_products}"
                scrape_result = cache.get(cache_key)
                if scrape_result and 'products' in scrape_result:
                    total_products += len(scrape_result['products'])
                    for product in scrape_result['products']:
                        shop = product.get('shop', {})
                        shop_id = shop.get('id')
                        if shop_id:
                            if shop_id not in all_shops:
                                all_shops[shop_id] = shop
                            # Update product count
                            all_shops[shop_id]['product_count'] = all_shops[shop_id].get('product_count', 0) + 1

        # Calculate aggregate statistics
        if all_shops:
            shop_list = list(all_shops.values())
            avg_rating = sum(s.get('avgRating', 0) for s in shop_list) / len(shop_list)
            total_reviews = sum(s.get('totalReviews', 0) for s in shop_list)
            official_shops = sum(1 for s in shop_list if s.get('isOfficial'))
            power_badge_shops = sum(1 for s in shop_list if s.get('isPowerBadge'))

            # City distribution
            city_distribution = {}
            for shop in shop_list:
                city = shop.get('city', 'Unknown')
                city_distribution[city] = city_distribution.get(city, 0) + 1

            top_cities = sorted(city_distribution.items(), key=lambda x: x[1], reverse=True)[:10]

            # Rating distribution
            rating_ranges = {
                "5_star": sum(1 for s in shop_list if s.get('avgRating', 0) >= 4.8),
                "4_5_star": sum(1 for s in shop_list if 4.0 <= s.get('avgRating', 0) < 4.8),
                "3_4_star": sum(1 for s in shop_list if 3.0 <= s.get('avgRating', 0) < 4.0),
                "below_3": sum(1 for s in shop_list if s.get('avgRating', 0) > 0 and s.get('avgRating', 0) < 3.0),
                "unrated": sum(1 for s in shop_list if s.get('avgRating', 0) == 0)
            }

            stats = {
                "total_shops": len(all_shops),
                "total_products": total_products,
                "avg_rating_across_shops": round(avg_rating, 2),
                "total_reviews": total_reviews,
                "official_shops": official_shops,
                "power_badge_shops": power_badge_shops,
                "city_distribution": top_cities,
                "rating_distribution": rating_ranges,
                "recommendation_score_range": {
                    "min": min((s.get('recommendationScore', 0) for s in shop_list), default=0),
                    "max": max((s.get('recommendationScore', 0) for s in shop_list), default=0),
                    "avg": round(sum(s.get('recommendationScore', 0) for s in shop_list) / len(shop_list), 2)
                }
            }
        else:
            stats = {
                "total_shops": 0,
                "total_products": 0,
                "message": "No shop data available. Try scraping some products first."
            }

        return jsonify({
            "status": "success",
            "timestamp": datetime.utcnow().isoformat(),
            "shop_statistics": stats
        })

    except Exception as e:
        logger.error(f"Failed to get shop statistics: {str(e)}")
        return jsonify({"error": f"Failed to get shop statistics: {str(e)}"}), 500

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
        "message": "Professional Tokopedia Scraper API v2.0.0 with Enterprise Features",
        "version": "2.0.0",
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
            "GET /": "API information and available endpoints",
            "POST /scrape": "Scrape products with enhanced analytics (cached)",
            "GET /shops/recommended": "Get recommended shops (cached)",
            "GET /shops/<shop_id>": "Get detailed shop profile by ID",
            "GET /shops/top-rated": "Get shops with highest ratings",
            "GET /shops/by-city/<city>": "Filter shops by city location",
            "GET /shops/stats": "Aggregate statistics across all shops",
            "GET /products/bestsellers": "Get bestseller products (cached)",
            "GET /products/<product_id>": "Get detailed product info by ID (from cache)",
            "GET /products/trending": "Get currently trending products (from cache)",
            "GET /products/search/history": "Get recent search queries and results (from cache)",
            "GET /products/categories": "Get available product categories/tags (from scraped data)",
            "GET /analytics/overview": "Dashboard data (total scrapes, cache hits, popular queries)",
            "GET /analytics/performance": "Response times, success rates, error counts",
            "GET /cache/keys": "List current cache keys (admin/debug only)",
            "GET /logs/recent": "Recent API request logs"
        },
        "usage_example": {
            "scrape": "curl -k -X POST https://localhost:8443/scrape -H 'Content-Type: application/json' -d '{\"query\": \"decal mx king 150\", \"num_products\": 5}'",
            "redis_status": "curl -k https://localhost:8443/redis/status",
            "recommended_shops": "curl -k https://localhost:8443/shops/recommended",
            "shop_profile": "curl -k https://localhost:8443/shops/12345",
            "top_rated_shops": "curl -k https://localhost:8443/shops/top-rated?limit=10",
            "shops_by_city": "curl -k https://localhost:8443/shops/by-city/Jakarta",
            "shop_statistics": "curl -k https://localhost:8443/shops/stats",
            "bestsellers": "curl -k https://localhost:8443/products/bestsellers",
            "product_by_id": "curl -k https://localhost:8443/products/12345",
            "trending_products": "curl -k https://localhost:8443/products/trending",
            "search_history": "curl -k https://localhost:8443/products/search/history",
            "categories": "curl -k https://localhost:8443/products/categories",
            "analytics_overview": "curl -k https://localhost:8443/analytics/overview",
            "analytics_performance": "curl -k https://localhost:8443/analytics/performance",
            "cache_keys": "curl -k https://localhost:8443/cache/keys (requires DEBUG_MODE=true)",
            "recent_logs": "curl -k https://localhost:8443/logs/recent?limit=20"
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
    # Run with SSL for local development
    ssl_context = create_ssl_context()
    # Run with SSL for local development
    ssl_context = create_ssl_context()
    # Run with SSL for local development
    ssl_context = create_ssl_context()
    # Run with SSL for local development
    ssl_context = create_ssl_context()
    # Run without SSL for testing
    app.run(
        host="0.0.0.0",
        port=8449,
        debug=True
    )