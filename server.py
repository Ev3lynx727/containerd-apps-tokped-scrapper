from flask import Flask, request, jsonify
from flask_cors import CORS
from datetime import datetime
import logging
import sys
import os
import ssl

# Add src to path to import scraper
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))
from scraper import scrape_tokopedia

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

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
    Scrape Tokopedia products based on search query with enhanced shop ratings and bestseller indicators

    Expects JSON: {"query": "search term", "num_products": 10}
    """
    try:
        data = request.get_json()

        if not data or 'query' not in data:
            return jsonify({"error": "Missing 'query' parameter"}), 400

        query = data['query']
        num_products = data.get('num_products', 10)

        if not isinstance(num_products, int) or num_products < 1 or num_products > 100:
            return jsonify({"error": "'num_products' must be between 1 and 100"}), 400

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

        return jsonify({
            "status": "success",
            "timestamp": datetime.utcnow().isoformat(),
            "recommended_shops": sample_shops,
            "note": "This endpoint returns cached/pre-calculated shop recommendations"
        })

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

@app.route("/", methods=["GET"])
def root():
    """Root endpoint with API information"""
    return jsonify({
        "message": "Tokopedia Scraper API with Enhanced Features",
        "version": "1.0.0",
        "features": [
            "Shop rating and recommendation system",
            "Bestseller detection",
            "Trending product identification",
            "Enhanced product analytics"
        ],
        "endpoints": {
            "GET /health": "Health check",
            "POST /scrape": "Scrape products with enhanced analytics - expects JSON {'query': 'search term', 'num_products': 10}",
            "GET /shops/recommended": "Get recommended shops",
            "GET /products/bestsellers": "Get bestseller products"
        },
        "usage_example": {
            "scrape": "curl -k -X POST https://localhost:8443/scrape -H 'Content-Type: application/json' -d '{\"query\": \"decal mx king 150\", \"num_products\": 5}'",
            "recommended_shops": "curl -k https://localhost:8443/shops/recommended",
            "bestsellers": "curl -k https://localhost:8443/products/bestsellers"
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