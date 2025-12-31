import requests
from bs4 import BeautifulSoup

def scrape_tokopedia(query, num_products=10):
    """
    Unofficial scraper for Tokopedia product search.
    WARNING: May violate terms of service. Use official API for legitimate purposes.
    """
    # Construct search URL
    search_url = f"https://www.tokopedia.com/search?st=product&q={query.replace(' ', '%20')}"

    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }

    try:
        response = requests.get(search_url, headers=headers)
        response.raise_for_status()

        soup = BeautifulSoup(response.text, 'html.parser')

        # Find product containers (this may break if site changes)
        products = soup.find_all('div', class_='css-1g20a2n')[:num_products]  # Example class, may need updating

        results = []
        for product in products:
            # Extract data (selectors may need adjustment)
            name = product.find('span', class_='css-1bjwylw')  # Example
            price = product.find('span', class_='css-o5uqvq')  # Example

            name_text = name.text.strip() if name else 'N/A'
            price_text = price.text.strip() if price else 'N/A'

            results.append({
                'name': name_text,
                'price': price_text
            })

        return results

    except Exception as e:
        print(f"Error: {e}")
        return []

if __name__ == "__main__":
    query = input("Enter search query: ")
    products = scrape_tokopedia(query)

    for i, product in enumerate(products, 1):
        print(f"{i}. {product['name']} - {product['price']}")