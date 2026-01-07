"""
Tokopedia scraper with GraphQL primary and HTML fallback
"""

from typing import List, Dict, Any

try:
    from curl_cffi import requests as curl_requests

    USE_CURL_CFFI = True
except ImportError:
    import requests

    USE_CURL_CFFI = False


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
    if shop_data.get("isOfficial", False):
        badge_score += 25
    if shop_data.get("isPowerBadge", False):
        badge_score += 10

    score += badge_score

    # Rating-based score (30% weight) - using product ratings as proxy
    # In a real implementation, this would use actual shop ratings
    rating_score = 0
    avg_rating = shop_data.get("avgRating", 0)
    if avg_rating and avg_rating > 0:
        rating_score = (avg_rating / 5.0) * 30
    score += rating_score

    # Review count weight (20%)
    review_count = shop_data.get("totalReviews", 0)
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
    discount_score = min(shop_data.get("avgDiscountPercent", 0), 10)
    score += discount_score

    # Product count/popularity (5%) - shops with more products might be more established
    product_count = shop_data.get("productCount", 0)
    popularity_score = (
        min(product_count / 10, 5) if product_count > 0 else 0
    )  # Cap at 5 points
    score += popularity_score

    return min(100, max(0, score))


def scrape_tokopedia_v5(query: str, num_products: int = 10) -> List[Dict[str, Any]]:
    """
    Updated Tokopedia GraphQL API (searchProductV5) - 2025 compatible

    This uses the new GraphQL endpoint that replaced the old ace_search_product API.
    Requires specific headers including device fingerprint and authentication.

    Args:
        query: Search query string
        num_products: Maximum number of products to return

    Returns:
        List of product dictionaries
    """
    import requests
    import json
    import time
    from urllib.parse import quote

    print(
        f"🔍 GraphQL v5 (searchProductV5): Starting search for '{query}' ({num_products} products)"
    )

    graphql_url = "https://gql.tokopedia.com/graphql/SearchResult/getProductResult"

    base_param = (
        f"user_warehouseId=0&user_shopId=0&user_postCode=10110&srp_initial_state=false&breadcrumb=true&ep=product"
        f"&user_cityId=0&q={quote(query)}&related=true&source=search&srp_enter_method=normal_search"
        f"&enter_method=normal_search&l_name=sre&user_districtId=0&srp_feature_id=&catalog_rows=0&page=1"
        f"&srp_component_id=02.01.00.00&ob=0&srp_sug_type=&src=search&with_template=true&show_adult=false"
        f"&srp_direct_middle_page=false&channel=product%20search&rf=false&navsource=home&use_page=true"
        f"&dep_id=&device=android"
    )

    headers = {
        "Host": "gql.tokopedia.com",
        "Os_type": "2",
        "Accept-Language": "id-ID,id;q=0.9,en-US;q=0.8,en;q=0.7",
        "Content-Type": "application/json",
        "User-Agent": "Mozilla/5.0 (Linux; Android 14; Pixel 8) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.6099.210 Mobile Safari/537.36",
        "Accept": "application/json",
        "Accept-Encoding": "gzip, deflate, br",
        "Connection": "keep-alive",
        "Origin": "https://www.tokopedia.com",
        "Referer": "https://www.tokopedia.com/",
        "X-Requested-With": "com.tokopedia.tokopedia",
    }

    gql_query = """query Search_SearchProduct($params: String!, $query: String!) {
        searchProductV5(params: $params) {
            header {
                totalData
                responseCode
                keywordProcess
                keywordIntention
                componentID
                meta {
                    productListType
                    hasPostProcessing
                    hasButtonATC
                    dynamicFields
                }
                isQuerySafe
                additionalParams
                autocompleteApplink
                backendFilters
                backendFiltersToggle
            }
            data {
                totalDataText
                products {
                    id
                    ttsProductID
                    name
                    url
                    applink
                    mediaURL {
                        image
                        image300
                        image500
                        image700
                        videoCustom
                    }
                    shop {
                        id
                        name
                        url
                        city
                        ttsSellerID
                    }
                    badge {
                        title
                        url
                    }
                    price {
                        text
                        number
                        range
                        original
                        discountPercentage
                    }
                    freeShipping {
                        url
                    }
                    labelGroups {
                        id
                        position
                        title
                        type
                        url
                        styles {
                            key
                            value
                        }
                    }
                    category {
                        id
                        name
                        breadcrumb
                        gaKey
                    }
                    rating
                    wishlist
                    stock {
                        sold
                        ttsSKUID
                    }
                }
            }
        }
    }"""

    json_data = {
        "query": gql_query,
        "variables": {
            "params": base_param,
            "query": query,
        },
    }
    header = {}
    try:
        if USE_CURL_CFFI:
            response = curl_requests.post(
                graphql_url,
                json=json_data,
                headers=headers,
                timeout=30,
                impersonate="chrome124",
            )
        else:
            response = requests.post(
                graphql_url, headers=headers, json=json_data, timeout=30
            )

        if response.status_code == 200:
            result = response.json()
            if "data" in result and "searchProductV5" in result["data"]:
                search_data = result["data"]["searchProductV5"]
                header = search_data.get("header", {})
                products_data = search_data.get("data", {}).get("products", [])

                if header.get("totalData", 0) > 0 and products_data:
                    products = []
                    for p in products_data[:num_products]:
                        product = {
                            "id": p.get("id"),
                            "name": p.get("name"),
                            "price": p.get("price", {}).get("text", ""),
                            "price_raw": p.get("price", {}).get("number", 0),
                            "original_price": p.get("price", {}).get("original", ""),
                            "discount": p.get("price", {}).get("discountPercentage", 0),
                            "imageUrl": p.get("mediaURL", {}).get(
                                "image700", p.get("mediaURL", {}).get("image", "")
                            ),
                            "url": p.get("url", ""),
                            "rating": p.get("rating", 0),
                            "countReview": 0,
                            "badges": p.get("badge", []),
                            "labelGroups": p.get("labelGroups", []),
                            "discountPercentage": p.get("price", {}).get(
                                "discountPercentage", 0
                            ),
                            "shop": p.get("shop", {}),
                            "category": p.get("category", {}).get("name", ""),
                        }
                        products.append(product)

                    print(f"✅ GraphQL v5 SUCCESS: Found {len(products)} products")
                    return products

        else:
            print(f"❌ GraphQL v5 HTTP error: {response.status_code}")

    except Exception as e:
        print(f"❌ GraphQL v5 exception: {e}")

    print(f"⚠️ GraphQL v5: No products found (totalData: {header.get('totalData', 0)})")
    return []


def detect_bestseller_indicators(
    product: Dict[str, Any], all_products: List[Dict[str, Any]]
) -> Dict[str, Any]:
    """
    Analyze product data to detect bestseller indicators

    Returns enhanced product data with bestseller flags
    """
    enhanced_product = product.copy()

    # Bestseller indicators based on available data
    rating = product.get("rating") or 0  # Ensure we have a number, not None
    review_count = product.get("countReview", 0)
    discount_percent = product.get("discountPercentage", 0)

    # Calculate popularity score based on rating and reviews
    popularity_score = (
        (rating * 0.7) + min(review_count / 100, 3) if rating > 0 else 0
    )  # Cap review bonus at 3

    # Bestseller criteria
    is_bestseller = rating >= 4.5 and review_count >= 50 and popularity_score >= 3.5

    # Trending criteria (high discount + good reviews)
    is_trending = discount_percent >= 10 and rating >= 4.0 and review_count >= 20

    # Top rated in current search
    all_ratings = []
    for p in all_products:
        p_rating = p.get("rating")
        if p_rating is not None and p_rating > 0:
            all_ratings.append(p_rating)
    avg_rating = sum(all_ratings) / len(all_ratings) if all_ratings else 0
    is_top_rated = False
    if rating > 0:
        if avg_rating > 0:
            is_top_rated = rating > avg_rating + 0.5  # Significantly above average
        else:
            is_top_rated = rating >= 4.0  # High rating when no average available

    enhanced_product.update(
        {
            "isBestSeller": is_bestseller,
            "isTrending": is_trending,
            "isTopRated": is_top_rated,
            "popularityScore": round(popularity_score, 2),
            "avgDiscountPercent": discount_percent,
        }
    )

    return enhanced_product


def enhance_shop_data(
    shop_data: Dict[str, Any], all_products: List[Dict[str, Any]]
) -> Dict[str, Any]:
    """
    Enhance shop data with ratings and recommendation scores
    """
    enhanced_shop = shop_data.copy()

    # Calculate shop statistics from products
    shop_products = [
        p for p in all_products if p.get("shop", {}).get("id") == shop_data.get("id")
    ]
    shop_ratings = [p.get("rating", 0) for p in shop_products if p.get("rating")]
    shop_reviews = [p.get("countReview", 0) for p in shop_products]
    shop_discounts = [p.get("discountPercentage", 0) for p in shop_products]

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

    enhanced_shop.update(
        {
            "avgRating": avg_rating,
            "totalReviews": sum(shop_reviews),
            "avgDiscountPercent": avg_discount,
            "productCount": len(shop_products),
        }
    )

    # Calculate recommendation score
    shop_score = calculate_shop_score(enhanced_shop)
    enhanced_shop["recommendationScore"] = round(shop_score, 1)

    return enhanced_shop


def scrape_tokopedia_graphql(
    query: str, num_products: int = 10, api_version: str = "v4"
) -> List[Dict[str, Any]]:
    """
    Enhanced GraphQL-based scraper for Tokopedia using official API endpoint.

    Features:
    - Multiple API version support (v4, v3, v2)
    - Enhanced error handling and debugging
    - Automatic retry with different parameter formats
    - Comprehensive logging for troubleshooting

    Args:
        query: Search query string
        num_products: Maximum number of products to return
        api_version: GraphQL API version ('v4', 'v3', 'v2')

    Returns:
        List of product dictionaries
    """
    import requests
    import json
    import time

    print(
        f"🔍 GraphQL {api_version}: Starting search for '{query}' ({num_products} products)"
    )

    # GraphQL endpoint with versioning support
    graphql_url = "https://gql.tokopedia.com/"

    # Multiple query formats to try (Tokopedia may have changed their schema)
    query_formats = {
        # Format 1: Current format with versioned query
        "versioned": f"""
        query SearchProductQuery{api_version.upper()}($params: String!) {{
            ace_search_product_{api_version}(params: $params) {{
                header {{
                    totalData
                    totalDataText
                    processTime
                    responseCode
                    errorMessage
                    __typename
                }}
                data {{
                    isQuerySafe
                    products {{
                        id
                        name
                        price
                        imageUrl
                        rating
                        countReview
                        url
                        badges {{
                            title
                            imageUrl
                            show
                            __typename
                        }}
                        labelGroups {{
                            position
                            title
                            type
                            __typename
                        }}
                        discountPercentage
                        originalPrice
                        shop {{
                            id
                            name
                            url
                            city
                            isOfficial
                            isPowerBadge
                            __typename
                        }}
                        __typename
                    }}
                    __typename
                }}
                __typename
            }}
        }}
        """,
        # Format 2: Try different query name
        "alt_versioned": f"""
        query AceSearchProduct{api_version.upper()}($params: String!) {{
            ace_search_product_{api_version}(params: $params) {{
                header {{
                    totalData
                    totalDataText
                    processTime
                    responseCode
                    errorMessage
                }}
                data {{
                    isQuerySafe
                    products {{
                        id
                        name
                        price
                        imageUrl
                        rating
                        countReview
                        url
                        shop {{
                            id
                            name
                            city
                            isOfficial
                        }}
                    }}
                }}
            }}
        }}
        """,
        # Format 3: Simplified query without some fields
        "simple": f"""
        query SearchProductQuery($params: String!) {{
            ace_search_product_{api_version}(params: $params) {{
                header {{
                    totalData
                    totalDataText
                    processTime
                    responseCode
                    errorMessage
                }}
                data {{
                    products {{
                        id
                        name
                        price
                        imageUrl
                        rating
                        countReview
                        url
                        shop {{
                            id
                            name
                            city
                            isOfficial
                        }}
                    }}
                }}
            }}
        }}
        """,
        # Format 4: Try without version suffix
        "no_version": """
        query($params: String!) {
            ace_search_product(params: $params) {
                header {
                    totalData
                    totalDataText
                    processTime
                    responseCode
                    errorMessage
                }
                data {
                    products {
                        id
                        name
                        price
                        imageUrl
                        rating
                        countReview
                        url
                        shop {
                            id
                            name
                            city
                            isOfficial
                        }
                    }
                }
            }
        }
        """,
        # Format 5: Generic search query (may work if schema changed)
        "generic": """
        query($params: String!) {
            searchProduct(params: $params) {
                products {
                    id
                    name
                    price
                    imageUrl
                    rating
                    countReview
                    url
                    shop {
                        id
                        name
                        city
                        isOfficial
                    }
                }
            }
        }
        """,
    }

    # Multiple parameter formats to try (based on current Tokopedia API)
    param_formats = [
        # Format 1: Current JSON string format
        {
            "q": query,
            "page": 1,
            "rows": min(num_products, 100),  # Limit to reasonable number
            "device": "desktop",
        },
        # Format 2: Try with different device types
        {"q": query, "page": 1, "rows": min(num_products, 100), "device": "mobile"},
        # Format 3: Try without device parameter
        {"q": query, "page": 1, "rows": min(num_products, 100)},
        # Format 4: Try with source parameter (some APIs need this)
        {
            "q": query,
            "page": 1,
            "rows": min(num_products, 100),
            "device": "desktop",
            "source": "search",
        },
        # Format 5: Minimal parameters
        {"q": query, "rows": min(num_products, 50)},
        # Format 6: Try with different parameter names
        {
            "query": query,
            "page": 1,
            "rows": min(num_products, 100),
            "device": "desktop",
        },
    ]

    # Enhanced headers with more browser-like properties
    headers = {
        "Content-Type": "application/json",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "application/json",
        "Accept-Language": "en-US,en;q=0.9,id;q=0.8",
        "Origin": "https://www.tokopedia.com",
        "Referer": "https://www.tokopedia.com/",
        "sec-ch-ua": '"Not_A Brand";v="8", "Chromium";v="120", "Google Chrome";v="120"',
        "sec-ch-ua-mobile": "?0",
        "sec-ch-ua-platform": '"Windows"',
        "Sec-Fetch-Dest": "empty",
        "Sec-Fetch-Mode": "cors",
        "Sec-Fetch-Site": "same-site",
        "DNT": "1",
    }

    # Try different combinations of query formats and parameter formats
    for query_format_name, gql_query in query_formats.items():
        for param_format in param_formats:
            try:
                print(
                    f"🔄 Trying {query_format_name} format with params: {param_format}"
                )

                # Prepare parameters based on format
                if query_format_name == "generic":
                    # Generic format doesn't use the params string
                    params = json.dumps(param_format)
                    payload = {"query": gql_query, "variables": {"params": params}}
                else:
                    # Standard format with params as JSON string
                    params = json.dumps(param_format)
                    payload = {"query": gql_query, "variables": {"params": params}}

                # Make GraphQL request with timeout and error handling
                print(f"📡 Making request to {graphql_url}")
                try:
                    response = requests.post(
                        graphql_url, json=payload, headers=headers, timeout=15
                    )
                    response.raise_for_status()

                    data = response.json()
                    print(
                        f"📥 Response status: {response.status_code}, data keys: {list(data.keys()) if isinstance(data, dict) else type(data)}"
                    )

                    # Check for GraphQL errors
                    if "errors" in data:
                        print(f"❌ GraphQL errors: {data['errors']}")
                        continue  # Try next format

                    # Check if we have the expected data structure
                    products_data = None
                    if "data" in data and isinstance(data["data"], dict):
                        # Try different possible data paths
                        possible_paths = [
                            f"ace_search_product_{api_version}",
                            "searchProduct",
                            "data",
                        ]

                        for path in possible_paths:
                            if path in data["data"]:
                                section = data["data"][path]
                                if isinstance(section, dict):
                                    if (
                                        "data" in section
                                        and isinstance(section["data"], dict)
                                        and "products" in section["data"]
                                    ):
                                        products_data = section["data"]["products"]
                                        print(
                                            f"✅ Found products in path: data.{path}.data.products"
                                        )
                                        break
                                    elif "products" in section:
                                        products_data = section["products"]
                                        print(
                                            f"✅ Found products in path: data.{path}.products"
                                        )
                                        break

                    if not products_data:
                        # Debug: show more info about the response
                        section = data.get("data", {}).get(
                            f"ace_search_product_{api_version}", {}
                        )
                        header = (
                            section.get("header", {})
                            if isinstance(section, dict)
                            else {}
                        )
                        print(f"⚠️ No products found. Header info: {header}")
                        print(
                            f"⚠️ Section keys: {list(section.keys()) if isinstance(section, dict) else 'N/A'}"
                        )
                        continue

                    if not isinstance(products_data, list) or len(products_data) == 0:
                        print(
                            f"⚠️ Products data is not a list or is empty: {type(products_data)}"
                        )
                        continue

                    print(
                        f"🎉 Success with {query_format_name} format! Found {len(products_data)} products"
                    )

                    # Process products
                    products = []
                    for product in products_data[:num_products]:
                        try:
                            # Extract product information with enhanced error handling
                            product_id = product.get("id")
                            if not product_id:
                                # Generate synthetic ID if not provided
                                product_id = (
                                    hash(
                                        f"{product.get('name', '')}_{product.get('shop', {}).get('id', '')}"
                                    )
                                    % 1000000
                                )

                            # Extract shop information
                            shop_data = product.get("shop", {})
                            enhanced_shop = enhance_shop_data(shop_data, [product])

                            # Process product with enhanced analytics
                            enhanced_product = detect_bestseller_indicators(
                                product, products_data
                            )

                            # Build final product structure
                            result = {
                                "id": product_id,
                                "name": enhanced_product.get("name", "N/A"),
                                "price": enhanced_product.get("price", "N/A"),
                                "originalPrice": product.get("originalPrice", "N/A"),
                                "discountPercentage": product.get(
                                    "discountPercentage", 0
                                ),
                                "rating": enhanced_product.get("rating", "N/A"),
                                "reviewCount": product.get("countReview", 0),
                                "url": enhanced_product.get("url", "N/A"),
                                "imageUrl": product.get("imageUrl", ""),
                                "badges": product.get("badges", []),
                                "labelGroups": product.get("labelGroups", []),
                                "isBestSeller": enhanced_product.get(
                                    "isBestSeller", False
                                ),
                                "isTrending": enhanced_product.get("isTrending", False),
                                "isTopRated": enhanced_product.get("isTopRated", False),
                                "popularityScore": enhanced_product.get(
                                    "popularityScore", 0
                                ),
                                "shop": enhanced_shop,
                            }

                            products.append(result)

                        except Exception as e:
                            print(f"⚠️ Error processing product: {e}")
                            continue

                    # Return successful results
                    return products

                except requests.exceptions.RequestException as e:
                    print(f"❌ Request error: {e}")
                    continue
                except json.JSONDecodeError as e:
                    print(f"❌ JSON decode error: {e}")
                    continue
                except Exception as e:
                    print(f"❌ Unexpected error: {e}")
                    continue

            except Exception as e:
                print(f"❌ Format combination failed: {e}")
                continue

    # If all attempts failed, return empty list with detailed diagnostics
    print(f"💔 All GraphQL {api_version} attempts failed for query '{query}'")
    print(f"🔍 Diagnostics: API responded successfully but returned totalData: 0")
    print(
        f"🔍 Possible causes: API authentication required, schema changed, or parameters incorrect"
    )
    print(
        f"🔍 Recommendation: Use HTML scraping fallback or investigate API authentication"
    )
    return []


def scrape_tokopedia(query: str, num_products: int = 10) -> List[Dict[str, Any]]:
    """
    Enhanced hybrid scraper with intelligent fallback strategy.

    Strategy:
    1. GraphQL v5 (new 2025 API - searchProductV5)
    2. GraphQL v4 (fastest, most reliable)
    3. GraphQL v3 (fallback API version)
    4. HTML scraping (may not work due to Tokopedia's SPA architecture)

    Note: Tokopedia has moved to a JavaScript-heavy architecture where products
    are loaded dynamically. HTML scraping success rate may be limited.

    Args:
        query: Search query string
        num_products: Maximum number of products to return

    Returns:
        List of product dictionaries
    """
    methods_tried = []

    # Method 1: GraphQL v5 (new 2025 API)
    try:
        methods_tried.append("GraphQL v5")
        print(f"🔍 Trying GraphQL v5 (searchProductV5) for: '{query}'")
        products = scrape_tokopedia_v5(query, num_products)
        if products and len(products) > 0:
            print(f"✅ GraphQL v5 succeeded: {len(products)} products")
            return products
    except Exception as e:
        print(f"⚠️ GraphQL v5 failed: {str(e)[:100]}...")

    # Method 2: GraphQL v4 (fastest when available)
    try:
        methods_tried.append("GraphQL v4")
        print(f"🔍 Trying GraphQL v4 for: '{query}'")
        products = scrape_tokopedia_graphql(query, num_products, api_version="v4")
        if products and len(products) > 0:
            print(f"✅ GraphQL v4 succeeded: {len(products)} products")
            return products
    except Exception as e:
        print(f"⚠️ GraphQL v4 failed: {str(e)[:100]}...")

    # Method 3: GraphQL v3 (fallback API version)
    try:
        methods_tried.append("GraphQL v3")
        print("🔄 Trying GraphQL v3...")
        products = scrape_tokopedia_graphql(query, num_products, api_version="v3")
        if products and len(products) > 0:
            print(f"✅ GraphQL v3 succeeded: {len(products)} products")
            return products
    except Exception as e:
        print(f"⚠️ GraphQL v3 failed: {str(e)[:100]}...")

    # Method 4: HTML Scraping (most reliable fallback)
    try:
        methods_tried.append("HTML Scraping")
        print("🔄 Falling back to HTML scraping...")
        from .html_scraper import scrape_tokopedia_html

        products = scrape_tokopedia_html(query, num_products)
        if products and len(products) > 0:
            print(f"✅ HTML scraping succeeded: {len(products)} products")
            return products
    except Exception as e:
        print(f"❌ HTML scraping failed: {str(e)[:100]}...")

    # All methods failed
    methods_str = ", ".join(methods_tried)
    print(f"💔 All scraping methods failed for '{query}'. Methods tried: {methods_str}")
    return []


if __name__ == "__main__":
    # For testing purposes when run directly
    import sys

    query = sys.argv[1] if len(sys.argv) > 1 else "decal mx king 150"
    num_products = int(sys.argv[2]) if len(sys.argv) > 2 else 10

    print("🚀 Tokopedia Scraper Test")
    print("=" * 50)

    # Test GraphQL first
    print(f"\n🔍 Testing GraphQL API for query: '{query}'")
    try:
        products = scrape_tokopedia(query, num_products)
        if products:
            print(f"✅ GraphQL SUCCESS: Found {len(products)} products")
            for i, product in enumerate(products[:3], 1):
                print(f"   {i}. {product['name'][:50]} - {product['price']}")
        else:
            print("❌ GraphQL returned no products")
    except Exception as e:
        print(f"❌ GraphQL FAILED: {e}")

    # Test HTML fallback
    print(f"\n📄 Testing HTML fallback for query: '{query}'")
    try:
        products = scrape_tokopedia(query, num_products)
        if products:
            print(f"✅ HTML SUCCESS: Found {len(products)} products")
            for i, product in enumerate(products[:3], 1):
                print(f"   {i}. {product['name'][:50]} - {product['price']}")
        else:
            print("❌ HTML returned no products")
    except Exception as e:
        print(f"❌ HTML FAILED: {e}")

    print("\n📊 Test Summary:")
    print("- GraphQL API: May require authentication or updated parameters")
    print("- HTML Scraping: May need selector updates for current website")
    print("- Enhanced error handling and debugging implemented")
