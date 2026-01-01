"""
Enhanced HTML-based fallback scraper for Tokopedia using Beautiful Soup 4 + lxml
Provides robust alternative scraping method when GraphQL API is unavailable
Features improved HTML5 parsing, better error handling, and enhanced debugging
"""

import requests
import time
from typing import List, Dict, Any
from bs4 import BeautifulSoup
import re
import json
from datetime import datetime

def scrape_tokopedia_html(query: str, num_products: int = 10) -> List[Dict[str, Any]]:
    """
    Fallback HTML scraper using selectolax when GraphQL fails

    Args:
        query: Search query string
        num_products: Maximum number of products to return

    Returns:
        List of product dictionaries (similar format to GraphQL scraper)
    """

    # Tokopedia search URL
    search_url = f"https://www.tokopedia.com/search?st=product&q={query.replace(' ', '%20')}"

    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.5',
        'Accept-Encoding': 'gzip, deflate',
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1',
    }

    try:
        # Add delay to be respectful
        time.sleep(1)

        response = requests.get(search_url, headers=headers, timeout=15)
        response.raise_for_status()

        # Parse HTML with Beautiful Soup 4 + lxml for enhanced HTML5 support
        soup = BeautifulSoup(response.content.decode('utf-8', errors='ignore'), 'lxml')

        products = []

        # Find product containers using multiple strategies
        # IMPORTANT: Tokopedia frequently changes their HTML structure
        # To update selectors for current structure:
        # 1. Visit https://www.tokopedia.com/search?q=laptop in browser
        # 2. Open DevTools (F12) → Elements tab
        # 3. Search for product listings and note their selectors
        # 4. Update the selectors below based on what you find

        # Current selectors (may be outdated - inspect actual page to update)
        product_selectors = [
            # Try product-related data-testid attributes first (most specific)
            'div[data-testid*="product"]',              # Any data-testid containing "product"

            # Try broader patterns
            'div[class*="product"]',                   # Class names containing "product"
            'article[class*="product"]',               # Article elements with product classes
            '[data-product-id]',                       # Elements with product ID attributes

            # Legacy selectors (may still work in some cases)
            '.css-1dq1dix',
            '.css-1f2quy8',
        ]

        product_elements = []
        print(f"🔍 Trying {len(product_selectors)} product selectors...")

        for i, selector in enumerate(product_selectors, 1):
            try:
                print(f"  {i}. Trying selector: {selector}")
                elements = soup.select(selector)
                print(f"     → Found {len(elements) if elements else 0} elements")

                if elements and len(elements) > 0:
                    product_elements = elements
                    print(f"✅ SUCCESS with selector: {selector} ({len(elements)} products)")
                    break
            except Exception as e:
                print(f"     ❌ Selector failed: {e}")
                continue

        if not product_elements:
            print("❌ No selectors found any products.")
            print("🔍 Analysis: Tokopedia appears to use JavaScript/SPA for product loading")
            print("💡 Recommendation: Use GraphQL API instead of HTML scraping for better results")

            # Still provide some debug info
            print(f"📄 Page title: {soup.title.get_text() if soup.title else 'N/A'}")
            print(f"📏 HTML length: {len(str(soup))} characters")

            # Check for common SPA indicators
            scripts = soup.find_all('script')
            has_react = any('react' in str(script).lower() for script in scripts)
            has_nextjs = any('next' in str(script).lower() for script in scripts)

            if has_react or has_nextjs:
                print("🔧 Detected: React/Next.js SPA - products load via JavaScript")
            else:
                print("🔧 Detected: Traditional HTML - selectors may need updating")

        # Limit to requested number
        product_elements = product_elements[:num_products]

        print(f"📊 Total product elements found: {len(product_elements)}")

        for i, product_elem in enumerate(product_elements):
            try:
                # Extract product information using CSS selectors
                # NOTE: Field selectors also need updating based on current HTML structure
                # Inspect product elements in DevTools to find correct selectors

                # Product name - enhanced extraction with multiple fallbacks
                name_selectors = [
                    'span[data-testid="spnSRPProdName"]',
                    'a[data-testid="lnkProductContainer"] span',
                    'h3, h2, .product-name',
                    '[class*="product-name"]',
                    'span[class*="name"]',
                    'a[class*="product"] span',
                    'a[href*="/product/"]'
                ]

                name = f"Product {i+1}"  # Default fallback
                for selector in name_selectors:
                    name_elem = product_elem.select_one(selector)
                    if name_elem:
                        text = name_elem.get_text(strip=True)
                        if text and len(text) > 3:  # Filter out meaningless short text
                            name = text
                            break

                # Additional fallback: extract from element's text content
                if name == f"Product {i+1}":
                    all_text = product_elem.get_text()
                    text_parts = [t.strip() for t in all_text.split('\n') if t.strip() and len(t.strip()) > 10]
                    if text_parts:
                        name = text_parts[0]

                # Price - enhanced extraction with multiple fallbacks
                price_selectors = [
                    'span[data-testid="spnSRPProdPrice"]',
                    '.price, .final-price',
                    '[class*="price"]',
                    'span[class*="price"]',
                    '.css-1bl',
                    '[data-testid*="price"]'
                ]

                price = "N/A"  # Default fallback
                for selector in price_selectors:
                    price_elem = product_elem.select_one(selector)
                    if price_elem:
                        text = price_elem.get_text(strip=True)
                        if text and ('Rp' in text or '$' in text or 'IDR' in text or any(char.isdigit() for char in text)):
                            price = text
                            break

                # Additional fallback: look for price patterns in element text
                if price == "N/A":
                    all_text = product_elem.get_text()
                    price_match = re.search(r'Rp[\d,.]+', all_text)
                    if price_match:
                        price = price_match.group(0)

                # Rating - enhanced extraction with multiple fallbacks
                rating_selectors = [
                    'span[data-testid*="rating"]',
                    '.rating span',
                    '[class*="rating"] span',
                    'span[class*="rating"]',
                    '[data-testid*="rating"]'
                ]

                rating = 0  # Default fallback
                for selector in rating_selectors:
                    rating_elem = product_elem.select_one(selector)
                    if rating_elem:
                        rating_text = rating_elem.get_text(strip=True)
                        rating_match = re.search(r'(\d+\.?\d*)', rating_text)
                        if rating_match:
                            try:
                                rating = float(rating_match.group(1))
                                break
                            except ValueError:
                                continue

                # Review count - enhanced extraction with multiple fallbacks
                review_selectors = [
                    'span[data-testid*="review"]',
                    '.review-count',
                    '[class*="review"]',
                    'span[class*="review"]',
                    '[data-testid*="review"]'
                ]

                review_count = 0  # Default fallback
                for selector in review_selectors:
                    review_elem = product_elem.select_one(selector)
                    if review_elem:
                        review_text = review_elem.get_text(strip=True)
                        review_match = re.search(r'(\d+)', review_text)
                        if review_match:
                            try:
                                review_count = int(review_match.group(1))
                                break
                            except ValueError:
                                continue

                # Product URL - enhanced extraction with multiple fallbacks
                url_selectors = [
                    'a[data-testid="lnkProductContainer"]',
                    'a[href*="/product/"]',
                    'a[class*="product"]',
                    '[href*="/product/"]',
                    'a[href*="tokopedia.com"]'
                ]

                url = ""  # Default fallback
                for selector in url_selectors:
                    url_elem = product_elem.select_one(selector)
                    if url_elem and url_elem.get('href'):
                        url = url_elem['href']
                        if url and not url.startswith('http'):
                            url = f"https://www.tokopedia.com{url}"
                        break

                # Shop name - enhanced extraction with multiple fallbacks
                shop_selectors = [
                    'span[data-testid="spnSRPShopName"]',
                    '.shop-name, .merchant-name',
                    '[class*="shop"]',
                    'span[class*="shop"]',
                    '[data-testid*="shop"]',
                    '.css-1b6',
                    '[class*="merchant"]'
                ]

                shop_name = "Unknown Shop"  # Default fallback
                for selector in shop_selectors:
                    shop_elem = product_elem.select_one(selector)
                    if shop_elem:
                        text = shop_elem.get_text(strip=True)
                        if text and len(text) > 2:  # Filter out meaningless short text
                            shop_name = text
                            break

                # Image URL - enhanced extraction with multiple fallbacks
                image_selectors = [
                    'img[alt*="product"]',
                    'img[class*="product"]',
                    'img[src*="tokopedia-static.net"]',
                    'img[decoding="async"]',
                    'img[src*=".webp"]',
                    'img'
                ]

                image_url = ""  # Default fallback
                for selector in image_selectors:
                    image_elem = product_elem.select_one(selector)
                    if image_elem and image_elem.get('src'):
                        image_url = image_elem['src']
                        break

                # Generate synthetic ID for consistency
                product_id = hash(f"{name}_{shop_name}_{url}") % 1000000

                # Basic bestseller/trending detection (simplified)
                is_bestseller = review_count > 100 and rating >= 4.5
                is_trending = review_count > 50 and rating >= 4.0

                product = {
                    'id': product_id,
                    'name': name,
                    'price': price,
                    'imageUrl': image_url,
                    'rating': rating,
                    'reviewCount': review_count,
                    'url': url,
                    'isBestSeller': is_bestseller,
                    'isTrending': is_trending,
                    'shop': {
                        'name': shop_name,
                        'city': 'Unknown',  # HTML parsing might not get city
                        'isOfficial': False,  # Simplified
                        'recommendationScore': 50.0  # Default score
                    }
                }

                products.append(product)

            except Exception as e:
                print(f"Error parsing product {i+1}: {e}")
                continue

        print(f"HTML scraper found {len(products)} products for query: '{query}'")
        return products

    except Exception as e:
        print(f"HTML scraping failed: {e}")
        return []


def scrape_graphql_mock(query: str, num_products: int = 10) -> List[Dict[str, Any]]:
    """
    Mock GraphQL scraper for demonstration
    In production, this would contain the actual GraphQL implementation
    """
    # Simulate GraphQL API call (this is just for demonstration)
    # In reality, this would make actual GraphQL requests to Tokopedia
    import time
    time.sleep(0.5)  # Simulate network delay

    # For demo purposes, we'll simulate occasional failures
    import random
    if random.random() < 0.3:  # 30% chance of failure
        raise Exception("Simulated GraphQL API failure")

    # Return mock data
    return [
        {
            'id': hash(f"{query}_1") % 1000000,
            'name': f"GraphQL Product 1 for '{query}'",
            'price': "Rp100.000",
            'rating': 4.5,
            'reviewCount': 25,
            'url': f"https://tokopedia.com/product1-{query.replace(' ', '-')}",
            'isBestSeller': False,
            'isTrending': True,
            'shop': {
                'id': 1001,
                'name': 'GraphQL Shop',
                'city': 'Jakarta',
                'isOfficial': True,
                'recommendationScore': 85.0
            }
        }
    ][:num_products]


def scrape_with_fallback(query: str, num_products: int = 10) -> List[Dict[str, Any]]:
    """
    Main scraping function with GraphQL primary and HTML fallback

    Args:
        query: Search query
        num_products: Number of products to return

    Returns:
        List of product dictionaries
    """
    try:
        # Try GraphQL first (mock implementation)
        print(f"🔍 Attempting GraphQL scraping for: '{query}'")
        products = scrape_graphql_mock(query, num_products)

        if products and len(products) > 0:
            print(f"✅ GraphQL scraping successful: {len(products)} products")
            return products
        else:
            print("⚠️ GraphQL returned no products, trying HTML fallback")
            raise Exception("GraphQL returned empty results")

    except Exception as e:
        print(f"❌ GraphQL scraping failed: {e}")
        print("🔄 Attempting HTML fallback scraping...")

        try:
            products = scrape_tokopedia_html(query, num_products)
            if products and len(products) > 0:
                print(f"✅ HTML fallback successful: {len(products)} products")
                return products
            else:
                print("❌ HTML fallback also returned no products")
                return []
        except Exception as html_error:
            print(f"❌ HTML fallback also failed: {html_error}")
            return []


if __name__ == "__main__":
    # Test the HTML scraper
    import sys

    query = sys.argv[1] if len(sys.argv) > 1 else "laptop gaming"
    num_products = int(sys.argv[2]) if len(sys.argv) > 2 else 5

    print(f"Testing HTML scraper with query: '{query}'")
    products = scrape_tokopedia_html(query, num_products)

    print(f"\nFound {len(products)} products:")
    for i, product in enumerate(products[:3], 1):  # Show first 3
        print(f"{i}. {product['name']} - {product['price']}")