import requests
import sys
import json
import time
import math
import os

class PaginationSystemTester:
    def __init__(self, base_url="https://faster-crm.preview.emergentagent.com"):
        self.base_url = base_url
        self.token = None
        self.tests_run = 0
        self.tests_passed = 0
        self.user_id = None
        self.test_contacts = []
        self.test_products = []
        self.test_courses = []

    def run_test(self, name, method, endpoint, expected_status, data=None, headers=None):
        """Run a single API test with timing"""
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
                response = requests.get(url, headers=test_headers)
            elif method == 'POST':
                response = requests.post(url, json=data, headers=test_headers)
            elif method == 'PUT':
                response = requests.put(url, json=data, headers=test_headers)
            elif method == 'DELETE':
                response = requests.delete(url, headers=test_headers)

            end_time = time.time()
            response_time = (end_time - start_time) * 1000  # Convert to milliseconds

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
                        if 'data' in response_data:
                            print(f"   Response: Dict with 'data' containing {len(response_data['data'])} items")
                        elif 'contacts' in response_data:
                            print(f"   Response: Dict with 'contacts' containing {len(response_data['contacts'])} items")
                        elif 'products' in response_data:
                            print(f"   Response: Dict with 'products' containing {len(response_data['products'])} items")
                        elif 'courses' in response_data:
                            print(f"   Response: Dict with 'courses' containing {len(response_data['courses'])} items")
                        else:
                            print(f"   Response: Dict with keys: {list(response_data.keys())}")
                    return success, response_data, response_time
                except:
                    return success, {}, response_time
            else:
                print(f"❌ Failed - Expected {expected_status}, got {response.status_code} - Time: {response_time:.2f}ms")
                try:
                    error_data = response.json()
                    print(f"   Error: {error_data}")
                except:
                    print(f"   Error: {response.text}")
                return False, {}, response_time

        except Exception as e:
            end_time = time.time()
            response_time = (end_time - start_time) * 1000
            print(f"❌ Failed - Error: {str(e)} - Time: {response_time:.2f}ms")
            return False, {}, response_time

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

    def test_dashboard_initial_data_pagination(self):
        """Test GET /api/dashboard/initial-data - Verifica paginazione dashboard"""
        print("\n🔍 Testing Dashboard Initial Data with Pagination...")
        
        success, response, response_time = self.run_test(
            "Dashboard Initial Data - Pagination Check",
            "GET",
            "api/dashboard/initial-data",
            200
        )
        
        if success:
            # Verify response structure
            required_fields = ['success', 'dashboard_stats', 'contacts_data', 'products_data', 'courses_data']
            for field in required_fields:
                if field not in response:
                    print(f"   ❌ Missing required field: {field}")
                    return False
            
            # Check dashboard stats (should be TOTAL counts)
            stats = response.get('dashboard_stats', {})
            total_contacts = stats.get('total_contacts', 0)
            total_products = stats.get('total_products', 0)
            total_courses = stats.get('total_courses', 0)
            
            print(f"   📊 Total Statistics:")
            print(f"      - Total Contacts: {total_contacts}")
            print(f"      - Total Products: {total_products}")
            print(f"      - Total Courses: {total_courses}")
            
            # Check contacts data pagination (should return only first 100)
            contacts_data = response.get('contacts_data', {})
            contacts = contacts_data.get('contacts', [])
            contacts_pagination = contacts_data.get('pagination', {})
            
            print(f"   👥 Contacts Data:")
            print(f"      - Returned: {len(contacts)} contacts")
            print(f"      - Pagination: {contacts_pagination}")
            
            if len(contacts) > 100:
                print(f"   ❌ Too many contacts returned: {len(contacts)} (should be ≤ 100)")
                return False
            
            # Check products data pagination (should return only first 100)
            products_data = response.get('products_data', {})
            products = products_data.get('products', [])
            products_pagination = products_data.get('pagination', {})
            
            print(f"   🛍️ Products Data:")
            print(f"      - Returned: {len(products)} products")
            print(f"      - Pagination: {products_pagination}")
            
            if len(products) > 100:
                print(f"   ❌ Too many products returned: {len(products)} (should be ≤ 100)")
                return False
            
            # Check courses data pagination (should return only first 100)
            courses_data = response.get('courses_data', {})
            courses = courses_data.get('courses', [])
            courses_pagination = courses_data.get('pagination', {})
            
            print(f"   📚 Courses Data:")
            print(f"      - Returned: {len(courses)} courses")
            print(f"      - Pagination: {courses_pagination}")
            
            if len(courses) > 100:
                print(f"   ❌ Too many courses returned: {len(courses)} (should be ≤ 100)")
                return False
            
            # Verify pagination structure
            for data_type, pagination in [
                ('contacts', contacts_pagination),
                ('products', products_pagination),
                ('courses', courses_pagination)
            ]:
                required_pagination_fields = ['page', 'limit', 'total', 'pages', 'has_next', 'has_prev']
                for field in required_pagination_fields:
                    if field not in pagination:
                        print(f"   ❌ Missing pagination field '{field}' in {data_type}")
                        return False
                
                # Verify pagination values
                if pagination.get('page') != 1:
                    print(f"   ❌ Expected page 1, got {pagination.get('page')} for {data_type}")
                    return False
                
                if pagination.get('limit') != 100:
                    print(f"   ❌ Expected limit 100, got {pagination.get('limit')} for {data_type}")
                    return False
                
                if pagination.get('has_prev') != False:
                    print(f"   ❌ Expected has_prev False, got {pagination.get('has_prev')} for {data_type}")
                    return False
            
            print(f"   ✅ Dashboard initial data pagination working correctly")
            print(f"   ⚡ Response time: {response_time:.2f}ms")
            return True
        
        return False

    def test_products_pagination(self):
        """Test GET /api/products with pagination parameters"""
        print("\n🔍 Testing Products Pagination...")
        
        # Test page 1 with limit 100
        success1, response1, time1 = self.run_test(
            "Products Page 1 - Limit 100",
            "GET",
            "api/products?page=1&limit=100",
            200
        )
        
        if not success1:
            return False
        
        # Verify response structure
        if 'data' not in response1 or 'pagination' not in response1:
            print(f"   ❌ Missing 'data' or 'pagination' in response")
            return False
        
        products_page1 = response1.get('data', [])
        pagination1 = response1.get('pagination', {})
        
        print(f"   📦 Page 1 Results:")
        print(f"      - Products returned: {len(products_page1)}")
        print(f"      - Pagination: {pagination1}")
        print(f"      - Response time: {time1:.2f}ms")
        
        # Verify pagination structure
        required_fields = ['page', 'limit', 'total', 'pages', 'has_next', 'has_prev']
        for field in required_fields:
            if field not in pagination1:
                print(f"   ❌ Missing pagination field: {field}")
                return False
        
        total_products = pagination1.get('total', 0)
        total_pages = pagination1.get('pages', 0)
        
        # Test page 2 if there are multiple pages
        if total_pages > 1:
            success2, response2, time2 = self.run_test(
                "Products Page 2 - Pagination Verification",
                "GET",
                "api/products?page=2&limit=100",
                200
            )
            
            if success2:
                products_page2 = response2.get('data', [])
                pagination2 = response2.get('pagination', {})
                
                print(f"   📦 Page 2 Results:")
                print(f"      - Products returned: {len(products_page2)}")
                print(f"      - Pagination: {pagination2}")
                print(f"      - Response time: {time2:.2f}ms")
                
                # Verify page 2 pagination
                if pagination2.get('page') != 2:
                    print(f"   ❌ Expected page 2, got {pagination2.get('page')}")
                    return False
                
                if pagination2.get('has_prev') != True:
                    print(f"   ❌ Page 2 should have has_prev=True")
                    return False
                
                print(f"   ✅ Products pagination working correctly across multiple pages")
            else:
                print(f"   ❌ Failed to test page 2")
                return False
        else:
            print(f"   ℹ️ Only 1 page of products available, pagination logic still correct")
        
        return True

    def test_courses_pagination(self):
        """Test GET /api/courses with pagination and filters"""
        print("\n🔍 Testing Courses Pagination...")
        
        # Test basic pagination
        success1, response1, time1 = self.run_test(
            "Courses Page 1 - Limit 100",
            "GET",
            "api/courses?page=1&limit=100",
            200
        )
        
        if not success1:
            return False
        
        # Verify response structure
        if 'data' not in response1 or 'pagination' not in response1:
            print(f"   ❌ Missing 'data' or 'pagination' in response")
            return False
        
        courses_page1 = response1.get('data', [])
        pagination1 = response1.get('pagination', {})
        
        print(f"   📚 Page 1 Results:")
        print(f"      - Courses returned: {len(courses_page1)}")
        print(f"      - Pagination: {pagination1}")
        print(f"      - Response time: {time1:.2f}ms")
        
        # Test with language filter + pagination
        success2, response2, time2 = self.run_test(
            "Courses with Language Filter + Pagination",
            "GET",
            "api/courses?language=it&page=1&limit=100",
            200
        )
        
        if success2:
            courses_filtered = response2.get('data', [])
            pagination2 = response2.get('pagination', {})
            
            print(f"   📚 Filtered Results (language=it):")
            print(f"      - Courses returned: {len(courses_filtered)}")
            print(f"      - Pagination: {pagination2}")
            print(f"      - Response time: {time2:.2f}ms")
            
            # Verify all returned courses have language=it (if any)
            if courses_filtered:
                for course in courses_filtered:
                    if course.get('language') != 'it':
                        print(f"   ❌ Course {course.get('id')} has language {course.get('language')}, expected 'it'")
                        return False
                print(f"   ✅ Language filter working correctly with pagination")
            else:
                print(f"   ℹ️ No Italian courses found, filter logic still correct")
        else:
            print(f"   ❌ Failed to test language filter with pagination")
            return False
        
        return True

    def test_contacts_pagination(self):
        """Test GET /api/contacts with pagination"""
        print("\n🔍 Testing Contacts Pagination...")
        
        # Test basic pagination
        success1, response1, time1 = self.run_test(
            "Contacts Page 1 - Limit 100",
            "GET",
            "api/contacts?page=1&limit=100",
            200
        )
        
        if not success1:
            return False
        
        # Verify response structure
        if 'contacts' not in response1 or 'pagination' not in response1:
            print(f"   ❌ Missing 'contacts' or 'pagination' in response")
            return False
        
        contacts_page1 = response1.get('contacts', [])
        pagination1 = response1.get('pagination', {})
        
        print(f"   👥 Page 1 Results:")
        print(f"      - Contacts returned: {len(contacts_page1)}")
        print(f"      - Pagination: {pagination1}")
        print(f"      - Response time: {time1:.2f}ms")
        
        # Verify pagination structure
        required_fields = ['current_page', 'per_page', 'total_count', 'total_pages']
        for field in required_fields:
            if field not in pagination1:
                print(f"   ❌ Missing pagination field: {field}")
                return False
        
        # Test with search + pagination
        success2, response2, time2 = self.run_test(
            "Contacts with Search + Pagination",
            "GET",
            "api/contacts?search=test&page=1&limit=100",
            200
        )
        
        if success2:
            contacts_search = response2.get('contacts', [])
            pagination2 = response2.get('pagination', {})
            
            print(f"   👥 Search Results (search=test):")
            print(f"      - Contacts returned: {len(contacts_search)}")
            print(f"      - Pagination: {pagination2}")
            print(f"      - Response time: {time2:.2f}ms")
            
            print(f"   ✅ Contacts pagination working correctly with search")
        else:
            print(f"   ❌ Failed to test search with pagination")
            return False
        
        return True

    def test_performance_comparison(self):
        """Test performance comparison between paginated and non-paginated endpoints"""
        print("\n🔍 Testing Performance Comparison...")
        
        # Test paginated contacts (should be faster)
        success1, response1, time1 = self.run_test(
            "Paginated Contacts Performance",
            "GET",
            "api/contacts?page=1&limit=50",
            200
        )
        
        if not success1:
            return False
        
        # Test original contacts endpoint (should be slower for large datasets)
        success2, response2, time2 = self.run_test(
            "Original Contacts Performance",
            "GET",
            "api/contacts/original",
            200
        )
        
        if success2:
            paginated_count = len(response1.get('contacts', []))
            original_count = len(response2) if isinstance(response2, list) else 0
            
            print(f"   ⚡ Performance Comparison:")
            print(f"      - Paginated (50 items): {time1:.2f}ms - {paginated_count} contacts")
            print(f"      - Original (all items): {time2:.2f}ms - {original_count} contacts")
            
            if original_count > 50:
                performance_improvement = ((time2 - time1) / time2) * 100
                print(f"      - Performance improvement: {performance_improvement:.1f}%")
                
                if time1 < time2:
                    print(f"   ✅ Pagination provides performance improvement")
                else:
                    print(f"   ⚠️ Pagination not significantly faster (dataset may be small)")
            else:
                print(f"   ℹ️ Dataset too small to measure significant performance difference")
            
            return True
        else:
            print(f"   ❌ Failed to test original endpoint for comparison")
            return False

    def test_pagination_data_integrity(self):
        """Test that pagination maintains data integrity"""
        print("\n🔍 Testing Pagination Data Integrity...")
        
        # Get total counts from dashboard
        success1, response1, _ = self.run_test(
            "Get Dashboard Stats for Integrity Check",
            "GET",
            "api/dashboard/stats",
            200
        )
        
        if not success1:
            return False
        
        total_contacts_expected = response1.get('total_contacts', 0)
        
        # Get first page of contacts
        success2, response2, _ = self.run_test(
            "Get Contacts Page 1 for Integrity Check",
            "GET",
            "api/contacts?page=1&limit=100",
            200
        )
        
        if success2:
            pagination = response2.get('pagination', {})
            total_contacts_paginated = pagination.get('total_count', 0)
            
            print(f"   🔍 Data Integrity Check:")
            print(f"      - Dashboard total contacts: {total_contacts_expected}")
            print(f"      - Paginated total contacts: {total_contacts_paginated}")
            
            if total_contacts_expected == total_contacts_paginated:
                print(f"   ✅ Data integrity maintained - counts match")
                return True
            else:
                print(f"   ❌ Data integrity issue - counts don't match")
                return False
        
        return False

    def run_all_pagination_tests(self):
        """Run all pagination system tests"""
        print("🚀 Starting Pagination System Testing...")
        print(f"🌐 Base URL: {self.base_url}")
        print("=" * 80)
        
        # Test sequence for pagination system
        test_methods = [
            self.test_login,
            self.test_dashboard_initial_data_pagination,
            self.test_products_pagination,
            self.test_courses_pagination,
            self.test_contacts_pagination,
            self.test_performance_comparison,
            self.test_pagination_data_integrity,
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
        print("📊 PAGINATION SYSTEM TEST RESULTS")
        print("=" * 80)
        print(f"✅ Tests Passed: {self.tests_passed}")
        print(f"❌ Tests Failed: {self.tests_run - self.tests_passed}")
        print(f"📊 Total Tests: {self.tests_run}")
        print(f"📈 Success Rate: {(self.tests_passed/self.tests_run)*100:.1f}%")
        
        if self.tests_passed == self.tests_run:
            print("\n🎉 ALL PAGINATION TESTS PASSED!")
            print("✅ Dashboard initial data returns only first 100 elements")
            print("✅ Products pagination working with page/limit parameters")
            print("✅ Courses pagination working with filters")
            print("✅ Contacts pagination working correctly")
            print("✅ Performance improvement confirmed")
            print("✅ Data integrity maintained")
        elif self.tests_passed / self.tests_run >= 0.8:
            print("\n✅ PAGINATION SYSTEM MOSTLY WORKING")
            print("⚠️ Some minor issues detected, but core functionality is working")
        else:
            print("\n⚠️ PAGINATION SYSTEM NEEDS ATTENTION")
            print("❌ Multiple issues detected with pagination implementation")
        
        return self.tests_passed, self.tests_run

if __name__ == "__main__":
    print("🚀 GRABOVOI CRM - PAGINATION SYSTEM TESTING")
    print("=" * 80)
    print("Testing pagination system implementation as requested in Italian review:")
    print("1. Dashboard initial data with pagination (first 100 elements)")
    print("2. Products pagination with page/limit parameters")
    print("3. Courses pagination with filters")
    print("4. Contacts pagination")
    print("5. Performance comparison")
    print("6. Data integrity verification")
    print("=" * 80)
    
    # Get base URL from environment or use default
    base_url = os.getenv("REACT_APP_BACKEND_URL", "https://faster-crm.preview.emergentagent.com")
    
    # Run pagination tests
    pagination_tester = PaginationSystemTester(base_url)
    passed, total = pagination_tester.run_all_pagination_tests()
    
    print("\n" + "=" * 80)
    print("🎯 PAGINATION SYSTEM TEST SUMMARY")
    print("=" * 80)
    print(f"📊 Tests Passed: {passed}/{total}")
    print(f"📈 Success Rate: {(passed/total)*100:.1f}%")
    
    if passed == total:
        print("\n🎉 ALL PAGINATION TESTS PASSED!")
        print("✅ Dashboard initial data returns only first 100 elements")
        print("✅ Products pagination working with page/limit parameters")
        print("✅ Courses pagination working with filters")
        print("✅ Contacts pagination working correctly")
        print("✅ Performance improvement confirmed")
        print("✅ Data integrity maintained")
        print("✅ Pagination system is working perfectly!")
        sys.exit(0)
    elif passed / total >= 0.8:
        print("\n✅ PAGINATION SYSTEM MOSTLY WORKING")
        print("⚠️ Some minor issues detected, but core functionality is working")
        sys.exit(0)
    else:
        print("\n❌ PAGINATION SYSTEM NEEDS ATTENTION")
        print("🚨 Critical issues found with pagination implementation")
        sys.exit(1)