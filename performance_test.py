#!/usr/bin/env python3
"""
Simple performance test for Tokopedia API endpoints
"""

import requests
import time
import statistics
import urllib3

# Disable SSL warnings
urllib3.disable_warnings()

BASE_URL = "http://localhost:8449"
ENDPOINTS = [
    "/health",
    "/analytics/overview",
    "/products/search/history?limit=5",
    "/products/categories?limit=10",
    "/shops/top-rated?limit=5"
]

def test_endpoint(endpoint, iterations=5):
    """Test a single endpoint multiple times"""
    times = []
    errors = 0

    print(f"Testing {endpoint}...")

    for i in range(iterations):
        try:
            start_time = time.time()
            response = requests.get(f"{BASE_URL}{endpoint}", verify=False, timeout=10)
            end_time = time.time()

            if response.status_code == 200:
                times.append((end_time - start_time) * 1000)  # Convert to ms
                print(f"  Request {i+1}: {round((end_time - start_time) * 1000, 2)}ms")
            else:
                errors += 1
                print(f"  Request {i+1}: ERROR {response.status_code}")

        except Exception as e:
            errors += 1
            print(f"  Request {i+1}: EXCEPTION - {str(e)[:50]}")

    if times:
        avg_time = round(statistics.mean(times), 2)
        min_time = round(min(times), 2)
        max_time = round(max(times), 2)
        success_rate = round((len(times) / (len(times) + errors)) * 100, 1)

        print(f"  Results: Avg={avg_time}ms, Min={min_time}ms, Max={max_time}ms, Success={success_rate}%")
        print()

        return {
            'endpoint': endpoint,
            'avg_time': avg_time,
            'min_time': min_time,
            'max_time': max_time,
            'requests': len(times),
            'errors': errors,
            'success_rate': success_rate
        }
    else:
        print(f"  No successful requests")
        print()
        return {
            'endpoint': endpoint,
            'avg_time': 0,
            'min_time': 0,
            'max_time': 0,
            'requests': 0,
            'errors': errors,
            'success_rate': 0
        }

def run_performance_test():
    """Run performance tests on all endpoints"""
    print("🚀 Starting Performance Test for Tokopedia API")
    print("=" * 60)
    print()

    results = []

    # Test each endpoint
    for endpoint in ENDPOINTS:
        result = test_endpoint(endpoint, iterations=3)
        results.append(result)

    # Summary
    print("📊 Performance Summary:")
    print("-" * 80)

    total_requests = sum(r['requests'] for r in results)
    total_errors = sum(r['errors'] for r in results)
    avg_times = [r['avg_time'] for r in results if r['requests'] > 0]

    print(f"Total Endpoints Tested: {len(results)}")
    print(f"Total Requests Made: {total_requests}")
    print(f"Total Errors: {total_errors}")

    if total_requests > 0:
        overall_success = round((total_requests / (total_requests + total_errors)) * 100, 1)
        print(f"Overall Success Rate: {overall_success}%")

    if avg_times:
        avg_response_time = round(statistics.mean(avg_times), 2)
        print(f"Average Response Time: {avg_response_time}ms")

    print()
    print("✅ Performance test completed!")

if __name__ == "__main__":
    run_performance_test()