import requests
import json

def scrape_tokopedia(query, num_products=10):
    """
    Unofficial scraper for Tokopedia product search using GraphQL API.
    WARNING: May violate terms of service. Use official API for legitimate purposes.
    """
    graphql_url = 'https://gql.tokopedia.com/'

    # GraphQL query for product search
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
                    shop {
                        name
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
            print(f"GraphQL Errors: {data['errors']}")
            return []

        if 'data' in data and 'ace_search_product_v4' in data['data']:
            result = data['data']['ace_search_product_v4']
            products = result['data']['products']

            results = []
            for product in products:
                results.append({
                    'name': product.get('name', 'N/A'),
                    'price': product.get('price', 'N/A'),
                    'shop': product.get('shop', {}).get('name', 'N/A'),
                    'rating': product.get('rating', 'N/A'),
                    'url': product.get('url', 'N/A')
                })

            return results
        else:
            print("No products found in response")
            return []

    except Exception as e:
        print(f"Error: {e}")
        return []

if __name__ == "__main__":
    query = input("Enter search query: ")
    products = scrape_tokopedia(query)

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