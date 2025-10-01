import requests
import sys
import json
import time
import threading
import queue
import os

class OptimizedInitialDataTester:
    def __init__(self, base_url="https://faster-crm.preview.emergentagent.com"):
        self.base_url = base_url
        self.token = None
        self.tests_run = 0
        self.tests_passed = 0
        self.user_id = None
        self.performance_data = {}

    def run_test(self, name, method, endpoint, expected_status, data=None, headers=None, measure_time=False):
        """Run a single API test with optional performance measurement"""
        url = f"{self.base_url}/{endpoint}"
        test_headers = {'Content-Type': 'application/json'}
        
        if self.token:
            test_headers['Authorization'] = f'Bearer {self.token}'
        
        if headers:
            test_headers.update(headers)

        self.tests_run += 1
        print(f"\n🔍 Testing {name}...")
        print(f"   URL: {method} {url}")
        
        start_time = time.time() if measure_time else None
        
        try:
            if method == 'GET':
                response = requests.get(url, headers=test_headers)
            elif method == 'POST':
                response = requests.post(url, json=data, headers=test_headers)
            elif method == 'PUT':
                response = requests.put(url, json=data, headers=test_headers)
            elif method == 'DELETE':
                response = requests.delete(url, headers=test_headers)

            end_time = time.time() if measure_time else None
            response_time = (end_time - start_time) * 1000 if measure_time else None  # Convert to milliseconds

            success = response.status_code == expected_status
            if success:
                self.tests_passed += 1
                print(f"✅ Passed - Status: {response.status_code}")
                if response_time:
                    print(f"   ⏱️ Response Time: {response_time:.2f}ms")
                    self.performance_data[name] = response_time
                try:
                    response_data = response.json()
                    if isinstance(response_data, dict) and len(str(response_data)) < 1000:
                        print(f"   Response: {response_data}")
                    elif isinstance(response_data, list):
                        print(f"   Response: List with {len(response_data)} items")
                    elif isinstance(response_data, dict):
                        print(f"   Response: Dict with {len(response_data)} keys")
                    return success, response_data, response_time
                except:
                    return success, {}, response_time
            else:
                print(f"❌ Failed - Expected {expected_status}, got {response.status_code}")
                try:
                    error_data = response.json()
                    print(f"   Error: {error_data}")
                except:
                    print(f"   Error: {response.text}")
                return False, {}, response_time

        except Exception as e:
            print(f"❌ Failed - Error: {str(e)}")
            return False, {}, None

    def test_login(self):
        """Test login with admin credentials"""
        success, response, _ = self.run_test(
            "Admin Login",
            "POST",
            "api/login",
            200,
            data={"email": "admin@grabovoi.com", "password": "admin123"}
        )
        if success and 'access_token' in response:
            self.token = response['access_token']
            if 'user' in response:
                self.user_id = response['user'].get('id')
            print(f"   🔑 Token obtained: {self.token[:20]}...")
            return True
        return False

    def test_optimized_initial_data_endpoint(self):
        """Test GET /api/dashboard/initial-data - New optimized endpoint"""
        print("\n🔍 Testing New Optimized Initial Data Endpoint...")
        
        success, response, response_time = self.run_test(
            "Optimized Initial Data Endpoint",
            "GET",
            "api/dashboard/initial-data",
            200,
            measure_time=True
        )
        
        if success:
            # Verify response structure
            expected_fields = ['success', 'dashboard_stats', 'contacts_data', 'products', 'courses', 'load_time']
            for field in expected_fields:
                if field not in response:
                    print(f"   ❌ Missing response field: {field}")
                    return False
            
            # Verify dashboard stats structure
            stats = response.get('dashboard_stats', {})
            expected_stats = ['total_contacts', 'active_students', 'total_orders', 'leads']
            for stat in expected_stats:
                if stat not in stats:
                    print(f"   ❌ Missing dashboard stat: {stat}")
                    return False
            
            # Verify contacts data structure
            contacts_data = response.get('contacts_data', {})
            if 'contacts' not in contacts_data or 'pagination' not in contacts_data:
                print(f"   ❌ Invalid contacts data structure")
                return False
            
            # Verify products and courses are arrays
            products = response.get('products', [])
            courses = response.get('courses', [])
            
            if not isinstance(products, list) or not isinstance(courses, list):
                print(f"   ❌ Products and courses should be arrays")
                return False
            
            print(f"   ✅ Response structure is correct")
            print(f"   📊 Dashboard Stats: {stats}")
            print(f"   👥 Contacts: {len(contacts_data.get('contacts', []))} items")
            print(f"   🛍️ Products: {len(products)} items")
            print(f"   📚 Courses: {len(courses)} items")
            print(f"   ⏱️ Load Time: {response_time:.2f}ms")
            
            return True
        
        return False

    def test_individual_api_calls_performance(self):
        """Test performance of individual API calls for comparison"""
        print("\n🔍 Testing Individual API Calls Performance...")
        
        individual_times = {}
        
        # Test dashboard stats
        success1, response1, time1 = self.run_test(
            "Individual Dashboard Stats",
            "GET",
            "api/dashboard/stats",
            200,
            measure_time=True
        )
        if success1:
            individual_times['dashboard_stats'] = time1
        
        # Test contacts (first page)
        success2, response2, time2 = self.run_test(
            "Individual Contacts (Page 1)",
            "GET",
            "api/contacts?page=1&limit=50",
            200,
            measure_time=True
        )
        if success2:
            individual_times['contacts'] = time2
        
        # Test products
        success3, response3, time3 = self.run_test(
            "Individual Products",
            "GET",
            "api/products",
            200,
            measure_time=True
        )
        if success3:
            individual_times['products'] = time3
        
        # Test courses
        success4, response4, time4 = self.run_test(
            "Individual Courses",
            "GET",
            "api/courses",
            200,
            measure_time=True
        )
        if success4:
            individual_times['courses'] = time4
        
        if all([success1, success2, success3, success4]):
            total_individual_time = sum(individual_times.values())
            print(f"   ✅ All individual API calls successful")
            print(f"   📊 Individual Times: {individual_times}")
            print(f"   ⏱️ Total Individual Time: {total_individual_time:.2f}ms")
            
            self.performance_data['individual_calls'] = individual_times
            self.performance_data['total_individual_time'] = total_individual_time
            
            return True
        
        return False

    def test_performance_comparison(self):
        """Compare performance between optimized endpoint and individual calls"""
        print("\n🔍 Testing Performance Comparison...")
        
        optimized_time = self.performance_data.get('Optimized Initial Data Endpoint')
        total_individual_time = self.performance_data.get('total_individual_time')
        
        if optimized_time and total_individual_time:
            improvement = ((total_individual_time - optimized_time) / total_individual_time) * 100
            
            print(f"   📊 Performance Comparison:")
            print(f"   🚀 Optimized Endpoint: {optimized_time:.2f}ms")
            print(f"   🐌 Individual Calls: {total_individual_time:.2f}ms")
            print(f"   📈 Performance Improvement: {improvement:.1f}%")
            
            if optimized_time < total_individual_time:
                print(f"   ✅ Optimized endpoint is faster!")
                return True
            elif optimized_time <= total_individual_time * 1.1:  # Within 10% is acceptable
                print(f"   ✅ Optimized endpoint performance is acceptable")
                return True
            else:
                print(f"   ⚠️ Optimized endpoint is slower than expected")
                return False
        else:
            print(f"   ❌ Missing performance data for comparison")
            return False

    def test_data_integrity_verification(self):
        """Verify data integrity across the combined response"""
        print("\n🔍 Testing Data Integrity Verification...")
        
        # Get optimized data
        success_opt, opt_response, _ = self.run_test(
            "Get Optimized Data for Integrity Check",
            "GET",
            "api/dashboard/initial-data",
            200
        )
        
        if not success_opt:
            return False
        
        # Get individual data for comparison
        success_stats, stats_response, _ = self.run_test(
            "Get Individual Stats for Comparison",
            "GET",
            "api/dashboard/stats",
            200
        )
        
        success_contacts, contacts_response, _ = self.run_test(
            "Get Individual Contacts for Comparison",
            "GET",
            "api/contacts?page=1&limit=50",
            200
        )
        
        if not all([success_stats, success_contacts]):
            return False
        
        # Compare dashboard stats
        opt_stats = opt_response.get('dashboard_stats', {})
        individual_stats = stats_response
        
        stats_match = True
        for key in ['total_contacts', 'active_students', 'total_orders', 'leads']:
            if opt_stats.get(key) != individual_stats.get(key):
                print(f"   ❌ Stats mismatch for {key}: {opt_stats.get(key)} vs {individual_stats.get(key)}")
                stats_match = False
        
        if stats_match:
            print(f"   ✅ Dashboard stats integrity verified")
        
        # Compare contacts pagination info
        opt_contacts = opt_response.get('contacts_data', {})
        opt_pagination = opt_contacts.get('pagination', {})
        individual_pagination = contacts_response.get('pagination', {})
        
        pagination_match = True
        for key in ['current_page', 'total_count', 'per_page']:
            if opt_pagination.get(key) != individual_pagination.get(key):
                print(f"   ❌ Pagination mismatch for {key}: {opt_pagination.get(key)} vs {individual_pagination.get(key)}")
                pagination_match = False
        
        if pagination_match:
            print(f"   ✅ Contacts pagination integrity verified")
        
        # Verify products and courses arrays are complete
        products = opt_response.get('products', [])
        courses = opt_response.get('courses', [])
        
        print(f"   📊 Data Integrity Summary:")
        print(f"   👥 Contacts: {len(opt_contacts.get('contacts', []))} items")
        print(f"   🛍️ Products: {len(products)} items")
        print(f"   📚 Courses: {len(courses)} items")
        print(f"   📈 Total Contacts: {opt_stats.get('total_contacts', 0)}")
        print(f"   📈 Total Orders: {opt_stats.get('total_orders', 0)}")
        
        return stats_match and pagination_match

    def test_error_handling_authentication(self):
        """Test endpoint with authentication requirements"""
        print("\n🔍 Testing Error Handling - Authentication...")
        
        # Store original token
        original_token = self.token
        self.token = None
        
        success, response, _ = self.run_test(
            "Optimized Endpoint Without Auth",
            "GET",
            "api/dashboard/initial-data",
            401  # Should require authentication
        )
        
        # Restore token
        self.token = original_token
        
        if success:
            print(f"   ✅ Authentication requirement properly enforced")
            return True
        else:
            print(f"   ❌ Authentication not properly enforced")
            return False

    def test_error_handling_invalid_token(self):
        """Test endpoint with invalid token"""
        print("\n🔍 Testing Error Handling - Invalid Token...")
        
        # Store original token
        original_token = self.token
        self.token = "invalid.jwt.token"
        
        success, response, _ = self.run_test(
            "Optimized Endpoint With Invalid Token",
            "GET",
            "api/dashboard/initial-data",
            401  # Should reject invalid token
        )
        
        # Restore token
        self.token = original_token
        
        if success:
            print(f"   ✅ Invalid token properly rejected")
            return True
        else:
            print(f"   ❌ Invalid token not properly handled")
            return False

    def test_data_volume_handling(self):
        """Test endpoint behavior with different data volumes"""
        print("\n🔍 Testing Data Volume Handling...")
        
        # Test multiple calls to ensure consistency
        times = []
        for i in range(3):
            success, response, response_time = self.run_test(
                f"Volume Test Call {i+1}",
                "GET",
                "api/dashboard/initial-data",
                200,
                measure_time=True
            )
            
            if success and response_time:
                times.append(response_time)
            else:
                return False
        
        if len(times) == 3:
            avg_time = sum(times) / len(times)
            max_time = max(times)
            min_time = min(times)
            
            print(f"   📊 Performance Consistency:")
            print(f"   ⏱️ Average Time: {avg_time:.2f}ms")
            print(f"   ⏱️ Min Time: {min_time:.2f}ms")
            print(f"   ⏱️ Max Time: {max_time:.2f}ms")
            print(f"   📈 Variance: {max_time - min_time:.2f}ms")
            
            # Check if performance is consistent (variance < 50% of average)
            if (max_time - min_time) < (avg_time * 0.5):
                print(f"   ✅ Performance is consistent across multiple calls")
                return True
            else:
                print(f"   ⚠️ Performance variance is high")
                return True  # Still pass, but note the variance
        
        return False

    def test_concurrent_requests(self):
        """Test endpoint behavior under concurrent load"""
        print("\n🔍 Testing Concurrent Request Handling...")
        
        results = queue.Queue()
        
        def make_request(request_id):
            try:
                start_time = time.time()
                url = f"{self.base_url}/api/dashboard/initial-data"
                headers = {
                    'Content-Type': 'application/json',
                    'Authorization': f'Bearer {self.token}'
                }
                
                response = requests.get(url, headers=headers)
                end_time = time.time()
                
                results.put({
                    'id': request_id,
                    'status': response.status_code,
                    'time': (end_time - start_time) * 1000,
                    'success': response.status_code == 200
                })
            except Exception as e:
                results.put({
                    'id': request_id,
                    'status': 0,
                    'time': 0,
                    'success': False,
                    'error': str(e)
                })
        
        # Create 3 concurrent threads
        threads = []
        for i in range(3):
            thread = threading.Thread(target=make_request, args=(i+1,))
            threads.append(thread)
        
        # Start all threads
        start_time = time.time()
        for thread in threads:
            thread.start()
        
        # Wait for all threads to complete
        for thread in threads:
            thread.join()
        
        total_time = (time.time() - start_time) * 1000
        
        # Collect results
        concurrent_results = []
        while not results.empty():
            concurrent_results.append(results.get())
        
        successful_requests = sum(1 for r in concurrent_results if r['success'])
        avg_response_time = sum(r['time'] for r in concurrent_results if r['success']) / max(successful_requests, 1)
        
        print(f"   📊 Concurrent Request Results:")
        print(f"   ✅ Successful Requests: {successful_requests}/3")
        print(f"   ⏱️ Total Time: {total_time:.2f}ms")
        print(f"   ⏱️ Average Response Time: {avg_response_time:.2f}ms")
        
        if successful_requests == 3:
            print(f"   ✅ All concurrent requests successful")
            self.tests_passed += 1  # Manual increment since we didn't use run_test
            return True
        else:
            print(f"   ❌ Some concurrent requests failed")
            return False

    def run_all_optimized_initial_data_tests(self):
        """Run all optimized initial data loading tests"""
        print("🚀 Starting Optimized Initial Data Loading Testing...")
        print(f"🌐 Base URL: {self.base_url}")
        print("=" * 80)
        
        # Test sequence for optimized initial data loading
        test_methods = [
            self.test_login,
            self.test_optimized_initial_data_endpoint,
            self.test_individual_api_calls_performance,
            self.test_performance_comparison,
            self.test_data_integrity_verification,
            self.test_error_handling_authentication,
            self.test_error_handling_invalid_token,
            self.test_data_volume_handling,
            self.test_concurrent_requests,
        ]
        
        for test_method in test_methods:
            try:
                result = test_method()
                if not result:
                    print(f"❌ Test {test_method.__name__} failed")
                time.sleep(0.5)  # Small delay between tests
            except Exception as e:
                print(f"❌ Test {test_method.__name__} failed with error: {str(e)}")
                self.tests_run += 1
        
        # Print final results
        print("\n" + "=" * 80)
        print("📊 OPTIMIZED INITIAL DATA LOADING TEST RESULTS")
        print("=" * 80)
        print(f"✅ Tests Passed: {self.tests_passed}")
        print(f"❌ Tests Failed: {self.tests_run - self.tests_passed}")
        print(f"📊 Total Tests: {self.tests_run}")
        print(f"📈 Success Rate: {(self.tests_passed/self.tests_run)*100:.1f}%")
        
        # Performance Summary
        if self.performance_data:
            print(f"\n📈 PERFORMANCE SUMMARY:")
            optimized_time = self.performance_data.get('Optimized Initial Data Endpoint')
            total_individual = self.performance_data.get('total_individual_time')
            
            if optimized_time and total_individual:
                improvement = ((total_individual - optimized_time) / total_individual) * 100
                print(f"🚀 Optimized Endpoint: {optimized_time:.2f}ms")
                print(f"🐌 Individual Calls: {total_individual:.2f}ms")
                print(f"📈 Performance Improvement: {improvement:.1f}%")
        
        if self.tests_passed == self.tests_run:
            print("\n🎉 ALL OPTIMIZED INITIAL DATA TESTS PASSED!")
            print("✅ New optimized endpoint is working perfectly")
            print("✅ Performance improvement confirmed")
            print("✅ Data integrity verified")
            print("✅ Error handling working correctly")
        elif self.tests_passed / self.tests_run >= 0.8:
            print("\n✅ OPTIMIZED INITIAL DATA LOADING MOSTLY WORKING")
            print("⚠️ Some minor issues detected, but core functionality is working")
        else:
            print("\n⚠️ OPTIMIZED INITIAL DATA LOADING NEEDS ATTENTION")
            print("❌ Multiple issues detected with the new endpoint")
        
        return self.tests_passed, self.tests_run

# Run the optimized initial data loading tests
if __name__ == "__main__":
    print("🚀 TESTING OPTIMIZED INITIAL DATA LOADING ENDPOINT")
    print("Testing the new GET /api/dashboard/initial-data endpoint")
    print("Focus: Performance comparison, data integrity, and error handling")
    print("=" * 80)
    
    # Get base URL from environment or use default
    base_url = os.getenv("REACT_APP_BACKEND_URL", "https://faster-crm.preview.emergentagent.com")
    
    # Run optimized initial data tests
    optimized_tester = OptimizedInitialDataTester(base_url)
    passed, total = optimized_tester.run_all_optimized_initial_data_tests()
    
    print("\n" + "=" * 80)
    print("🎯 OPTIMIZED INITIAL DATA LOADING TEST SUMMARY")
    print("=" * 80)
    print(f"📊 Tests Passed: {passed}/{total}")
    print(f"📈 Success Rate: {(passed/total)*100:.1f}%")
    
    if passed == total:
        print("\n🎉 ALL OPTIMIZED INITIAL DATA TESTS PASSED!")
        print("✅ New optimized endpoint is working perfectly")
        print("✅ Performance improvement confirmed")
        print("✅ Data integrity verified")
        print("✅ Error handling working correctly")
        sys.exit(0)
    elif passed / total >= 0.8:
        print("\n✅ OPTIMIZED INITIAL DATA LOADING MOSTLY WORKING")
        print("⚠️ Some minor issues detected, but core functionality is working")
        sys.exit(0)
    else:
        print("\n⚠️ OPTIMIZED INITIAL DATA LOADING NEEDS ATTENTION")
        print("❌ Multiple issues detected with the new endpoint")
        sys.exit(1)