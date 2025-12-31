# Tokopedia Unofficial Scraper API - Enhanced Edition

This is an advanced unofficial scraper for Tokopedia product data, running as a REST API server with intelligent shop rating algorithms, bestseller detection, and seamless n8n integration.

**WARNING:** Unofficial scraping may violate Tokopedia's terms of service. Use at your own risk. For legitimate use, consider the official API or paid services like Apify/ScrapingBee.

## 🚀 Enhanced Features

- **Shop Intelligence**: Advanced recommendation algorithm (0-100 scoring)
- **Best Seller Detection**: Multi-factor analysis for truly popular products
- **Trending Analysis**: Identifies rising products and special deals
- **Real-time Analytics**: Comprehensive market intelligence
- **REST API**: JSON responses with enhanced data structures
- **HTTPS Security**: SSL/TLS encryption for secure communication
- **CORS Enabled**: Ready for web and automation integrations
- **Docker Containerized**: Production-ready deployment
- **n8n Integration**: Optimized for workflow automation

## 📋 API Endpoints

### GET /health
Health check endpoint.

**Response:**
```json
{
  "status": "healthy",
  "timestamp": "2024-12-31T10:41:31.002107",
  "version": "1.0.0"
}
```

### GET /
API information and available endpoints.

**Response:**
```json
{
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
    "POST /scrape": "Scrape products with enhanced analytics",
    "GET /shops/recommended": "Get recommended shops",
    "GET /products/bestsellers": "Get bestseller products"
  }
}
```

### POST /scrape
Enhanced product scraping with shop ratings and bestseller detection.

**Request:**
```json
{
  "query": "decal mx king 150",
  "num_products": 10
}
```

**Enhanced Response:**
```json
{
  "status": "success",
  "timestamp": "2024-12-31T10:41:45.250493",
  "query": "decal mx king 150",
  "total_products": 3,
  "products": [
    {
      "name": "STRIPING STICKER MOTOR LIS DECAL MX KING 150 exciter",
      "price": "Rp60.000",
      "originalPrice": "",
      "discountPercentage": 0,
      "rating": 0,
      "reviewCount": 5,
      "url": "https://www.tokopedia.com/...",
      "badges": [{"title": "Surakarta", "show": true}],
      "labelGroups": [{"title": "15 terjual", "type": ""}],
      "isBestSeller": false,
      "isTrending": false,
      "isTopRated": false,
      "popularityScore": 0,
      "shop": {
        "id": 970110,
        "name": "huda.ARF stripingshoop",
        "city": "Surakarta",
        "isOfficial": false,
        "isPowerBadge": false,
        "avgRating": 0,
        "totalReviews": 8,
        "avgDiscountPercent": 0,
        "productCount": 3,
        "recommendationScore": 0.3
      }
    }
  ],
  "bestsellers": [],
  "trending_products": [],
  "recommended_shops": [
    {
      "id": 970110,
      "name": "huda.ARF stripingshoop",
      "city": "Surakarta",
      "isOfficial": false,
      "isPowerBadge": false,
      "avgRating": 0,
      "totalReviews": 8,
      "recommendationScore": 0.3
    }
  ],
  "summary": {
    "total_shops": 1,
    "bestseller_count": 0,
    "trending_count": 0,
    "avg_product_rating": 0
  }
}
```

### GET /shops/recommended
Get top recommended shops based on the intelligent scoring algorithm.

**Response:**
```json
{
  "status": "success",
  "timestamp": "2024-12-31T11:13:00.281039",
  "recommended_shops": [
    {
      "id": 1,
      "name": "Top Rated Shop Example",
      "city": "Jakarta",
      "isOfficial": true,
      "isPowerBadge": true,
      "avgRating": 4.8,
      "totalReviews": 1250,
      "recommendationScore": 92.5,
      "specialties": ["Electronics", "Accessories"]
    }
  ],
  "note": "This endpoint returns cached/pre-calculated shop recommendations"
}
```

### GET /products/bestsellers
Get current bestseller products across categories.

**Response:**
```json
{
  "status": "success",
  "timestamp": "2024-12-31T11:13:08.607268",
  "bestsellers": [
    {
      "name": "Popular Product Example",
      "price": "Rp150.000",
      "rating": 4.9,
      "reviewCount": 500,
      "isBestSeller": true,
      "popularityScore": 4.2,
      "shop": {
        "name": "Top Shop",
        "isOfficial": true,
        "recommendationScore": 95.0
      }
    }
  ],
  "note": "This endpoint returns cached bestseller data"
}
```

## 🚀 Quick Start

### GitHub Container Registry (Recommended)
```bash
# Pull from GitHub Container Registry
docker pull ghcr.io/ev3lynx727/containerd-apps-tokped-scrapper:latest

# Run the container
docker run -d -p 8443:8443 --name tokped-api ghcr.io/ev3lynx727/containerd-apps-tokped-scrapper:latest

# The API will be available at https://localhost:8443
```

### Docker Compose (Local Development)
```bash
# Clone or navigate to the project directory
cd /path/to/tokped-scraper

# Build and run the container
docker-compose up --build -d

# Check if it's running
docker ps

# The API will be available at https://localhost:8443
```

### Manual Docker Build
```bash
# Build the image
docker build -t tokped-scraper .

# Run the container
docker run -d --name tokped-scraper -p 8443:8443 tokped-scraper

# Check logs
docker logs tokped-scraper
```

### Local Development
```bash
# Install dependencies
pip install -r requirements.txt

# Generate SSL certificates (for HTTPS)
openssl req -x509 -newkey rsa:4096 -keyout certs/key.pem -out certs/cert.pem -days 365 -nodes -subj "/C=US/ST=State/L=City/O=Organization/CN=localhost"

# Run the server
python server.py

# API will be available at https://localhost:8443
```

## 📊 Container Status & Registry

### Automated Builds
The container is automatically built and pushed to **GitHub Container Registry (GHCR)** on every push to the main branch:

- **Registry**: `ghcr.io/ev3lynx727/containerd-apps-tokped-scrapper`
- **Tags**: `latest`, `main`, `main-<commit-sha>`
- **Platforms**: Linux AMD64 & ARM64
- **Security**: Build attestations included

### Container Management

```bash
# Check if container is running
docker ps | grep tokped

# View container logs
docker logs tokped-api

# For docker-compose setup
docker logs containerd-apps-tokped-scrap_scraper_1

# Check health endpoint
curl -k https://localhost:8443/health

# Stop container
docker stop tokped-api
docker rm tokped-api

# Or with docker-compose
docker-compose down
```

### Registry Information

```bash
# View available tags
curl -s https://ghcr.io/v2/ev3lynx727/containerd-apps-tokped-scrapper/tags/list | jq .

# Pull specific version
docker pull ghcr.io/ev3lynx727/containerd-apps-tokped-scrapper:main

# Check image details
docker inspect ghcr.io/ev3lynx727/containerd-apps-tokped-scrapper:latest
```

## 🔄 n8n Integration & Automation

### Enhanced Workflow Setup

1. **Install n8n** (if not already installed)
2. **Create a new workflow** in n8n
3. **Add nodes** in this sequence:
   - **Schedule Trigger** → **HTTP Request** → **Split In Batches** → **Data Processing** → **Storage/Actions**

### Complete n8n Workflow Example

#### 1. Schedule Trigger Node
```
Trigger: Every 6 hours
Timezone: Your local timezone
```

#### 2. HTTP Request Node (Scrape Products)
```
Method: POST
URL: https://localhost:8443/scrape
Send Headers: ✓
  Content-Type: application/json
Send Body: ✓
Body Content Type: Raw JSON
Body:
{
  "query": "decal mx king 150",
  "num_products": 10
}
Ignore SSL Issues: ✓ (for self-signed certificates)
```

#### 3. Split In Batches Node (Process Products)
```
Batch Size: 1
Options:
  Field to Split By: products
  Options: Add Field with Original Index
```

#### 4. Function Node (Extract Shop Data)
```javascript
// Extract enhanced shop and product data
const item = $item(0, $runIndex);
const product = item.json.products[$runIndex];

return {
  product_name: product.name,
  product_price: product.price,
  product_rating: product.rating,
  is_bestseller: product.isBestSeller,
  is_trending: product.isTrending,
  popularity_score: product.popularityScore,
  shop_name: product.shop.name,
  shop_rating: product.shop.avgRating,
  shop_score: product.shop.recommendationScore,
  shop_is_official: product.shop.isOfficial,
  scraped_at: item.json.timestamp
};
```

#### 5. Google Sheets Node (Store Results)
```
Operation: Append Row
Spreadsheet ID: your_google_sheet_id
Range: Sheet1!A:L
Values to Send:
  - {{ $json.product_name }}
  - {{ $json.product_price }}
  - {{ $json.product_rating }}
  - {{ $json.is_bestseller }}
  - {{ $json.is_trending }}
  - {{ $json.popularity_score }}
  - {{ $json.shop_name }}
  - {{ $json.shop_rating }}
  - {{ $json.shop_score }}
  - {{ $json.shop_is_official }}
  - {{ $json.scraped_at }}
```

### Advanced n8n Workflows

#### Price Monitoring & Alerts
- Compare current prices with historical data
- Send Slack notifications when prices drop
- Trigger alerts for new bestsellers

#### Multi-Query Automation
```javascript
// n8n Function node for multiple queries
const queries = [
  "decal mx king 150",
  "sticker motor yamaha",
  "accessories motor",
  "helm motor"
];

return queries.map(query => ({
  json: { query: query, num_products: 5 }
}));
```

#### Shop Intelligence Dashboard
- Aggregate shop recommendation scores
- Track trending shops over time
- Generate performance reports

#### Database Integration
- Store results in PostgreSQL/MySQL
- Create historical price tracking
- Build product catalog database

## 🧪 Testing & Validation

### API Testing with curl

```bash
# Health check
curl -k https://localhost:8443/health

# Get API information
curl -k https://localhost:8443/

# Scrape products with enhanced analytics
curl -k -X POST https://localhost:8443/scrape \
  -H "Content-Type: application/json" \
  -d '{"query": "decal mx king 150", "num_products": 5}'

# Get recommended shops
curl -k https://localhost:8443/shops/recommended

# Get bestseller products
curl -k https://localhost:8443/products/bestsellers
```

### Data Structure Validation

The enhanced API returns comprehensive data:

**Product Analysis Fields:**
- `isBestSeller`: Boolean - Product meets bestseller criteria
- `isTrending`: Boolean - Product has special promotions
- `isTopRated`: Boolean - Product ranks high in search results
- `popularityScore`: Float - Calculated engagement score (0-5)
- `reviewCount`: Integer - Number of customer reviews

**Shop Intelligence Fields:**
- `recommendationScore`: Float - Overall shop rating (0-100)
- `avgRating`: Float - Average product rating across shop
- `totalReviews`: Integer - Total reviews for shop products
- `isOfficial`: Boolean - Tokopedia official store status
- `isPowerBadge`: Boolean - Premium seller status

### Performance Testing

```bash
# Test response time
time curl -k -X POST https://localhost:8443/scrape \
  -H "Content-Type: application/json" \
  -d '{"query": "laptop gaming", "num_products": 10}'

# Load testing (basic)
for i in {1..5}; do
  curl -k -X POST https://localhost:8443/scrape \
    -H "Content-Type: application/json" \
    -d '{"query": "test query '$i'", "num_products": 3}' &
done
```

## 🔧 Container Management

### Docker Commands

```bash
# View running containers
docker ps

# View container logs
docker logs containerd-apps-tokped-scrap_scraper_1

# Stop the container
docker-compose down

# Restart with rebuild
docker-compose up --build -d

# Check container health
docker ps --filter "name=tokped" --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"
```

### SSL Certificate Management

The container auto-generates self-signed certificates. For production:

```bash
# Use proper SSL certificates
# Place your certificates in certs/ directory:
# - certs/cert.pem (certificate)
# - certs/key.pem (private key)

# Or use Let's Encrypt for free certificates
```

## 🔒 Security & Production Considerations

### Security Features
- **HTTPS encryption** with SSL/TLS
- **CORS enabled** for web integrations
- **Input validation** on all endpoints
- **Error handling** without data leakage

### Production Deployment
```bash
# Use environment variables for configuration
export SCRAPER_PORT=8443
export SCRAPER_HOST=0.0.0.0

# Use proper SSL certificates
# Implement rate limiting
# Add authentication/authorization
# Set up monitoring and logging
```

### Performance Optimization
- **In-memory caching** for shop scores (1-hour TTL)
- **Connection pooling** for API requests
- **Async processing** for concurrent requests
- **Response compression** for large datasets

## 📈 Data Intelligence Features

### Shop Recommendation Algorithm
- **Official/Power Badge**: 35% weight (credibility)
- **Average Rating**: 30% weight (product quality)
- **Review Count**: 20% weight (popularity)
- **Discount Activity**: 10% weight (competitiveness)
- **Product Count**: 5% weight (scale)

### Bestseller Detection Criteria
- Rating ≥ 4.5 ⭐
- Review count ≥ 50
- Popularity score ≥ 3.5
- Combines quantitative metrics

### Analytics Insights
- **Market Trends**: Identify rising products
- **Shop Performance**: Rank sellers by multiple factors
- **Price Intelligence**: Track competitive pricing
- **Customer Engagement**: Review and rating analysis

## 🚨 Troubleshooting

### Common Issues

**Container won't start:**
```bash
# Check logs
docker logs containerd-apps-tokped-scrap_scraper_1

# Check port conflicts
netstat -tulpn | grep 8443
```

**SSL certificate errors:**
```bash
# Regenerate certificates
rm certs/*.pem
docker-compose down
docker-compose up --build
```

**API returns empty results:**
```bash
# Check Tokopedia API status
curl -k -X POST https://localhost:8443/scrape \
  -H "Content-Type: application/json" \
  -d '{"query": "test", "num_products": 1}'
```

**n8n connection issues:**
- Ensure "Ignore SSL Issues" is enabled
- Check container is running on correct port
- Verify n8n can reach localhost:8443

## 🔄 CI/CD Pipeline

### GitHub Actions Workflow
- **Trigger**: Push to main/master branches
- **Build**: Multi-platform Docker images (AMD64, ARM64)
- **Registry**: Automatic push to GHCR (`ghcr.io/ev3lynx727/containerd-apps-tokped-scrapper`)
- **Security**: Build attestation and vulnerability scanning
- **Caching**: Layer caching for faster builds

### Workflow Status
Check the build status at: https://github.com/Ev3lynx727/containerd-apps-tokped-scrapper/actions

## 📝 Changelog

### v1.0.0 - Enhanced Edition
- ✨ **Shop Intelligence**: Added comprehensive shop recommendation algorithm (0-100 scoring)
- 🏆 **Best Seller Detection**: Multi-factor analysis for identifying truly popular products
- 📈 **Trending Analysis**: Smart detection of promotional and rising products
- 🌐 **REST API Server**: Converted from CLI to production-ready API server
- 🔒 **HTTPS Security**: SSL/TLS encryption for secure communication
- 🐳 **Docker Containerization**: Full containerized deployment
- 🔄 **n8n Integration**: Optimized for workflow automation
- 📊 **Data Intelligence**: Advanced market analysis capabilities
- 🚀 **GHCR Integration**: Automated container registry builds
- 🔧 **CI/CD Pipeline**: GitHub Actions for automated deployment

### Previous Versions
- Basic CLI scraper with simple HTML parsing
- Limited product data extraction
- No shop intelligence or analytics

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your enhancements
4. Test with the API endpoints
5. Submit a pull request

## 📄 License

This project is for educational and research purposes. Use responsibly and in accordance with Tokopedia's terms of service.

## ⚠️ Legal Notice

This is an unofficial tool. Scraping may violate Tokopedia's terms of service. Use at your own risk and ensure compliance with applicable laws and regulations.