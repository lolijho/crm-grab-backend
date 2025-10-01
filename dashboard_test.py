import requests
import sys
import json
import time
import os
from datetime import datetime

class DashboardTester:
    def __init__(self, base_url="https://faster-crm.preview.emergentagent.com"):
        self.base_url = base_url
        self.token = None
        self.tests_run = 0
        self.tests_passed = 0
        self.user_id = None
        self.response_times = {}

    def run_test(self, name, method, endpoint, expected_status, data=None, headers=None, timeout=10):
        """Run a single API test with performance tracking"""
        url = f"{self.base_url}/{endpoint}"
        test_headers = {'Content-Type': 'application/json'}
        
        if self.token:
            test_headers['Authorization'] = f'Bearer {self.token}'
        
        if headers:
            test_headers.update(headers)

        self.tests_run += 1
        print(f"\n🔍 Testing {name}...")
        print(f"   URL: {method} {url}")
        
        start_time = time.time()
        
        try:
            if method == 'GET':
                response = requests.get(url, headers=test_headers, timeout=timeout)
            elif method == 'POST':
                response = requests.post(url, json=data, headers=test_headers, timeout=timeout)
            elif method == 'PUT':
                response = requests.put(url, json=data, headers=test_headers, timeout=timeout)
            elif method == 'DELETE':
                response = requests.delete(url, headers=test_headers, timeout=timeout)

            end_time = time.time()
            response_time = (end_time - start_time) * 1000  # Convert to milliseconds
            self.response_times[name] = response_time
            
            success = response.status_code == expected_status
            if success:
                self.tests_passed += 1
                print(f"✅ Passed - Status: {response.status_code} - Time: {response_time:.2f}ms")
                try:
                    response_data = response.json()
                    if isinstance(response_data, dict) and len(str(response_data)) < 1000:
                        print(f"   Response: {response_data}")
                    elif isinstance(response_data, list):
                        print(f"   Response: List with {len(response_data)} items")
                    elif isinstance(response_data, dict):
                        # For large responses, show summary
                        keys = list(response_data.keys())
                        print(f"   Response keys: {keys}")
                    return success, response_data
                except:
                    return success, {}
            else:
                print(f"❌ Failed - Expected {expected_status}, got {response.status_code} - Time: {response_time:.2f}ms")
                try:
                    error_data = response.json()
                    print(f"   Error: {error_data}")
                except:
                    print(f"   Error: {response.text}")
                return False, {}

        except requests.exceptions.Timeout:
            print(f"❌ Failed - Request timeout after {timeout} seconds")
            return False, {}
        except Exception as e:
            print(f"❌ Failed - Error: {str(e)}")
            return False, {}

    def test_login(self):
        """Test login with admin credentials"""
        success, response = self.run_test(
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

    def test_backend_health(self):
        """Test backend health and availability"""
        success, response = self.run_test(
            "Backend Health Check",
            "GET",
            "api/health",
            200,
            timeout=5
        )
        
        if success:
            if response.get('status') == 'healthy':
                print(f"   ✅ Backend is healthy and responding")
                return True
            else:
                print(f"   ❌ Backend status: {response.get('status')}")
                return False
        return False

    def test_dashboard_stats_endpoint(self):
        """Test /api/dashboard/stats endpoint"""
        if not self.token:
            print(f"   ❌ No authentication token available")
            return False
        
        success, response = self.run_test(
            "Dashboard Stats Endpoint",
            "GET",
            "api/dashboard/stats",
            200,
            timeout=5
        )
        
        if success:
            # Verify response structure
            expected_fields = ['total_contacts', 'active_students', 'total_orders', 'leads']
            missing_fields = []
            
            for field in expected_fields:
                if field not in response:
                    missing_fields.append(field)
                else:
                    value = response[field]
                    print(f"   📊 {field}: {value}")
            
            if missing_fields:
                print(f"   ❌ Missing fields: {missing_fields}")
                return False
            
            # Verify data types are numbers
            for field in expected_fields:
                if not isinstance(response[field], (int, float)):
                    print(f"   ❌ {field} should be a number, got: {type(response[field])}")
                    return False
            
            print(f"   ✅ Dashboard stats endpoint working correctly")
            return True
        
        return False

    def test_contacts_endpoint(self):
        """Test /api/contacts endpoint"""
        if not self.token:
            print(f"   ❌ No authentication token available")
            return False
        
        success, response = self.run_test(
            "Contacts Endpoint",
            "GET",
            "api/contacts",
            200,
            timeout=10
        )
        
        if success:
            # Check if it's paginated response or direct list
            if isinstance(response, dict) and 'contacts' in response:
                # Paginated response
                contacts = response['contacts']
                pagination = response.get('pagination', {})
                
                print(f"   📊 Paginated response: {len(contacts)} contacts")
                print(f"   📄 Pagination: Page {pagination.get('current_page', 'N/A')} of {pagination.get('total_pages', 'N/A')}")
                print(f"   📊 Total contacts: {pagination.get('total_count', 'N/A')}")
                
                # Verify contact structure
                if len(contacts) > 0:
                    contact = contacts[0]
                    expected_fields = ['id', 'first_name', 'last_name', 'email', 'status']
                    for field in expected_fields:
                        if field not in contact:
                            print(f"   ❌ Missing contact field: {field}")
                            return False
                    print(f"   ✅ Contact structure correct")
                
            elif isinstance(response, list):
                # Direct list response
                contacts = response
                print(f"   📊 Direct list response: {len(contacts)} contacts")
                
                # Verify contact structure
                if len(contacts) > 0:
                    contact = contacts[0]
                    expected_fields = ['id', 'first_name', 'last_name', 'email', 'status']
                    for field in expected_fields:
                        if field not in contact:
                            print(f"   ❌ Missing contact field: {field}")
                            return False
                    print(f"   ✅ Contact structure correct")
            else:
                print(f"   ❌ Unexpected response format")
                return False
            
            print(f"   ✅ Contacts endpoint working correctly")
            return True
        
        return False

    def test_orders_endpoint(self):
        """Test /api/orders endpoint"""
        if not self.token:
            print(f"   ❌ No authentication token available")
            return False
        
        success, response = self.run_test(
            "Orders Endpoint",
            "GET",
            "api/orders",
            200,
            timeout=15  # Orders might take longer due to complex aggregation
        )
        
        if success:
            # Check if it's paginated response or direct list
            if isinstance(response, dict) and 'orders' in response:
                # Paginated response
                orders = response['orders']
                pagination = response.get('pagination', {})
                
                print(f"   📊 Paginated response: {len(orders)} orders")
                print(f"   📄 Pagination: Page {pagination.get('current_page', 'N/A')} of {pagination.get('total_pages', 'N/A')}")
                print(f"   📊 Total orders: {pagination.get('total_count', 'N/A')}")
                
                # Verify order structure
                if len(orders) > 0:
                    order = orders[0]
                    expected_fields = ['id', 'order_number', 'total_amount', 'status']
                    for field in expected_fields:
                        if field not in order:
                            print(f"   ❌ Missing order field: {field}")
                            return False
                    print(f"   ✅ Order structure correct")
                
            elif isinstance(response, list):
                # Direct list response
                orders = response
                print(f"   📊 Direct list response: {len(orders)} orders")
                
                # Verify order structure
                if len(orders) > 0:
                    order = orders[0]
                    expected_fields = ['id', 'order_number', 'total_amount', 'status']
                    for field in expected_fields:
                        if field not in order:
                            print(f"   ❌ Missing order field: {field}")
                            return False
                    print(f"   ✅ Order structure correct")
            else:
                print(f"   ❌ Unexpected response format")
                return False
            
            print(f"   ✅ Orders endpoint working correctly")
            return True
        
        return False

    def test_authentication_system(self):
        """Test authentication system for dashboard endpoints"""
        # Test without authentication
        original_token = self.token
        self.token = None
        
        endpoints_to_test = [
            ("api/dashboard/stats", "Dashboard Stats"),
            ("api/contacts", "Contacts"),
            ("api/orders", "Orders")
        ]
        
        auth_tests_passed = 0
        
        for endpoint, name in endpoints_to_test:
            success, response = self.run_test(
                f"Auth Test - {name} (No Token)",
                "GET",
                endpoint,
                401  # Should require authentication
            )
            
            if success:
                auth_tests_passed += 1
                print(f"   ✅ {name} endpoint properly protected")
            else:
                print(f"   ❌ {name} endpoint not properly protected")
        
        # Restore token
        self.token = original_token
        
        if auth_tests_passed == len(endpoints_to_test):
            print(f"   ✅ All dashboard endpoints properly require authentication")
            return True
        else:
            print(f"   ❌ {len(endpoints_to_test) - auth_tests_passed} endpoints not properly protected")
            return False

    def test_performance_requirements(self):
        """Test that all dashboard endpoints respond within 5 seconds"""
        print("\n🔍 Testing Performance Requirements (< 5 seconds)...")
        
        performance_results = []
        
        for test_name, response_time in self.response_times.items():
            if any(keyword in test_name.lower() for keyword in ['dashboard', 'contacts', 'orders']):
                is_fast = response_time < 5000  # 5 seconds in milliseconds
                performance_results.append(is_fast)
                
                if is_fast:
                    print(f"   ✅ {test_name}: {response_time:.2f}ms (FAST)")
                else:
                    print(f"   ❌ {test_name}: {response_time:.2f}ms (SLOW - > 5s)")
        
        if all(performance_results):
            print(f"   ✅ All dashboard endpoints respond within 5 seconds")
            return True
        else:
            slow_count = len([r for r in performance_results if not r])
            print(f"   ❌ {slow_count} endpoints are slower than 5 seconds")
            return False

    def test_dashboard_data_consistency(self):
        """Test data consistency between dashboard stats and actual data"""
        if not self.token:
            print(f"   ❌ No authentication token available")
            return False
        
        # Get dashboard stats
        stats_success, stats_response = self.run_test(
            "Dashboard Stats for Consistency Check",
            "GET",
            "api/dashboard/stats",
            200
        )
        
        if not stats_success:
            return False
        
        # Get contacts count
        contacts_success, contacts_response = self.run_test(
            "Contacts for Consistency Check",
            "GET",
            "api/contacts",
            200
        )
        
        if not contacts_success:
            return False
        
        # Get orders count
        orders_success, orders_response = self.run_test(
            "Orders for Consistency Check",
            "GET",
            "api/orders",
            200
        )
        
        if not orders_success:
            return False
        
        # Extract actual counts
        if isinstance(contacts_response, dict) and 'pagination' in contacts_response:
            actual_contacts = contacts_response['pagination']['total_count']
        elif isinstance(contacts_response, list):
            actual_contacts = len(contacts_response)
        else:
            print(f"   ❌ Cannot determine contacts count")
            return False
        
        if isinstance(orders_response, dict) and 'pagination' in orders_response:
            actual_orders = orders_response['pagination']['total_count']
        elif isinstance(orders_response, list):
            actual_orders = len(orders_response)
        else:
            print(f"   ❌ Cannot determine orders count")
            return False
        
        # Compare with dashboard stats
        dashboard_contacts = stats_response.get('total_contacts', 0)
        dashboard_orders = stats_response.get('total_orders', 0)
        
        consistency_checks = []
        
        # Check contacts consistency
        if dashboard_contacts == actual_contacts:
            print(f"   ✅ Contacts count consistent: {dashboard_contacts}")
            consistency_checks.append(True)
        else:
            print(f"   ❌ Contacts count mismatch: Dashboard={dashboard_contacts}, Actual={actual_contacts}")
            consistency_checks.append(False)
        
        # Check orders consistency
        if dashboard_orders == actual_orders:
            print(f"   ✅ Orders count consistent: {dashboard_orders}")
            consistency_checks.append(True)
        else:
            print(f"   ❌ Orders count mismatch: Dashboard={dashboard_orders}, Actual={actual_orders}")
            consistency_checks.append(False)
        
        if all(consistency_checks):
            print(f"   ✅ Dashboard data is consistent with actual data")
            return True
        else:
            print(f"   ❌ Dashboard data inconsistencies detected")
            return False

    def test_error_handling(self):
        """Test error handling for dashboard endpoints"""
        if not self.token:
            print(f"   ❌ No authentication token available")
            return False
        
        # Test with invalid token
        original_token = self.token
        self.token = "invalid.jwt.token"
        
        success, response = self.run_test(
            "Dashboard Stats with Invalid Token",
            "GET",
            "api/dashboard/stats",
            401
        )
        
        # Restore token
        self.token = original_token
        
        if success:
            print(f"   ✅ Invalid token properly handled")
            return True
        else:
            print(f"   ❌ Invalid token not properly handled")
            return False

    def run_all_dashboard_tests(self):
        """Run all dashboard functionality tests"""
        print("🚀 Starting Dashboard Functionality Testing...")
        print(f"🌐 Base URL: {self.base_url}")
        print("=" * 80)
        
        # Test sequence for dashboard functionality
        test_methods = [
            self.test_login,
            self.test_backend_health,
            self.test_dashboard_stats_endpoint,
            self.test_contacts_endpoint,
            self.test_orders_endpoint,
            self.test_authentication_system,
            self.test_error_handling,
            self.test_dashboard_data_consistency,
            self.test_performance_requirements,
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
        print("📊 DASHBOARD FUNCTIONALITY TEST RESULTS")
        print("=" * 80)
        print(f"✅ Tests Passed: {self.tests_passed}")
        print(f"❌ Tests Failed: {self.tests_run - self.tests_passed}")
        print(f"📊 Total Tests: {self.tests_run}")
        print(f"📈 Success Rate: {(self.tests_passed/self.tests_run)*100:.1f}%")
        
        # Performance summary
        print("\n📈 PERFORMANCE SUMMARY:")
        for test_name, response_time in self.response_times.items():
            if any(keyword in test_name.lower() for keyword in ['dashboard', 'contacts', 'orders']):
                status = "🟢 FAST" if response_time < 5000 else "🔴 SLOW"
                print(f"   {status} {test_name}: {response_time:.2f}ms")
        
        if self.tests_passed == self.tests_run:
            print("\n🎉 ALL DASHBOARD TESTS PASSED!")
            print("✅ Dashboard should load correctly in frontend")
        elif self.tests_passed / self.tests_run >= 0.8:
            print("\n✅ DASHBOARD MOSTLY WORKING")
            print("⚠️ Minor issues detected - dashboard may have some loading delays")
        else:
            print("\n⚠️ DASHBOARD HAS ISSUES")
            print("❌ Dashboard loading problems likely - check failed tests above")
        
        return self.tests_passed, self.tests_run

if __name__ == "__main__":
    # Run dashboard tests based on the review request
    print("🚀 Starting Dashboard Loading Issue Investigation...")
    print("=" * 80)
    
    # Dashboard Functionality Tests (Primary focus based on review request)
    dashboard_tester = DashboardTester()
    dashboard_passed, dashboard_total = dashboard_tester.run_all_dashboard_tests()
    
    # Final Summary
    print("\n" + "=" * 80)
    print("🎯 DASHBOARD TESTING RESULTS")
    print("=" * 80)
    print(f"📊 Dashboard Tests: {dashboard_passed}/{dashboard_total} ({(dashboard_passed/dashboard_total)*100:.1f}%)")
    print("=" * 80)
    
    if dashboard_passed == dashboard_total:
        print("\n🎉 ALL DASHBOARD TESTS PASSED!")
        print("✅ The dashboard loading issue should be resolved")
        print("✅ All API endpoints (/api/dashboard/stats, /api/contacts, /api/orders) are working")
        print("✅ Authentication is working correctly")
        print("✅ Performance is within acceptable limits (< 5 seconds)")
    elif dashboard_passed / dashboard_total >= 0.8:
        print("\n⚠️ DASHBOARD MOSTLY WORKING - MINOR ISSUES DETECTED")
        print("🔍 Check the failed tests above for specific issues")
        print("💡 Dashboard may load but with some delays or missing data")
    else:
        print("\n❌ DASHBOARD HAS MAJOR ISSUES")
        print("🔍 Multiple API endpoints are failing")
        print("💡 Dashboard will likely remain stuck in loading state")
        print("🛠️ Review the failed tests above and fix the underlying issues")
    
    print("=" * 80)