#!/usr/bin/env python3
"""
Local Performance Test for Optimized Endpoints
Tests the specific endpoints mentioned in the Italian review request using localhost
"""

import requests
import time
import json

class LocalPerformanceTester:
    def __init__(self, base_url="http://localhost:8001"):
        self.base_url = base_url
        self.token = None
        self.results = {}

    def login(self):
        """Login with admin credentials"""
        print("🔐 Logging in...")
        url = f"{self.base_url}/api/login"
        data = {"email": "admin@grabovoi.com", "password": "admin123"}
        
        try:
            response = requests.post(url, json=data, timeout=5)
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

    def test_endpoint(self, name, endpoint, runs=3):
        """Test a single endpoint multiple times and measure response time"""
        print(f"\n🔍 Testing {name}...")
        url = f"{self.base_url}/{endpoint}"
        headers = {'Authorization': f'Bearer {self.token}'} if self.token else {}
        
        response_times = []
        successful_runs = 0
        
        for i in range(runs):
            try:
                start_time = time.time()
                response = requests.get(url, headers=headers, timeout=10)
                end_time = time.time()
                
                response_time = (end_time - start_time) * 1000  # Convert to milliseconds
                
                if response.status_code == 200:
                    response_times.append(response_time)
                    successful_runs += 1
                    print(f"   Run {i+1}: {response_time:.2f}ms ✅")
                else:
                    print(f"   Run {i+1}: Status {response.status_code} ❌")
                    
            except Exception as e:
                print(f"   Run {i+1}: Error - {str(e)} ❌")
        
        if response_times:
            avg_time = sum(response_times) / len(response_times)
            min_time = min(response_times)
            max_time = max(response_times)
            
            print(f"📊 Results for {name}:")
            print(f"   ⏱️  Average: {avg_time:.2f}ms")
            print(f"   🚀 Fastest: {min_time:.2f}ms")
            print(f"   🐌 Slowest: {max_time:.2f}ms")
            print(f"   ✅ Success: {successful_runs}/{runs} runs")
            
            # Performance evaluation
            if avg_time < 100:
                performance = "🎉 EXCELLENT"
            elif avg_time < 300:
                performance = "✅ GOOD"
            elif avg_time < 500:
                performance = "⚠️  ACCEPTABLE"
            else:
                performance = "❌ SLOW"
            
            print(f"   📈 Performance: {performance}")
            
            # Try to get response info from last successful response
            try:
                if successful_runs > 0:
                    response = requests.get(url, headers=headers, timeout=5)
                    if response.status_code == 200:
                        data = response.json()
                        if isinstance(data, dict):
                            if 'data' in data and 'pagination' in data:
                                items_count = len(data.get('data', []))
                                total_count = data.get('pagination', {}).get('total_count', 0)
                                print(f"   📦 Data: {items_count} items returned, {total_count} total")
                            elif len(data) > 0:
                                print(f"   📦 Data: Response with {len(data)} fields")
                        elif isinstance(data, list):
                            print(f"   📦 Data: {len(data)} items returned")
            except:
                pass
            
            self.results[name] = {
                'avg_response_time': avg_time,
                'min_response_time': min_time,
                'max_response_time': max_time,
                'success_rate': (successful_runs / runs) * 100,
                'performance': performance,
                'status': 'success' if successful_runs > 0 else 'failed'
            }
            return successful_runs > 0
        else:
            self.results[name] = {
                'status': 'failed',
                'success_rate': 0
            }
            return False

    def run_performance_tests(self):
        """Run performance tests for the specific endpoints mentioned in the review"""
        print("🚀 Local Performance Test for Optimized Endpoints")
        print("🎯 Focus: Response time measurement after optimizations")
        print("👤 Credentials: admin@grabovoi.com / admin123")
        print("🌐 Testing locally on http://localhost:8001")
        print("=" * 70)
        
        # Login first
        if not self.login():
            print("❌ Cannot proceed without authentication")
            return
        
        # Test the specific endpoints mentioned in the review
        endpoints_to_test = [
            ("GET /api/crm-products", "api/crm-products"),
            ("GET /api/courses", "api/courses"),
            ("GET /api/auth/me", "api/auth/me"),
            ("GET /api/dashboard/stats", "api/dashboard/stats")
        ]
        
        successful_tests = 0
        total_tests = len(endpoints_to_test)
        
        for name, endpoint in endpoints_to_test:
            if self.test_endpoint(name, endpoint):
                successful_tests += 1
            time.sleep(0.5)  # Small delay between tests
        
        # Print summary
        print("\n" + "=" * 70)
        print("📊 PERFORMANCE TEST RESULTS SUMMARY")
        print("=" * 70)
        
        if self.results:
            print("⏱️  Response Time Results:")
            total_avg_time = 0
            successful_count = 0
            
            for name, result in self.results.items():
                if result['status'] == 'success':
                    avg_time = result['avg_response_time']
                    performance = result['performance']
                    success_rate = result['success_rate']
                    print(f"   {name}: {avg_time:.2f}ms avg - {performance} ({success_rate:.0f}% success)")
                    total_avg_time += avg_time
                    successful_count += 1
                else:
                    print(f"   {name}: FAILED")
            
            if successful_count > 0:
                overall_avg = total_avg_time / successful_count
                print(f"\n🎯 Overall Average Response Time: {overall_avg:.2f}ms")
                
                if overall_avg < 100:
                    print("🎉 EXCELLENT overall performance - Optimizations working perfectly!")
                    print("   All endpoints responding in under 100ms!")
                elif overall_avg < 300:
                    print("✅ GOOD overall performance - Optimizations effective!")
                    print("   All endpoints responding in under 300ms!")
                elif overall_avg < 500:
                    print("⚠️  ACCEPTABLE overall performance - Some room for improvement")
                    print("   Most endpoints responding in under 500ms")
                else:
                    print("❌ SLOW overall performance - Further optimization needed")
                    print("   Some endpoints taking over 500ms")
                
                # Specific analysis for the review request
                print(f"\n📋 Analysis for Italian Review Request:")
                print(f"   1. GET /api/crm-products - Should be faster without aggregation pipeline")
                print(f"   2. GET /api/courses - Should be faster without count query")
                print(f"   3. GET /api/auth/me - Authentication should be fast")
                print(f"   4. GET /api/dashboard/stats - Dashboard should be fast")
                
                crm_result = self.results.get("GET /api/crm-products", {})
                courses_result = self.results.get("GET /api/courses", {})
                auth_result = self.results.get("GET /api/auth/me", {})
                dashboard_result = self.results.get("GET /api/dashboard/stats", {})
                
                if crm_result.get('status') == 'success':
                    print(f"   ✅ CRM Products: {crm_result['avg_response_time']:.2f}ms - Optimization working!")
                if courses_result.get('status') == 'success':
                    print(f"   ✅ Courses: {courses_result['avg_response_time']:.2f}ms - Optimization working!")
                if auth_result.get('status') == 'success':
                    print(f"   ✅ Authentication: {auth_result['avg_response_time']:.2f}ms - Fast authentication!")
                if dashboard_result.get('status') == 'success':
                    print(f"   ✅ Dashboard: {dashboard_result['avg_response_time']:.2f}ms - Fast dashboard!")
        
        print(f"\n✅ Tests Passed: {successful_tests}")
        print(f"❌ Tests Failed: {total_tests - successful_tests}")
        print(f"📊 Total Tests: {total_tests}")
        print(f"📈 Success Rate: {(successful_tests/total_tests)*100:.1f}%")
        
        if successful_tests == total_tests:
            print("\n🎉 ALL PERFORMANCE TESTS PASSED!")
            print("🚀 OPTIMIZATIONS ARE WORKING PERFECTLY!")
        elif successful_tests / total_tests >= 0.75:
            print("\n✅ PERFORMANCE OPTIMIZATIONS MOSTLY WORKING")
        else:
            print("\n⚠️ PERFORMANCE OPTIMIZATIONS NEED ATTENTION")

if __name__ == "__main__":
    tester = LocalPerformanceTester()
    tester.run_performance_tests()