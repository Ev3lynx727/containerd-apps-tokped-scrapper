from locust import HttpUser, task, between
import json

class TokopediaAPIScraperUser(HttpUser):
    wait_time = between(1, 3)

    def on_start(self):
        """Setup before starting tests"""
        # Scrape some data to populate cache
        self.client.post("/scrape",
                        json={"query": "laptop gaming", "num_products": 3},
                        headers={"Content-Type": "application/json"},
                        verify=False)

    @task(3)
    def test_health_check(self):
        """Test health endpoint - high frequency"""
        with self.client.get("/health", verify=False, catch_response=True) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"Health check failed: {response.status_code}")

    @task(2)
    def test_api_info(self):
        """Test API information endpoint"""
        self.client.get("/", verify=False)

    @task(2)
    def test_analytics_overview(self):
        """Test analytics overview endpoint"""
        with self.client.get("/analytics/overview", verify=False, catch_response=True) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"Analytics overview failed: {response.status_code}")

    @task(2)
    def test_search_history(self):
        """Test search history endpoint"""
        self.client.get("/products/search/history?limit=5", verify=False)

    @task(2)
    def test_categories(self):
        """Test product categories endpoint"""
        self.client.get("/products/categories?limit=10", verify=False)

    @task(1)
    def test_trending_products(self):
        """Test trending products endpoint"""
        self.client.get("/products/trending", verify=False)

    @task(1)
    def test_top_rated_shops(self):
        """Test top rated shops endpoint"""
        self.client.get("/shops/top-rated?limit=5", verify=False)

    @task(1)
    def test_shop_stats(self):
        """Test shop statistics endpoint"""
        self.client.get("/shops/stats", verify=False)

    @task(1)
    def test_analytics_performance(self):
        """Test analytics performance endpoint"""
        self.client.get("/analytics/performance", verify=False)

    @task(1)
    def test_recent_logs(self):
        """Test recent logs endpoint"""
        self.client.get("/logs/recent?limit=10", verify=False)

    @task(1)
    def test_redis_status(self):
        """Test Redis status endpoint"""
        self.client.get("/redis/status", verify=False)

    @task(1)
    def test_scrape_products(self):
        """Test product scraping - low frequency to avoid overloading"""
        self.client.post("/scrape",
                        json={"query": "test query", "num_products": 2},
                        headers={"Content-Type": "application/json"},
                        verify=False)