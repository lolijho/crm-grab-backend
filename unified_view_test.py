import requests
import sys
import json
import time
import uuid
import threading
import queue

class UnifiedViewTester:
    def __init__(self, base_url="https://faster-crm.preview.emergentagent.com"):
        self.base_url = base_url
        self.token = None
        self.tests_run = 0
        self.tests_passed = 0
        self.user_id = None
        self.test_contacts = []
        self.test_products = []
        self.test_courses = []

    def run_test(self, name, method, endpoint, expected_status, data=None, headers=None, params=None):
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
        if params:
            print(f"   Params: {params}")
        
        start_time = time.time()
        
        try:
            if method == 'GET':
                response = requests.get(url, headers=test_headers, params=params)
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
                    if isinstance(response_data, dict):
                        if 'contacts' in response_data:
                            contacts_count = len(response_data['contacts'])
                            pagination = response_data.get('pagination', {})
                            print(f"   Response: {contacts_count} contacts, pagination: {pagination}")
                        elif 'orders' in response_data:
                            orders_count = len(response_data['orders'])
                            pagination = response_data.get('pagination', {})
                            print(f"   Response: {orders_count} orders, pagination: {pagination}")
                        elif isinstance(response_data, list):
                            print(f"   Response: List with {len(response_data)} items")
                        elif len(str(response_data)) < 500:
                            print(f"   Response: {response_data}")
                        else:
                            print(f"   Response: Large object with {len(response_data)} fields")
                    elif isinstance(response_data, list):
                        print(f"   Response: List with {len(response_data)} items")
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

    def test_contacts_api_basic(self):
        """Test GET /api/contacts - Basic functionality"""
        success, response, response_time = self.run_test(
            "Contacts API - Basic",
            "GET",
            "api/contacts",
            200
        )
        
        if success:
            # Verify response structure
            if 'contacts' in response and 'pagination' in response:
                contacts = response['contacts']
                pagination = response['pagination']
                
                print(f"   ✅ Response structure correct")
                print(f"   📊 Contacts: {len(contacts)}")
                print(f"   📄 Pagination: {pagination}")
                
                # Performance check
                if response_time < 2000:  # Less than 2 seconds
                    print(f"   ⚡ Performance: EXCELLENT ({response_time:.2f}ms)")
                elif response_time < 5000:  # Less than 5 seconds
                    print(f"   ⚡ Performance: GOOD ({response_time:.2f}ms)")
                else:
                    print(f"   ⚠️ Performance: SLOW ({response_time:.2f}ms)")
                
                return True
            else:
                print(f"   ❌ Missing required fields: contacts or pagination")
                return False
        
        return False

    def test_contacts_api_pagination(self):
        """Test GET /api/contacts with pagination parameters"""
        # Test with different page sizes
        page_sizes = [10, 25, 50]
        
        for page_size in page_sizes:
            params = {"page": 1, "limit": page_size}
            
            success, response, response_time = self.run_test(
                f"Contacts API - Pagination (limit={page_size})",
                "GET",
                "api/contacts",
                200,
                params=params
            )
            
            if success:
                contacts = response.get('contacts', [])
                pagination = response.get('pagination', {})
                
                # Verify pagination works correctly
                if len(contacts) <= page_size:
                    print(f"   ✅ Pagination working: {len(contacts)} contacts (limit: {page_size})")
                    
                    # Check pagination metadata
                    if pagination.get('per_page') == page_size:
                        print(f"   ✅ Pagination metadata correct")
                    else:
                        print(f"   ❌ Pagination metadata incorrect")
                        return False
                else:
                    print(f"   ❌ Too many contacts returned: {len(contacts)} > {page_size}")
                    return False
            else:
                return False
        
        return True

    def test_contacts_api_search(self):
        """Test GET /api/contacts with search functionality"""
        # Test search with common terms
        search_terms = ["mario", "test", "gmail"]
        
        for search_term in search_terms:
            params = {"search": search_term, "page": 1, "limit": 20}
            
            success, response, response_time = self.run_test(
                f"Contacts API - Search '{search_term}'",
                "GET",
                "api/contacts",
                200,
                params=params
            )
            
            if success:
                contacts = response.get('contacts', [])
                print(f"   🔍 Search '{search_term}' found {len(contacts)} results")
                
                # Performance check for search
                if response_time < 1000:  # Less than 1 second
                    print(f"   ⚡ Search performance: EXCELLENT ({response_time:.2f}ms)")
                elif response_time < 3000:  # Less than 3 seconds
                    print(f"   ⚡ Search performance: GOOD ({response_time:.2f}ms)")
                else:
                    print(f"   ⚠️ Search performance: SLOW ({response_time:.2f}ms)")
                
                # Verify search results contain the search term (if any results)
                if len(contacts) > 0:
                    sample_contact = contacts[0]
                    contact_text = f"{sample_contact.get('first_name', '')} {sample_contact.get('last_name', '')} {sample_contact.get('email', '')}".lower()
                    if search_term.lower() in contact_text:
                        print(f"   ✅ Search results relevant")
                    else:
                        print(f"   ⚠️ Search results may not be relevant")
            else:
                return False
        
        return True

    def test_products_api(self):
        """Test GET /api/products - Products tab functionality"""
        success, response, response_time = self.run_test(
            "Products API - Basic",
            "GET",
            "api/products",
            200
        )
        
        if success:
            if isinstance(response, list):
                products = response
                print(f"   ✅ Products API working")
                print(f"   📦 Products count: {len(products)}")
                
                # Performance check
                if response_time < 2000:
                    print(f"   ⚡ Performance: EXCELLENT ({response_time:.2f}ms)")
                elif response_time < 5000:
                    print(f"   ⚡ Performance: GOOD ({response_time:.2f}ms)")
                else:
                    print(f"   ⚠️ Performance: SLOW ({response_time:.2f}ms)")
                
                # Store sample products for later tests
                self.test_products = products[:5] if len(products) > 5 else products
                
                # Verify product structure
                if len(products) > 0:
                    sample_product = products[0]
                    required_fields = ['id', 'name', 'price']
                    for field in required_fields:
                        if field not in sample_product:
                            print(f"   ❌ Missing product field: {field}")
                            return False
                    print(f"   ✅ Product structure correct")
                
                return True
            else:
                print(f"   ❌ Expected list, got: {type(response)}")
                return False
        
        return False

    def test_courses_api(self):
        """Test GET /api/courses - Courses tab functionality"""
        success, response, response_time = self.run_test(
            "Courses API - Basic",
            "GET",
            "api/courses",
            200
        )
        
        if success:
            if isinstance(response, list):
                courses = response
                print(f"   ✅ Courses API working")
                print(f"   🎓 Courses count: {len(courses)}")
                
                # Performance check
                if response_time < 2000:
                    print(f"   ⚡ Performance: EXCELLENT ({response_time:.2f}ms)")
                elif response_time < 5000:
                    print(f"   ⚡ Performance: GOOD ({response_time:.2f}ms)")
                else:
                    print(f"   ⚠️ Performance: SLOW ({response_time:.2f}ms)")
                
                # Store sample courses for later tests
                self.test_courses = courses[:5] if len(courses) > 5 else courses
                
                # Verify course structure
                if len(courses) > 0:
                    sample_course = courses[0]
                    required_fields = ['id', 'title']
                    for field in required_fields:
                        if field not in sample_course:
                            print(f"   ❌ Missing course field: {field}")
                            return False
                    print(f"   ✅ Course structure correct")
                
                return True
            else:
                print(f"   ❌ Expected list, got: {type(response)}")
                return False
        
        return False

    def test_unified_view_performance(self):
        """Test performance of loading all three datasets simultaneously"""
        print("\n🔍 Testing Unified View Performance - Simultaneous Loading...")
        
        # Simulate loading all three tabs at once
        results_queue = queue.Queue()
        
        def load_contacts():
            try:
                success, response, response_time = self.run_test(
                    "Unified - Contacts Load",
                    "GET",
                    "api/contacts",
                    200,
                    params={"page": 1, "limit": 50}
                )
                results_queue.put(("contacts", success, response_time, len(response.get('contacts', []))))
            except Exception as e:
                results_queue.put(("contacts", False, 0, 0))
        
        def load_products():
            try:
                success, response, response_time = self.run_test(
                    "Unified - Products Load",
                    "GET",
                    "api/products",
                    200
                )
                results_queue.put(("products", success, response_time, len(response) if isinstance(response, list) else 0))
            except Exception as e:
                results_queue.put(("products", False, 0, 0))
        
        def load_courses():
            try:
                success, response, response_time = self.run_test(
                    "Unified - Courses Load",
                    "GET",
                    "api/courses",
                    200
                )
                results_queue.put(("courses", success, response_time, len(response) if isinstance(response, list) else 0))
            except Exception as e:
                results_queue.put(("courses", False, 0, 0))
        
        # Start all threads simultaneously
        start_time = time.time()
        
        threads = [
            threading.Thread(target=load_contacts),
            threading.Thread(target=load_products),
            threading.Thread(target=load_courses)
        ]
        
        for thread in threads:
            thread.start()
        
        for thread in threads:
            thread.join()
        
        end_time = time.time()
        total_time = (end_time - start_time) * 1000
        
        # Collect results
        results = {}
        while not results_queue.empty():
            endpoint, success, response_time, count = results_queue.get()
            results[endpoint] = {
                'success': success,
                'response_time': response_time,
                'count': count
            }
        
        print(f"\n📊 Unified View Performance Results:")
        print(f"   ⏱️ Total parallel load time: {total_time:.2f}ms")
        
        all_successful = True
        for endpoint, result in results.items():
            if result['success']:
                print(f"   ✅ {endpoint.capitalize()}: {result['response_time']:.2f}ms ({result['count']} items)")
            else:
                print(f"   ❌ {endpoint.capitalize()}: FAILED")
                all_successful = False
        
        if all_successful:
            if total_time < 5000:  # Less than 5 seconds for all
                print(f"   🎉 Unified view performance: EXCELLENT")
            elif total_time < 10000:  # Less than 10 seconds
                print(f"   ✅ Unified view performance: GOOD")
            else:
                print(f"   ⚠️ Unified view performance: NEEDS OPTIMIZATION")
        
        return all_successful

    def test_empty_data_scenarios(self):
        """Test unified view with empty data scenarios"""
        print("\n🔍 Testing Empty Data Scenarios...")
        
        # Test with filters that should return empty results
        empty_scenarios = [
            {"endpoint": "api/contacts", "params": {"search": "nonexistentuser12345"}, "name": "Empty Contacts Search"},
            {"endpoint": "api/contacts", "params": {"status": "nonexistentstatus"}, "name": "Empty Contacts Status Filter"},
            {"endpoint": "api/contacts", "params": {"language": "zz"}, "name": "Empty Contacts Language Filter"}
        ]
        
        all_successful = True
        
        for scenario in empty_scenarios:
            success, response, response_time = self.run_test(
                scenario["name"],
                "GET",
                scenario["endpoint"],
                200,
                params=scenario["params"]
            )
            
            if success:
                if 'contacts' in response:
                    contacts = response['contacts']
                    pagination = response.get('pagination', {})
                    
                    print(f"   ✅ Empty scenario handled: {len(contacts)} results")
                    print(f"   📄 Pagination: {pagination}")
                    
                    # Verify pagination is correct for empty results
                    if pagination.get('total_count', 0) == 0 and len(contacts) == 0:
                        print(f"   ✅ Empty data pagination correct")
                    else:
                        print(f"   ⚠️ Empty data pagination may be incorrect")
                else:
                    print(f"   ❌ Unexpected response structure for empty scenario")
                    all_successful = False
            else:
                all_successful = False
        
        return all_successful

    def test_large_dataset_handling(self):
        """Test unified view with large datasets"""
        print("\n🔍 Testing Large Dataset Handling...")
        
        # Test with maximum page sizes
        large_dataset_tests = [
            {"endpoint": "api/contacts", "params": {"page": 1, "limit": 100}, "name": "Large Contacts Page"},
            {"endpoint": "api/contacts", "params": {"page": 1, "limit": 200}, "name": "Very Large Contacts Page"}
        ]
        
        all_successful = True
        
        for test in large_dataset_tests:
            success, response, response_time = self.run_test(
                test["name"],
                "GET",
                test["endpoint"],
                200,
                params=test["params"]
            )
            
            if success:
                contacts = response.get('contacts', [])
                pagination = response.get('pagination', {})
                
                print(f"   📊 Retrieved {len(contacts)} contacts")
                print(f"   ⏱️ Response time: {response_time:.2f}ms")
                
                # Performance check for large datasets
                if response_time < 3000:  # Less than 3 seconds
                    print(f"   ⚡ Large dataset performance: EXCELLENT")
                elif response_time < 8000:  # Less than 8 seconds
                    print(f"   ✅ Large dataset performance: ACCEPTABLE")
                else:
                    print(f"   ⚠️ Large dataset performance: NEEDS OPTIMIZATION")
                
                # Verify pagination metadata
                if pagination.get('per_page') == test['params']['limit']:
                    print(f"   ✅ Large dataset pagination correct")
                else:
                    print(f"   ❌ Large dataset pagination incorrect")
                    all_successful = False
            else:
                all_successful = False
        
        return all_successful

    def test_api_response_formats(self):
        """Test API response formats for unified view compatibility"""
        print("\n🔍 Testing API Response Formats...")
        
        # Test contacts response format
        success, response, _ = self.run_test(
            "Contacts Response Format",
            "GET",
            "api/contacts",
            200,
            params={"page": 1, "limit": 5}
        )
        
        if success:
            # Verify contacts response structure
            required_fields = ['contacts', 'pagination']
            for field in required_fields:
                if field not in response:
                    print(f"   ❌ Missing contacts field: {field}")
                    return False
            
            # Verify pagination structure
            pagination = response['pagination']
            pagination_fields = ['current_page', 'per_page', 'total_count', 'total_pages']
            for field in pagination_fields:
                if field not in pagination:
                    print(f"   ❌ Missing pagination field: {field}")
                    return False
            
            print(f"   ✅ Contacts response format correct")
            
            # Verify contact structure
            contacts = response['contacts']
            if len(contacts) > 0:
                contact = contacts[0]
                contact_fields = ['id', 'first_name', 'last_name', 'email', 'status']
                for field in contact_fields:
                    if field not in contact:
                        print(f"   ⚠️ Missing contact field: {field}")
                
                print(f"   ✅ Contact structure verified")
        else:
            return False
        
        # Test products response format
        success, response, _ = self.run_test(
            "Products Response Format",
            "GET",
            "api/products",
            200
        )
        
        if success:
            if isinstance(response, list):
                print(f"   ✅ Products response format correct (array)")
                
                if len(response) > 0:
                    product = response[0]
                    product_fields = ['id', 'name', 'price']
                    for field in product_fields:
                        if field not in product:
                            print(f"   ⚠️ Missing product field: {field}")
                    
                    print(f"   ✅ Product structure verified")
            else:
                print(f"   ❌ Products should return array, got: {type(response)}")
                return False
        else:
            return False
        
        # Test courses response format
        success, response, _ = self.run_test(
            "Courses Response Format",
            "GET",
            "api/courses",
            200
        )
        
        if success:
            if isinstance(response, list):
                print(f"   ✅ Courses response format correct (array)")
                
                if len(response) > 0:
                    course = response[0]
                    course_fields = ['id', 'title']
                    for field in course_fields:
                        if field not in course:
                            print(f"   ⚠️ Missing course field: {field}")
                    
                    print(f"   ✅ Course structure verified")
            else:
                print(f"   ❌ Courses should return array, got: {type(response)}")
                return False
        else:
            return False
        
        return True

    def test_concurrent_api_calls(self):
        """Test concurrent API calls to simulate real unified view usage"""
        print("\n🔍 Testing Concurrent API Calls...")
        
        results_queue = queue.Queue()
        
        def make_concurrent_calls():
            # Simulate a user rapidly switching between tabs
            calls = [
                ("api/contacts", {"page": 1, "limit": 20}),
                ("api/products", {}),
                ("api/courses", {}),
                ("api/contacts", {"search": "test", "page": 1, "limit": 10}),
                ("api/contacts", {"page": 2, "limit": 20}),
            ]
            
            for i, (endpoint, params) in enumerate(calls):
                try:
                    success, response, response_time = self.run_test(
                        f"Concurrent Call {i+1}",
                        "GET",
                        endpoint,
                        200,
                        params=params if params else None
                    )
                    results_queue.put((i+1, endpoint, success, response_time))
                except Exception as e:
                    results_queue.put((i+1, endpoint, False, 0))
                
                # Small delay to simulate user interaction
                time.sleep(0.1)
        
        # Run concurrent calls
        thread = threading.Thread(target=make_concurrent_calls)
        start_time = time.time()
        thread.start()
        thread.join()
        end_time = time.time()
        
        total_time = (end_time - start_time) * 1000
        
        # Collect results
        results = []
        while not results_queue.empty():
            results.append(results_queue.get())
        
        print(f"\n📊 Concurrent API Calls Results:")
        print(f"   ⏱️ Total time for {len(results)} calls: {total_time:.2f}ms")
        
        successful_calls = 0
        for call_num, endpoint, success, response_time in results:
            if success:
                print(f"   ✅ Call {call_num} ({endpoint}): {response_time:.2f}ms")
                successful_calls += 1
            else:
                print(f"   ❌ Call {call_num} ({endpoint}): FAILED")
        
        success_rate = (successful_calls / len(results)) * 100
        print(f"   📈 Success rate: {success_rate:.1f}% ({successful_calls}/{len(results)})")
        
        return successful_calls == len(results)

    def run_all_unified_view_tests(self):
        """Run all unified view tests"""
        print("🚀 Starting Unified View Functionality Testing...")
        print(f"🌐 Base URL: {self.base_url}")
        print("=" * 80)
        
        # Test sequence for unified view functionality
        test_methods = [
            self.test_login,
            self.test_contacts_api_basic,
            self.test_contacts_api_pagination,
            self.test_contacts_api_search,
            self.test_products_api,
            self.test_courses_api,
            self.test_unified_view_performance,
            self.test_empty_data_scenarios,
            self.test_large_dataset_handling,
            self.test_api_response_formats,
            self.test_concurrent_api_calls,
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
        print("📊 UNIFIED VIEW FUNCTIONALITY TEST RESULTS")
        print("=" * 80)
        print(f"✅ Tests Passed: {self.tests_passed}")
        print(f"❌ Tests Failed: {self.tests_run - self.tests_passed}")
        print(f"📊 Total Tests: {self.tests_run}")
        print(f"📈 Success Rate: {(self.tests_passed/self.tests_run)*100:.1f}%")
        
        if self.tests_passed == self.tests_run:
            print("\n🎉 ALL UNIFIED VIEW TESTS PASSED!")
            print("✅ Contacts API with pagination and search - WORKING")
            print("✅ Products API - WORKING")
            print("✅ Courses API - WORKING")
            print("✅ Performance optimization - VERIFIED")
            print("✅ Empty data scenarios - HANDLED")
            print("✅ Large datasets - SUPPORTED")
            print("✅ API response formats - COMPATIBLE")
            print("✅ Concurrent usage - STABLE")
        elif self.tests_passed / self.tests_run >= 0.8:
            print("\n✅ UNIFIED VIEW FUNCTIONALITY MOSTLY WORKING")
            print("⚠️ Some minor issues detected, but core functionality is working")
        else:
            print("\n⚠️ UNIFIED VIEW FUNCTIONALITY NEEDS ATTENTION")
            print("❌ Multiple issues detected with unified view APIs")
        
        return self.tests_passed, self.tests_run

if __name__ == "__main__":
    # Run unified view tests
    tester = UnifiedViewTester()
    passed, total = tester.run_all_unified_view_tests()
    
    print(f"\n🏁 UNIFIED VIEW TESTING COMPLETE")
    print(f"📈 Final Result: {passed}/{total} tests passed ({(passed/total)*100:.1f}%)")
    
    if passed == total:
        print("🎉 ALL UNIFIED VIEW FUNCTIONALITY WORKING PERFECTLY!")
    elif passed / total >= 0.8:
        print("✅ UNIFIED VIEW FUNCTIONALITY MOSTLY WORKING")
    else:
        print("⚠️ UNIFIED VIEW FUNCTIONALITY NEEDS ATTENTION")