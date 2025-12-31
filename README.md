# Tokopedia Unofficial Scraper

This is an unofficial scraper for Tokopedia product data.

**WARNING:** Unofficial scraping may violate Tokopedia's terms of service. Use at your own risk. For legitimate use, consider the official API or paid services like Apify/ScrapingBee.

## Setup

### Local Setup
1. Install dependencies: `pip install -r requirements.txt`
2. Run: `python src/scraper.py`

### Docker Setup
1. Build and run with Docker Compose: `docker-compose up --build`
2. Or build image: `docker build -t tokped-scraper .`
3. Run container: `docker run -it tokped-scraper`

### Deployment
1. Make deploy.sh executable: `chmod +x deploy.sh`
2. Run deployment: `./deploy.sh <repo_url> [volume_path]`
   - repo_url: Git repository URL to clone
   - volume_path: Optional shared volume path (default: /app/shared_volume)

## Usage

Enter a search query when prompted to get top 10 products.