# n8n API Integration Setup with Tokopedia Scraper

> **Intermediate Level Guide** - Production-ready n8n workflows with AI/LLM integration, database operations, and cloud deployment

This comprehensive guide shows intermediate n8n users how to build production-ready workflows that integrate with the Tokopedia scraper API, leverage AI/LLM capabilities, and use database operations for data persistence.

## 🎯 Overview

This setup combines:
- **Tokopedia Scraper API** - Product intelligence and market data
- **n8n Workflows** - Automation and data processing
- **AI/LLM Integration** - Smart data analysis and insights
- **Database Operations** - Data persistence and querying
- **Cloud Deployment** - Production-ready hosting

## 📋 Prerequisites

- n8n instance (local or cloud)
- Tokopedia Scraper API running (local or remote)
- OpenRouter API key (for cloud LLM) OR local LLM setup
- Basic understanding of n8n workflows

---

## 🚀 Deployment Options

### Option A: Local Development Setup

#### 1. Install n8n Locally

```bash
# Using npm
npm install n8n -g

# Or using Docker
docker run -d \
  --name n8n \
  -p 5678:5678 \
  -v ~/.n8n:/home/node/.n8n \
  -e N8N_BASIC_AUTH_ACTIVE=true \
  -e N8N_BASIC_AUTH_USER=user \
  -e N8N_BASIC_AUTH_PASSWORD=password \
  docker.n8n.io/n8nio/n8n:latest

# Access at http://localhost:5678
```

#### 2. Start Tokopedia Scraper API

```bash
# If using Docker Compose
docker-compose up -d

# Or run directly
python server.py
# API available at https://localhost:8443
```

#### 3. Local LLM Setup (Optional)

```bash
# Using Ollama for local LLM
curl -fsSL https://ollama.ai/install.sh | sh

# Pull a model
ollama pull llama2:7b

# Run the model
ollama serve
```

### Option B: Cloud Deployment (n8n Cloud + VPS)

#### 1. n8n Cloud Setup

```bash
# Sign up at https://n8n.cloud
# Create a new instance
# Get your webhook URL for external access
```

#### 2. VPS Setup for Scraper API

```bash
# On your VPS (Ubuntu/Debian)
sudo apt update
sudo apt install python3 python3-pip docker docker-compose

# Clone your repository
git clone https://github.com/yourusername/tokped-scraper.git
cd tokped-scraper

# Run the API
docker-compose up -d -f docker-compose.prod.yml

# Setup nginx reverse proxy (optional)
sudo apt install nginx
# Configure nginx for SSL termination
```

#### 3. Cloud LLM Setup (OpenRouter)

```bash
# Get API key from https://openrouter.ai/
# No local installation needed - use via API
```

---

## 🔧 Core Workflows Setup

### Workflow 1: Product Intelligence Pipeline

#### Step 1: Create New Workflow
1. Open n8n and create a new workflow
2. Name it "Tokopedia Product Intelligence"

#### Step 2: Add Schedule Trigger
```json
{
  "parameters": {
    "rule": {
      "interval": [
        {
          "field": "hours"
        }
      ]
    }
  },
  "name": "Schedule Trigger",
  "type": "n8n-nodes-base.scheduleTrigger"
}
```

#### Step 3: Add HTTP Request Node (Scraper API)
```json
{
  "parameters": {
    "method": "POST",
    "url": "https://your-api-server:8443/scrape",
    "sendHeaders": true,
    "headers": [
      {
        "name": "Content-Type",
        "value": "application/json"
      }
    ],
    "sendBody": true,
    "bodyContentType": "json",
    "body": {
      "query": "laptop gaming",
      "num_products": 10,
      "use_cache": true
    },
    "options": {
      "ignoreSslIssues": true,
      "timeout": 30000
    }
  },
  "name": "Scrape Products",
  "type": "n8n-nodes-base.httpRequest"
}
```

#### Step 4: Add Split In Batches Node
```json
{
  "parameters": {
    "batchSize": 1,
    "options": {
      "reset": false
    }
  },
  "name": "Process Products",
  "type": "n8n-nodes-base.splitInBatches"
}
```

#### Step 5: Add AI Analysis (OpenRouter)
```json
{
  "parameters": {
    "model": "anthropic/claude-3-haiku",
    "messages": [
      {
        "role": "user",
        "content": "Analyze this product: {{ $json.name }} priced at {{ $json.price }}. Is this a good deal? Provide a brief analysis."
      }
    ],
    "options": {}
  },
  "name": "AI Product Analysis",
  "type": "@n8n/n8n-nodes-langchain.chatOpenRouter"
}
```

#### Step 6: Add Database Storage
```json
{
  "parameters": {
    "operation": "insert",
    "table": "products",
    "columns": {
      "name": "={{ $json.name }}",
      "price": "={{ $json.price }}",
      "shop_name": "={{ $json.shop.name }}",
      "shop_rating": "={{ $json.shop.avgRating }}",
      "is_bestseller": "={{ $json.isBestSeller }}",
      "ai_analysis": "={{ $node[\"AI Product Analysis\"].json.output }}",
      "scraped_at": "={{ new Date().toISOString() }}"
    }
  },
  "name": "Store in Database",
  "type": "n8n-nodes-base.postgres"
}
```

### Workflow 2: AI-Powered Market Insights

#### Step 1: Database Query Node
```json
{
  "parameters": {
    "operation": "select",
    "query": "SELECT * FROM products WHERE scraped_at >= NOW() - INTERVAL '24 hours' ORDER BY shop_rating DESC LIMIT 10",
    "options": {}
  },
  "name": "Get Recent Products",
  "type": "n8n-nodes-base.postgres"
}
```

#### Step 2: AI Market Analysis
```json
{
  "parameters": {
    "model": "openai/gpt-4",
    "messages": [
      {
        "role": "system",
        "content": "You are a market analyst. Analyze these products and provide insights."
      },
      {
        "role": "user",
        "content": "Here are today's top products: {{ $json }}\n\nProvide market insights and recommendations."
      }
    ]
  },
  "name": "Market Analysis",
  "type": "@n8n/n8n-nodes-langchain.chatOpenAI"
}
```

#### Step 3: Generate Report
```json
{
  "parameters": {
    "fromEmail": "noreply@yourdomain.com",
    "toEmail": "analyst@yourcompany.com",
    "subject": "Daily Market Intelligence Report",
    "text": "Daily Market Report:\n\n{{ $node[\"Market Analysis\"].json.output }}\n\nGenerated at: {{ new Date().toISOString() }}"
  },
  "name": "Send Report",
  "type": "n8n-nodes-base.sendEmail"
}
```

---

## 🤖 AI/LLM Integration Options

### Option A: OpenRouter (Cloud LLM)

#### Setup:
1. Get API key from [openrouter.ai](https://openrouter.ai/)
2. Add credentials in n8n

#### Node Configuration:
```json
{
  "parameters": {
    "model": "anthropic/claude-3-sonnet",
    "messages": [
      {
        "role": "system",
        "content": "You are a product analyst specializing in e-commerce data."
      },
      {
        "role": "user",
        "content": "Analyze this product data and provide insights: {{ $json }}"
      }
    ],
    "options": {
      "maxTokens": 1000,
      "temperature": 0.7
    }
  },
  "name": "AI Analysis",
  "type": "@n8n/n8n-nodes-langchain.chatOpenRouter"
}
```

### Option B: Local LLM (Ollama)

#### Setup:
```bash
# On your VM/server
curl -fsSL https://ollama.ai/install.sh | sh
ollama pull llama2:13b
ollama serve
```

#### n8n Node Configuration:
```json
{
  "parameters": {
    "model": "llama2:13b",
    "messages": [
      {
        "role": "user",
        "content": "Analyze this e-commerce product: {{ $json.name }} - {{ $json.price }}\n\nProvide a detailed analysis of market positioning and pricing strategy."
      }
    ],
    "options": {
      "baseURL": "http://your-vm-ip:11434"
    }
  },
  "name": "Local AI Analysis",
  "type": "@n8n/n8n-nodes-langchain.chatOllama"
}
```

---

## 💾 Database Operations with n8n Tables

### Table Schema Design

#### Products Table:
```sql
CREATE TABLE products (
    id SERIAL PRIMARY KEY,
    name VARCHAR(500) NOT NULL,
    price VARCHAR(50),
    original_price VARCHAR(50),
    discount_percentage INTEGER,
    rating DECIMAL(3,2),
    review_count INTEGER,
    shop_name VARCHAR(255),
    shop_city VARCHAR(100),
    shop_rating DECIMAL(3,2),
    shop_total_reviews INTEGER,
    recommendation_score DECIMAL(5,2),
    is_bestseller BOOLEAN DEFAULT false,
    is_trending BOOLEAN DEFAULT false,
    is_top_rated BOOLEAN DEFAULT false,
    popularity_score DECIMAL(4,2),
    ai_analysis TEXT,
    scraped_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

#### Shops Table:
```sql
CREATE TABLE shops (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) UNIQUE NOT NULL,
    city VARCHAR(100),
    is_official BOOLEAN DEFAULT false,
    is_power_badge BOOLEAN DEFAULT false,
    avg_rating DECIMAL(3,2),
    total_reviews INTEGER,
    avg_discount_percent DECIMAL(5,2),
    product_count INTEGER,
    recommendation_score DECIMAL(5,2),
    specialties TEXT[],
    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### n8n Database Operations

#### Insert Product Data:
```json
{
  "parameters": {
    "operation": "insert",
    "table": "products",
    "columns": {
      "name": "={{ $json.name }}",
      "price": "={{ $json.price }}",
      "shop_name": "={{ $json.shop.name }}",
      "shop_rating": "={{ $json.shop.avgRating }}",
      "is_bestseller": "={{ $json.isBestSeller }}",
      "ai_analysis": "={{ $node[\"AI Analysis\"].json.output }}"
    }
  },
  "name": "Insert Product",
  "type": "n8n-nodes-base.postgres"
}
```

#### Query Analytics Data:
```json
{
  "parameters": {
    "operation": "select",
    "query": "SELECT shop_name, AVG(shop_rating) as avg_rating, COUNT(*) as product_count FROM products WHERE scraped_at >= NOW() - INTERVAL '7 days' GROUP BY shop_name ORDER BY avg_rating DESC LIMIT 10",
    "options": {}
  },
  "name": "Shop Analytics",
  "type": "n8n-nodes-base.postgres"
}
```

#### Update Shop Intelligence:
```json
{
  "parameters": {
    "operation": "upsert",
    "table": "shops",
    "columns": {
      "name": "={{ $json.name }}",
      "avg_rating": "={{ $json.avgRating }}",
      "recommendation_score": "={{ $json.recommendationScore }}"
    },
    "updateKey": "name"
  },
  "name": "Update Shop Data",
  "type": "n8n-nodes-base.postgres"
}
```

---

## 🚀 Production Deployment

### Environment Variables

#### n8n Cloud Configuration:
```bash
# Set in n8n Cloud dashboard
N8N_ENCRYPTION_KEY=your-encryption-key
N8N_DB_TYPE=postgresdb
N8N_DB_POSTGRESDB_HOST=your-db-host
N8N_DB_POSTGRESDB_USER=your-db-user
N8N_DB_POSTGRESDB_PASSWORD=your-db-password
```

#### Scraper API Production Config:
```bash
# On your VPS
export REDIS_URL=redis://localhost:6379/0
export SCRAPER_HOST=0.0.0.0
export SCRAPER_PORT=8443
export PYTHON_ENV=production
```

### Monitoring & Alerting

#### Health Check Workflow:
```
Schedule Trigger (every 5 min) →
HTTP Request (/health) →
IF (status != healthy) → Slack Alert
```

#### Performance Monitoring:
```json
{
  "parameters": {
    "operation": "select",
    "query": "SELECT COUNT(*) as total_products, AVG(rating) as avg_rating, MAX(scraped_at) as last_scrape FROM products WHERE scraped_at >= NOW() - INTERVAL '1 hour'",
    "options": {}
  },
  "name": "Performance Metrics",
  "type": "n8n-nodes-base.postgres"
}
```

### Scaling Considerations

#### Horizontal Scaling:
- Multiple scraper API instances behind load balancer
- Redis cluster for distributed caching
- Read replicas for database queries

#### Vertical Scaling:
- Increase VM resources (CPU, RAM)
- Optimize database queries
- Implement connection pooling

---

## 🔧 Advanced Features

### Webhook Integration

#### GitHub Webhook for CI/CD:
```json
{
  "parameters": {
    "httpMethod": "POST",
    "path": "github-webhook",
    "options": {}
  },
  "name": "GitHub Webhook",
  "type": "n8n-nodes-base.webhook"
}
```

### Error Handling & Retry Logic

#### Workflow-Level Error Handling:
```json
// Main workflow with error handling
HTTP Request → IF (success) → Process Data → Database Insert
            ↓ (error) → Wait (5s) → Retry HTTP Request (max 3 times)
```

#### Circuit Breaker Pattern:
```json
{
  "parameters": {
    "conditions": {
      "number": [
        {
          "value1": "{{ $node[\"HTTP Request\"].json.statusCode }}",
          "operation": "notEquals",
          "value2": 200
        }
      ]
    }
  },
  "name": "Circuit Breaker",
  "type": "n8n-nodes-base.if"
}
```

### Custom API Endpoints

#### Add Custom Analytics Endpoint:
```python
# In server.py
@app.route("/analytics/summary", methods=["GET"])
def get_analytics_summary():
    # Return cached analytics data
    return jsonify(cache.get("analytics_summary") or {"error": "No data available"})
```

---

## 📊 Monitoring & Analytics

### Dashboard Creation

#### Real-time Metrics:
```json
{
  "parameters": {
    "operation": "select",
    "query": "SELECT DATE(scraped_at) as date, COUNT(*) as products, AVG(rating) as avg_rating FROM products GROUP BY DATE(scraped_at) ORDER BY date DESC LIMIT 30",
    "options": {}
  },
  "name": "Daily Metrics",
  "type": "n8n-nodes-base.postgres"
}
```

#### Shop Performance Leaderboard:
```json
{
  "parameters": {
    "operation": "select",
    "query": "SELECT shop_name, AVG(shop_rating) as rating, COUNT(*) as products, AVG(recommendation_score) as score FROM products GROUP BY shop_name ORDER BY score DESC LIMIT 10",
    "options": {}
  },
  "name": "Shop Leaderboard",
  "type": "n8n-nodes-base.postgres"
}
```

---

## 🎯 Use Case Examples

### 1. **E-commerce Intelligence**
- Daily product price monitoring
- Competitor analysis
- Trend identification
- Automated reporting

### 2. **Market Research**
- Shop reputation tracking
- Product category analysis
- Customer sentiment analysis
- Market gap identification

### 3. **Business Intelligence**
- Sales performance dashboards
- Inventory optimization
- Pricing strategy insights
- Customer behavior analysis

---

## 🐛 Troubleshooting

### Common Issues

#### API Connection Issues:
```bash
# Test API directly
curl -k https://your-api-server:8443/health

# Check n8n logs
docker logs n8n-container

# Verify network connectivity
telnet your-api-server 8443
```

#### Database Connection Issues:
```bash
# Test database connection
docker exec -it postgres-container psql -U username -d database

# Check n8n database configuration
# Verify connection string in n8n credentials
```

#### AI/LLM Issues:
```bash
# Test OpenRouter API
curl -X POST https://openrouter.ai/api/v1/chat/completions \
  -H "Authorization: Bearer YOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"model": "anthropic/claude-3-haiku", "messages": [{"role": "user", "content": "Hello"}]}'

# Test local Ollama
curl http://localhost:11434/api/tags
```

---

## 📚 Resources & Next Steps

### Documentation Links:
- [n8n HTTP Request Node](https://docs.n8n.io/integrations/builtin/core-nodes/n8n-nodes-base.httprequest/)
- [n8n Database Operations](https://docs.n8n.io/integrations/builtin/app-nodes/n8n-nodes-base.postgres/)
- [OpenRouter API](https://openrouter.ai/docs)
- [Ollama Integration](https://docs.n8n.io/integrations/builtin/cluster-nodes/n8n-nodes-langchain.lmchatollama/)

### Advanced Topics:
- Custom n8n nodes development
- Webhook integrations
- Queue systems (Redis Queue)
- Advanced AI workflows
- Multi-tenant architectures

---

## 🎉 Ready for Production!

This setup provides a complete production-ready solution for:

- ✅ **Automated product intelligence gathering**
- ✅ **AI-powered market analysis**
- ✅ **Persistent data storage and analytics**
- ✅ **Scalable cloud deployment**
- ✅ **Comprehensive monitoring and alerting**

Your n8n workflows can now intelligently scrape, analyze, and store Tokopedia data with AI insights, all running in a production environment!