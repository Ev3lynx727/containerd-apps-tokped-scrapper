import requests
import json
from typing import List, Dict, Any
from datetime import datetime, timedelta
import time

# Simple in-memory cache for shop scores
_shop_score_cache = {}
_cache_expiry = {}

def calculate_shop_score(shop_data: Dict[str, Any]) -> float:
    """
    Calculate comprehensive shop recommendation score (0-100)

    Factors considered:
    - Official/Power badge status (35% weight)
    - Product rating average (30% weight)
    - Review count (20% weight)
    - Discount offerings (10% weight)
    - Product count/popularity (5% weight)
    """
    score = 0

    # Official and Power Badge bonus (35% of score)
    badge_score = 0
    if shop_data.get('isOfficial', False):
        badge_score += 25
    if shop_data.get('isPowerBadge', False):
        badge_score += 10

    score += badge_score

    # Rating-based score (30% weight) - using product ratings as proxy
    # In a real implementation, this would use actual shop ratings
    rating_score = 0
    avg_rating = shop_data.get('avgRating', 0)
    if avg_rating and avg_rating > 0:
        rating_score = (avg_rating / 5.0) * 30
    score += rating_score

    # Review count weight (20%)
    review_count = shop_data.get('totalReviews', 0)
    if review_count > 1000:
        review_count_score = 20
    elif review_count > 500:
        review_count_score = 15
    elif review_count > 100:
        review_count_score = 10
    elif review_count > 50:
        review_count_score = 5
    else:
        review_count_score = 0
    score += review_count_score

    # Discount offerings (10%) - shops with frequent discounts get higher scores
    discount_score = min(shop_data.get('avgDiscountPercent', 0), 10)
    score += discount_score

    # Product count/popularity (5%) - shops with more products might be more established
    product_count = shop_data.get('productCount', 0)
    popularity_score = min(product_count / 10, 5) if product_count > 0 else 0  # Cap at 5 points
    score += popularity_score

    return min(100, max(0, score))

def detect_bestseller_indicators(product: Dict[str, Any], all_products: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Analyze product data to detect bestseller indicators

    Returns enhanced product data with bestseller flags
    """
    enhanced_product = product.copy()

    # Bestseller indicators based on available data
    rating = product.get('rating') or 0  # Ensure we have a number, not None
    review_count = product.get('countReview', 0)
    discount_percent = product.get('discountPercentage', 0)

    # Calculate popularity score based on rating and reviews
    popularity_score = (rating * 0.7) + min(review_count / 100, 3) if rating > 0 else 0  # Cap review bonus at 3

    # Bestseller criteria
    is_bestseller = (
        rating >= 4.5 and
        review_count >= 50 and
        popularity_score >= 3.5
    )

    # Trending criteria (high discount + good reviews)
    is_trending = (
        discount_percent >= 10 and
        rating >= 4.0 and
        review_count >= 20
    )

    # Top rated in current search
    all_ratings = []
    for p in all_products:
        p_rating = p.get('rating')
        if p_rating is not None and p_rating > 0:
            all_ratings.append(p_rating)
    avg_rating = sum(all_ratings) / len(all_ratings) if all_ratings else 0
    is_top_rated = False
    if rating > 0:
        if avg_rating > 0:
            is_top_rated = rating > avg_rating + 0.5  # Significantly above average
        else:
            is_top_rated = rating >= 4.0  # High rating when no average available

    enhanced_product.update({
        'isBestSeller': is_bestseller,
        'isTrending': is_trending,
        'isTopRated': is_top_rated,
        'popularityScore': round(popularity_score, 2),
        'avgDiscountPercent': discount_percent
    })

    return enhanced_product

def enhance_shop_data(shop_data: Dict[str, Any], all_products: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Enhance shop data with ratings and recommendation scores
    """
    enhanced_shop = shop_data.copy()

    # Calculate shop statistics from products
    shop_products = [p for p in all_products if p.get('shop', {}).get('id') == shop_data.get('id')]
    shop_ratings = [p.get('rating', 0) for p in shop_products if p.get('rating')]
    shop_reviews = [p.get('countReview', 0) for p in shop_products]
    shop_discounts = [p.get('discountPercentage', 0) for p in shop_products]

    # Shop-level aggregations
    avg_rating = 0
    if shop_ratings:
        try:
            avg_rating = round(sum(shop_ratings) / len(shop_ratings), 1)
        except ZeroDivisionError:
            avg_rating = 0

    avg_discount = 0
    if shop_discounts:
        try:
            avg_discount = round(sum(shop_discounts) / len(shop_discounts), 1)
        except ZeroDivisionError:
            avg_discount = 0

    enhanced_shop.update({
        'avgRating': avg_rating,
        'totalReviews': sum(shop_reviews),
        'avgDiscountPercent': avg_discount,
        'productCount': len(shop_products)
    })

    # Calculate recommendation score
    shop_score = calculate_shop_score(enhanced_shop)
    enhanced_shop['recommendationScore'] = round(shop_score, 1)

    # Cache the score for performance
    cache_key = f"shop_{shop_data.get('id')}"
    _shop_score_cache[cache_key] = shop_score
    _cache_expiry[cache_key] = time.time() + 3600  # Cache for 1 hour

    return enhanced_shop

def scrape_tokopedia(query: str, num_products: int = 10) -> List[Dict[str, Any]]:
    """
    Unofficial scraper for Tokopedia product search using GraphQL API.
    WARNING: May violate terms of service. Use official API for legitimate purposes.

    Args:
        query: Search query string
        num_products: Maximum number of products to return

    Returns:
        List of product dictionaries
    """
    graphql_url = 'https://gql.tokopedia.com/'

    # Enhanced GraphQL query for product search with shop ratings and bestseller data
    gql_query = '''
    query SearchProductQueryV4($params: String!) {
        ace_search_product_v4(params: $params) {
            header {
                totalData
                totalDataText
                processTime
                responseCode
                errorMessage
                __typename
            }
            data {
                isQuerySafe
                products {
                    id
                    name
                    price
                    imageUrl
                    rating
                    countReview
                    url
                    badges {
                        title
                        imageUrl
                        show
                        __typename
                    }
                    labelGroups {
                        position
                        title
                        type
                        __typename
                    }
                    discountPercentage
                    originalPrice
                    shop {
                        id
                        name
                        url
                        city
                        isOfficial
                        isPowerBadge
                        __typename
                    }
                    __typename
                }
                __typename
            }
            __typename
        }
    }
    '''

    # Build search parameters
    params = f'q={query.replace(" ", "%20")}&st=product&rows={num_products}&start=0&device=desktop&scheme=https&source=search&safe_search=false&related=true&goldmerchant=false&official=false&ob=23&pmin=0&pmax=0'

    payload = {
        'query': gql_query,
        'variables': {
            'params': params
        }
    }

    headers = {
        'Content-Type': 'application/json',
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }

    try:
        response = requests.post(graphql_url, json=payload, headers=headers, timeout=10)
        response.raise_for_status()

        data = response.json()

        if 'errors' in data:
            raise Exception(f"GraphQL Errors: {data['errors']}")

        if 'data' in data and 'ace_search_product_v4' in data['data']:
            result = data['data']['ace_search_product_v4']
            products = result['data']['products']

            # Process and enhance products with bestseller indicators
            enhanced_products = []
            for product in products:
                enhanced_product = detect_bestseller_indicators(product, products)
                enhanced_products.append(enhanced_product)

            # Group products by shop and enhance shop data
            shop_groups = {}
            for product in enhanced_products:
                shop_id = product.get('shop', {}).get('id')
                if shop_id:
                    if shop_id not in shop_groups:
                        shop_groups[shop_id] = {
                            'shop_data': product['shop'],
                            'products': []
                        }
                    shop_groups[shop_id]['products'].append(product)

            # Enhance shop data with aggregated metrics
            enhanced_shops = {}
            for shop_id, shop_info in shop_groups.items():
                try:
                    enhanced_shops[shop_id] = enhance_shop_data(shop_info['shop_data'], shop_info['products'])
                except Exception as e:
                    # Use original shop data if enhancement fails
                    enhanced_shops[shop_id] = shop_info['shop_data']

            # Build final results with enhanced shop data
            results = []
            for product in enhanced_products:
                shop_id = product.get('shop', {}).get('id')
                enhanced_shop = enhanced_shops.get(shop_id, product['shop'])

                result = {
                    'name': product.get('name', 'N/A'),
                    'price': product.get('price', 'N/A'),
                    'originalPrice': product.get('originalPrice', 'N/A'),
                    'discountPercentage': product.get('discountPercentage', 0),
                    'rating': product.get('rating', 'N/A'),
                    'reviewCount': product.get('countReview', 0),
                    'url': product.get('url', 'N/A'),
                    'badges': product.get('badges', []),
                    'labelGroups': product.get('labelGroups', []),
                    'isBestSeller': product.get('isBestSeller', False),
                    'isTrending': product.get('isTrending', False),
                    'isTopRated': product.get('isTopRated', False),
                    'popularityScore': product.get('popularityScore', 0),
                    'shop': enhanced_shop
                }
                results.append(result)

            return results
        else:
            return []

    except Exception as e:
        raise Exception(f"Scraping error: {str(e)}")

if __name__ == "__main__":
    # For testing purposes when run directly
    import sys

    query = sys.argv[1] if len(sys.argv) > 1 else "decal mx king 150"
    num_products = int(sys.argv[2]) if len(sys.argv) > 2 else 10

    try:
        products = scrape_tokopedia(query, num_products)

        if products:
            print(f"\nFound {len(products)} products for '{query}':\n")
            for i, product in enumerate(products, 1):
                print(f"{i}. {product['name']}")
                print(f"   Price: {product['price']}")
                print(f"   Shop: {product['shop']}")
                print(f"   Rating: {product['rating']}")
                print(f"   URL: {product['url']}\n")
        else:
            print("No products found.")
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)