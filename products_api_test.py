import requests
import sys
import json
import time

class ProductsAPITester:
    def __init__(self, base_url="https://faster-crm.preview.emergentagent.com"):
        self.base_url = base_url
        self.token = None
        self.tests_run = 0
        self.tests_passed = 0
        self.user_id = None
        self.test_product_id = None

    def run_test(self, name, method, endpoint, expected_status, data=None, headers=None):
        """Run a single API test"""
        url = f"{self.base_url}/{endpoint}"
        test_headers = {'Content-Type': 'application/json'}
        
        if self.token:
            test_headers['Authorization'] = f'Bearer {self.token}'
        
        if headers:
            test_headers.update(headers)

        self.tests_run += 1
        print(f"\n🔍 Testing {name}...")
        print(f"   URL: {method} {url}")
        
        try:
            if method == 'GET':
                response = requests.get(url, headers=test_headers)
            elif method == 'POST':
                response = requests.post(url, json=data, headers=test_headers)
            elif method == 'PUT':
                response = requests.put(url, json=data, headers=test_headers)
            elif method == 'DELETE':
                response = requests.delete(url, headers=test_headers)

            success = response.status_code == expected_status
            if success:
                self.tests_passed += 1
                print(f"✅ Passed - Status: {response.status_code}")
                try:
                    response_data = response.json()
                    if isinstance(response_data, dict) and len(str(response_data)) < 1000:
                        print(f"   Response: {response_data}")
                    elif isinstance(response_data, list):
                        print(f"   Response: List with {len(response_data)} items")
                    elif isinstance(response_data, dict) and 'data' in response_data:
                        print(f"   Response: Dict with {len(response_data.get('data', []))} products")
                    return success, response_data
                except:
                    return success, {}
            else:
                print(f"❌ Failed - Expected {expected_status}, got {response.status_code}")
                try:
                    error_data = response.json()
                    print(f"   Error: {error_data}")
                except:
                    print(f"   Error: {response.text}")
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

    def test_get_products_basic(self):
        """Test GET /api/products - Basic functionality"""
        success, response = self.run_test(
            "GET Products - Basic",
            "GET",
            "api/products",
            200
        )
        
        if success:
            # Check response structure
            if 'data' in response and 'pagination' in response:
                products = response.get('data', [])
                pagination = response.get('pagination', {})
                
                print(f"   📊 Products found: {len(products)}")
                print(f"   📄 Pagination: {pagination}")
                
                # Verify pagination structure
                expected_pagination_fields = ['page', 'limit', 'total', 'pages', 'has_next', 'has_prev']
                for field in expected_pagination_fields:
                    if field not in pagination:
                        print(f"   ❌ Missing pagination field: {field}")
                        return False
                
                # If products exist, verify structure
                if products:
                    product = products[0]
                    expected_fields = ['id', 'name', 'price', 'created_at']
                    for field in expected_fields:
                        if field not in product:
                            print(f"   ❌ Missing product field: {field}")
                            return False
                    
                    print(f"   ✅ Product structure valid")
                    print(f"   📦 First product: {product.get('name')} - €{product.get('price')}")
                    
                    # Store for other tests
                    self.test_product_id = product.get('id')
                else:
                    print(f"   ⚠️ No products found in database")
                
                return True
            else:
                print(f"   ❌ Invalid response structure - missing 'data' or 'pagination'")
                return False
        
        return False

    def test_get_products_with_pagination(self):
        """Test GET /api/products with pagination parameters"""
        # Test with different page sizes
        page_sizes = [1, 5, 10]
        
        for limit in page_sizes:
            success, response = self.run_test(
                f"GET Products - Pagination (limit={limit})",
                "GET",
                f"api/products?page=1&limit={limit}",
                200
            )
            
            if success:
                products = response.get('data', [])
                pagination = response.get('pagination', {})
                
                # Verify limit is respected
                if len(products) <= limit:
                    print(f"   ✅ Pagination limit respected: {len(products)} <= {limit}")
                else:
                    print(f"   ❌ Pagination limit exceeded: {len(products)} > {limit}")
                    return False
                
                # Verify pagination metadata
                if pagination.get('limit') == limit:
                    print(f"   ✅ Pagination metadata correct")
                else:
                    print(f"   ❌ Pagination metadata incorrect")
                    return False
            else:
                return False
        
        return True

    def test_get_products_with_search(self):
        """Test GET /api/products with search functionality"""
        # Test search functionality
        search_terms = ["test", "product", "corso"]
        
        for search_term in search_terms:
            success, response = self.run_test(
                f"GET Products - Search '{search_term}'",
                "GET",
                f"api/products?search={search_term}",
                200
            )
            
            if success:
                products = response.get('data', [])
                print(f"   🔍 Search '{search_term}' found {len(products)} products")
                
                # If products found, verify they contain the search term
                if products:
                    for product in products:
                        name = product.get('name', '').lower()
                        description = product.get('description', '').lower()
                        if search_term.lower() not in name and search_term.lower() not in description:
                            print(f"   ⚠️ Product '{product.get('name')}' doesn't contain search term")
                
                return True
            else:
                return False
        
        return True

    def test_get_products_with_filters(self):
        """Test GET /api/products with category and active filters"""
        # Test category filter
        success, response = self.run_test(
            "GET Products - Category Filter",
            "GET",
            "api/products?category=corso",
            200
        )
        
        if success:
            products = response.get('data', [])
            print(f"   📂 Category 'corso' filter found {len(products)} products")
        
        # Test active filter
        success2, response2 = self.run_test(
            "GET Products - Active Filter",
            "GET",
            "api/products?is_active=true",
            200
        )
        
        if success2:
            products = response2.get('data', [])
            print(f"   ✅ Active products filter found {len(products)} products")
            
            # Verify all products are active
            for product in products:
                if not product.get('is_active', True):
                    print(f"   ❌ Inactive product found in active filter")
                    return False
        
        return success and success2

    def test_get_single_product(self):
        """Test GET /api/products/{id} - Single product endpoint"""
        if not self.test_product_id:
            print("   ⚠️ No test product ID available, skipping single product test")
            return True
        
        success, response = self.run_test(
            "GET Single Product",
            "GET",
            f"api/products/{self.test_product_id}",
            200
        )
        
        if success:
            # Verify product structure
            expected_fields = ['id', 'name', 'price', 'created_at', 'updated_at']
            for field in expected_fields:
                if field not in response:
                    print(f"   ❌ Missing product field: {field}")
                    return False
            
            print(f"   ✅ Single product retrieved successfully")
            print(f"   📦 Product: {response.get('name')} - €{response.get('price')}")
            
            # Check if course information is included
            if 'course' in response:
                course = response.get('course')
                if course:
                    print(f"   📚 Associated course: {course.get('title', 'N/A')}")
                else:
                    print(f"   📚 No associated course")
            
            return True
        
        return False

    def test_products_authentication(self):
        """Test that products endpoints require authentication"""
        # Store original token
        original_token = self.token
        self.token = None
        
        success, response = self.run_test(
            "GET Products - No Authentication",
            "GET",
            "api/products",
            401  # Should require authentication
        )
        
        # Restore token
        self.token = original_token
        
        if success:
            print(f"   ✅ Authentication properly required")
            return True
        else:
            print(f"   ❌ Authentication not properly enforced")
            return False

    def test_products_course_association(self):
        """Test products with course associations"""
        success, response = self.run_test(
            "GET Products - Course Associations",
            "GET",
            "api/products",
            200
        )
        
        if success:
            products = response.get('data', [])
            products_with_courses = 0
            
            for product in products:
                if 'course' in product and product.get('course'):
                    products_with_courses += 1
                    course = product.get('course')
                    print(f"   📚 Product '{product.get('name')}' → Course '{course.get('title')}'")
            
            print(f"   📊 Products with course associations: {products_with_courses}/{len(products)}")
            
            # This is informational, not a failure
            return True
        
        return False

    def test_products_error_handling(self):
        """Test error handling for products endpoints"""
        # Test invalid product ID
        success, response = self.run_test(
            "GET Product - Invalid ID",
            "GET",
            "api/products/invalid-id-format",
            400  # Should return bad request
        )
        
        if success:
            print(f"   ✅ Invalid product ID properly handled")
        
        # Test non-existent product ID
        success2, response2 = self.run_test(
            "GET Product - Non-existent ID",
            "GET",
            "api/products/507f1f77bcf86cd799439011",
            404  # Should return not found
        )
        
        if success2:
            print(f"   ✅ Non-existent product ID properly handled")
        
        return success and success2

    def test_dashboard_initial_data_products(self):
        """Test products in dashboard initial data endpoint"""
        success, response = self.run_test(
            "Dashboard Initial Data - Products",
            "GET",
            "api/dashboard/initial-data",
            200
        )
        
        if success:
            # Check if products_data is included
            if 'products_data' in response:
                products_data = response.get('products_data', {})
                products = products_data.get('products', [])
                total = products_data.get('total', 0)
                
                print(f"   📊 Dashboard products: {len(products)} loaded, {total} total")
                
                # Verify structure matches regular products endpoint
                if products:
                    product = products[0]
                    expected_fields = ['id', 'name', 'price']
                    for field in expected_fields:
                        if field not in product:
                            print(f"   ❌ Missing product field in dashboard: {field}")
                            return False
                    
                    print(f"   ✅ Dashboard products structure valid")
                
                return True
            else:
                print(f"   ❌ products_data missing from dashboard initial data")
                return False
        
        return False

    def run_all_products_tests(self):
        """Run all products API tests"""
        print("🚀 Starting Products API Testing...")
        print(f"🌐 Base URL: {self.base_url}")
        print("🎯 Focus: Resolving blank Products page issue")
        print("=" * 80)
        
        # Test sequence for products API
        test_methods = [
            self.test_login,
            self.test_get_products_basic,
            self.test_get_products_with_pagination,
            self.test_get_products_with_search,
            self.test_get_products_with_filters,
            self.test_get_single_product,
            self.test_products_authentication,
            self.test_products_course_association,
            self.test_products_error_handling,
            self.test_dashboard_initial_data_products,
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
        print("📊 PRODUCTS API TEST RESULTS")
        print("=" * 80)
        print(f"✅ Tests Passed: {self.tests_passed}")
        print(f"❌ Tests Failed: {self.tests_run - self.tests_passed}")
        print(f"📊 Total Tests: {self.tests_run}")
        print(f"📈 Success Rate: {(self.tests_passed/self.tests_run)*100:.1f}%")
        
        if self.tests_passed == self.tests_run:
            print("\n🎉 ALL PRODUCTS API TESTS PASSED!")
            print("✅ Products API is working correctly")
            print("✅ The issue may be in the frontend Products.js component")
        elif self.tests_passed / self.tests_run >= 0.8:
            print("\n✅ PRODUCTS API MOSTLY WORKING")
            print("⚠️ Some minor issues detected, but core functionality is working")
        else:
            print("\n⚠️ PRODUCTS API NEEDS ATTENTION")
            print("❌ Multiple issues detected with products endpoints")
        
        return self.tests_passed, self.tests_run

if __name__ == "__main__":
    print("🚀 Starting Products API Testing for Blank Page Issue...")
    print("=" * 80)
    
    # Focus on Products API testing
    products_tester = ProductsAPITester()
    products_passed, products_total = products_tester.run_all_products_tests()
    
    # Final Summary
    print("\n" + "=" * 100)
    print("🎯 PRODUCTS API TESTING - FINAL RESULTS")
    print("=" * 100)
    print(f"✅ Tests Passed: {products_passed}")
    print(f"❌ Tests Failed: {products_total - products_passed}")
    print(f"📊 Total Tests: {products_total}")
    print(f"📈 Success Rate: {(products_passed/products_total)*100:.1f}%")
    
    if products_passed == products_total:
        print("\n🎉 PRODUCTS API FULLY FUNCTIONAL!")
        print("✅ Backend products endpoints are working correctly")
        print("🔍 The blank Products page issue is likely in the frontend:")
        print("   - Check Products.js component for API call errors")
        print("   - Verify frontend is using correct API endpoint")
        print("   - Check browser console for JavaScript errors")
        print("   - Verify authentication token is being sent")
    elif products_passed / products_total >= 0.8:
        print("\n🌟 PRODUCTS API MOSTLY FUNCTIONAL")
        print("⚠️ Minor backend issues detected, check failed tests above")
    else:
        print("\n🚨 PRODUCTS API NEEDS IMMEDIATE ATTENTION")
        print("❌ Multiple critical backend issues detected")
    
    print("\n" + "=" * 100)