#!/usr/bin/env python3
"""
Quick Performance Test for Optimized Endpoints
Tests the specific endpoints mentioned in the Italian review request
"""

import requests
import time
import json

class QuickPerformanceTester:
    def __init__(self, base_url="https://faster-crm.preview.emergentagent.com"):
        self.base_url = base_url
        self.token = None
        self.results = {}

    def login(self):
        """Login with admin credentials"""
        print("🔐 Logging in...")
        url = f"{self.base_url}/api/login"
        data = {"email": "admin@grabovoi.com", "password": "admin123"}
        
        try:
            response = requests.post(url, json=data, timeout=10)
            if response.status_code == 200:
                result = response.json()
                self.token = result.get('access_token')
                print(f"✅ Login successful")
                return True
            else:
                print(f"❌ Login failed: {response.status_code}")
                return False
        except Exception as e:
            print(f"❌ Login error: {str(e)}")
            return False

    def test_endpoint(self, name, endpoint):
        """Test a single endpoint and measure response time"""
        print(f"\n🔍 Testing {name}...")
        url = f"{self.base_url}/{endpoint}"
        headers = {'Authorization': f'Bearer {self.token}'} if self.token else {}
        
        try:
            start_time = time.time()
            response = requests.get(url, headers=headers, timeout=15)
            end_time = time.time()
            
            response_time = (end_time - start_time) * 1000  # Convert to milliseconds
            
            if response.status_code == 200:
                print(f"✅ Status: {response.status_code}")
                print(f"⏱️  Response Time: {response_time:.2f}ms")
                
                # Performance evaluation
                if response_time < 100:
                    performance = "🎉 EXCELLENT"
                elif response_time < 300:
                    performance = "✅ GOOD"
                elif response_time < 500:
                    performance = "⚠️  ACCEPTABLE"
                else:
                    performance = "❌ SLOW"
                
                print(f"📊 Performance: {performance}")
                
                # Try to get response info
                try:
                    data = response.json()
                    if isinstance(data, dict):
                        if 'data' in data and 'pagination' in data:
                            items_count = len(data.get('data', []))
                            total_count = data.get('pagination', {}).get('total_count', 0)
                            print(f"📦 Data: {items_count} items returned, {total_count} total")
                        elif isinstance(data, dict) and len(data) > 0:
                            print(f"📦 Data: Response with {len(data)} fields")
                    elif isinstance(data, list):
                        print(f"📦 Data: {len(data)} items returned")
                except:
                    print(f"📦 Data: Response received")
                
                self.results[name] = {
                    'response_time': response_time,
                    'status': 'success',
                    'performance': performance
                }
                return True
            else:
                print(f"❌ Status: {response.status_code}")
                print(f"⏱️  Response Time: {response_time:.2f}ms")
                self.results[name] = {
                    'response_time': response_time,
                    'status': 'failed',
                    'error': response.status_code
                }
                return False
                
        except Exception as e:
            print(f"❌ Error: {str(e)}")
            self.results[name] = {
                'status': 'error',
                'error': str(e)
            }
            return False

    def run_performance_tests(self):
        """Run performance tests for the specific endpoints mentioned in the review"""
        print("🚀 Quick Performance Test for Optimized Endpoints")
        print("🎯 Focus: Response time measurement after optimizations")
        print("👤 Credentials: admin@grabovoi.com / admin123")
        print("=" * 70)
        
        # Login first
        if not self.login():
            print("❌ Cannot proceed without authentication")
            return
        
        # Test the specific endpoints mentioned in the review
        endpoints_to_test = [
            ("CRM Products", "api/crm-products"),
            ("Courses", "api/courses"),
            ("Auth Me", "api/auth/me"),
            ("Dashboard Stats", "api/dashboard/stats")
        ]
        
        successful_tests = 0
        total_tests = len(endpoints_to_test)
        
        for name, endpoint in endpoints_to_test:
            if self.test_endpoint(name, endpoint):
                successful_tests += 1
            time.sleep(1)  # Small delay between tests
        
        # Print summary
        print("\n" + "=" * 70)
        print("📊 PERFORMANCE TEST RESULTS SUMMARY")
        print("=" * 70)
        
        if self.results:
            print("⏱️  Response Time Results:")
            total_time = 0
            successful_count = 0
            
            for name, result in self.results.items():
                if result['status'] == 'success':
                    response_time = result['response_time']
                    performance = result['performance']
                    print(f"   {name}: {response_time:.2f}ms - {performance}")
                    total_time += response_time
                    successful_count += 1
                else:
                    print(f"   {name}: FAILED - {result.get('error', 'Unknown error')}")
            
            if successful_count > 0:
                avg_time = total_time / successful_count
                print(f"\n🎯 Overall Average Response Time: {avg_time:.2f}ms")
                
                if avg_time < 100:
                    print("🎉 EXCELLENT overall performance - Optimizations working perfectly!")
                elif avg_time < 300:
                    print("✅ GOOD overall performance - Optimizations effective!")
                elif avg_time < 500:
                    print("⚠️  ACCEPTABLE overall performance - Some room for improvement")
                else:
                    print("❌ SLOW overall performance - Further optimization needed")
        
        print(f"\n✅ Tests Passed: {successful_tests}")
        print(f"❌ Tests Failed: {total_tests - successful_tests}")
        print(f"📊 Total Tests: {total_tests}")
        print(f"📈 Success Rate: {(successful_tests/total_tests)*100:.1f}%")
        
        if successful_tests == total_tests:
            print("\n🎉 ALL PERFORMANCE TESTS PASSED!")
        elif successful_tests / total_tests >= 0.75:
            print("\n✅ PERFORMANCE OPTIMIZATIONS MOSTLY WORKING")
        else:
            print("\n⚠️ PERFORMANCE OPTIMIZATIONS NEED ATTENTION")

if __name__ == "__main__":
    tester = QuickPerformanceTester()
    tester.run_performance_tests()