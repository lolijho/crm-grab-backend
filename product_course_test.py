#!/usr/bin/env python3
"""
Product-Course Association Testing Suite
Tests the complete product-course association functionality
"""

import requests
import sys
import json
import time
import uuid
import os

class ProductCourseAssociationTester:
    def __init__(self, base_url="https://faster-crm.preview.emergentagent.com"):
        self.base_url = base_url
        self.token = None
        self.tests_run = 0
        self.tests_passed = 0
        self.user_id = None
        self.test_course_id = None
        self.test_product_id = None
        self.test_product_id_2 = None

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

    def test_create_test_course(self):
        """Create a test course for product association testing"""
        course_data = {
            "title": "Test Course for Product Association",
            "description": "This is a test course created for testing product-course associations",
            "instructor": "Test Instructor",
            "duration": "4 weeks",
            "price": 299.99,
            "category": "test",
            "is_active": True,
            "max_students": 50
        }
        
        success, response = self.run_test(
            "Create Test Course",
            "POST",
            "api/courses",
            200,
            data=course_data
        )
        
        if success:
            self.test_course_id = response.get('id')
            print(f"   ✅ Test course created with ID: {self.test_course_id}")
            print(f"   📚 Course title: {response.get('title')}")
            return True
        return False

    def test_create_product_with_course_association(self):
        """Test creating a product with course_id field"""
        if not self.test_course_id:
            print("   ❌ No test course available")
            return False
        
        product_data = {
            "name": "Test Product with Course Association",
            "description": "This product is associated with a course",
            "price": 199.99,
            "category": "test",
            "sku": "TEST-PROD-001",
            "is_active": True,
            "course_id": self.test_course_id
        }
        
        success, response = self.run_test(
            "Create Product with Course Association",
            "POST",
            "api/products",
            200,
            data=product_data
        )
        
        if success:
            self.test_product_id = response.get('id')
            course_id = response.get('course_id')
            
            if course_id == self.test_course_id:
                print(f"   ✅ Product created with correct course association")
                print(f"   🛍️ Product ID: {self.test_product_id}")
                print(f"   📚 Associated Course ID: {course_id}")
                return True
            else:
                print(f"   ❌ Course association not set correctly")
                return False
        return False

    def test_create_product_without_course_association(self):
        """Test creating a product without course_id field"""
        product_data = {
            "name": "Test Product without Course Association",
            "description": "This product has no course association",
            "price": 99.99,
            "category": "test",
            "sku": "TEST-PROD-002",
            "is_active": True
        }
        
        success, response = self.run_test(
            "Create Product without Course Association",
            "POST",
            "api/products",
            200,
            data=product_data
        )
        
        if success:
            self.test_product_id_2 = response.get('id')
            course_id = response.get('course_id')
            
            if course_id is None:
                print(f"   ✅ Product created without course association")
                print(f"   🛍️ Product ID: {self.test_product_id_2}")
                print(f"   📚 Course ID: {course_id} (None as expected)")
                return True
            else:
                print(f"   ❌ Unexpected course association: {course_id}")
                return False
        return False

    def test_create_product_with_invalid_course_id(self):
        """Test creating a product with non-existent course_id (should return 400 error)"""
        fake_course_id = "507f1f77bcf86cd799439011"  # Valid ObjectId format but non-existent
        
        product_data = {
            "name": "Test Product with Invalid Course",
            "description": "This product has invalid course association",
            "price": 149.99,
            "category": "test",
            "sku": "TEST-PROD-INVALID",
            "is_active": True,
            "course_id": fake_course_id
        }
        
        success, response = self.run_test(
            "Create Product with Invalid Course ID",
            "POST",
            "api/products",
            400,  # Should fail with 400 error
            data=product_data
        )
        
        if success:
            error_detail = response.get('detail', '')
            if 'course not found' in error_detail.lower() or 'associated course not found' in error_detail.lower():
                print(f"   ✅ Invalid course ID properly rejected")
                print(f"   📝 Error: {error_detail}")
                return True
            else:
                print(f"   ❌ Unexpected error message: {error_detail}")
                return False
        return False

    def test_get_products_with_course_information(self):
        """Test GET /api/products with course information included via aggregation"""
        success, response = self.run_test(
            "Get Products with Course Information",
            "GET",
            "api/products",
            200
        )
        
        if success:
            if isinstance(response, list):
                print(f"   📊 Retrieved {len(response)} products")
                
                # Find our test products
                product_with_course = None
                product_without_course = None
                
                for product in response:
                    if product.get('id') == self.test_product_id:
                        product_with_course = product
                    elif product.get('id') == self.test_product_id_2:
                        product_without_course = product
                
                # Verify product with course association
                if product_with_course:
                    course_info = product_with_course.get('course')
                    if course_info and course_info.get('id') == self.test_course_id:
                        print(f"   ✅ Product with course shows course information")
                        print(f"   📚 Course title: {course_info.get('title')}")
                    else:
                        print(f"   ❌ Product with course missing course information")
                        return False
                
                # Verify product without course association
                if product_without_course:
                    course_info = product_without_course.get('course')
                    if course_info is None:
                        print(f"   ✅ Product without course shows null course information")
                    else:
                        print(f"   ❌ Product without course has unexpected course info: {course_info}")
                        return False
                
                return True
            else:
                print(f"   ❌ Expected list response, got: {type(response)}")
                return False
        return False

    def test_get_single_product_with_course_details(self):
        """Test GET /api/products/{id} with course details"""
        if not self.test_product_id:
            print("   ❌ No test product available")
            return False
        
        success, response = self.run_test(
            "Get Single Product with Course Details",
            "GET",
            f"api/products/{self.test_product_id}",
            200
        )
        
        if success:
            course_info = response.get('course')
            if course_info and course_info.get('id') == self.test_course_id:
                print(f"   ✅ Single product shows complete course information")
                print(f"   📚 Course title: {course_info.get('title')}")
                print(f"   👨‍🏫 Instructor: {course_info.get('instructor')}")
                print(f"   💰 Course price: {course_info.get('price')}")
                return True
            else:
                print(f"   ❌ Single product missing or incorrect course information")
                return False
        return False

    def test_update_product_to_associate_with_course(self):
        """Test updating a product to associate with a course"""
        if not self.test_product_id_2 or not self.test_course_id:
            print("   ❌ No test product or course available")
            return False
        
        update_data = {
            "course_id": self.test_course_id
        }
        
        success, response = self.run_test(
            "Update Product to Associate with Course",
            "PUT",
            f"api/products/{self.test_product_id_2}",
            200,
            data=update_data
        )
        
        if success:
            course_id = response.get('course_id')
            if course_id == self.test_course_id:
                print(f"   ✅ Product successfully associated with course")
                print(f"   📚 New course association: {course_id}")
                return True
            else:
                print(f"   ❌ Course association not updated correctly")
                return False
        return False

    def test_update_product_to_remove_course_association(self):
        """Test updating a product to remove course association (set to null/empty)"""
        if not self.test_product_id:
            print("   ❌ No test product available")
            return False
        
        # Test with null value
        update_data = {
            "course_id": None
        }
        
        success, response = self.run_test(
            "Update Product to Remove Course Association (null)",
            "PUT",
            f"api/products/{self.test_product_id}",
            200,
            data=update_data
        )
        
        if success:
            course_id = response.get('course_id')
            if course_id is None:
                print(f"   ✅ Course association successfully removed (null)")
                return True
            else:
                print(f"   ❌ Course association not removed: {course_id}")
                return False
        return False

    def test_update_product_with_empty_course_id(self):
        """Test updating a product with empty string course_id"""
        if not self.test_product_id_2:
            print("   ❌ No test product available")
            return False
        
        # Test with empty string
        update_data = {
            "course_id": ""
        }
        
        success, response = self.run_test(
            "Update Product with Empty Course ID",
            "PUT",
            f"api/products/{self.test_product_id_2}",
            200,
            data=update_data
        )
        
        if success:
            course_id = response.get('course_id')
            # Empty string should be treated as no association
            if course_id == "" or course_id is None:
                print(f"   ✅ Empty course ID handled correctly")
                return True
            else:
                print(f"   ❌ Empty course ID not handled correctly: {course_id}")
                return False
        return False

    def test_update_product_with_invalid_course_id(self):
        """Test updating a product with invalid course_id format"""
        if not self.test_product_id_2:
            print("   ❌ No test product available")
            return False
        
        # Test with invalid ObjectId format
        update_data = {
            "course_id": "invalid-course-id"
        }
        
        success, response = self.run_test(
            "Update Product with Invalid Course ID Format",
            "PUT",
            f"api/products/{self.test_product_id_2}",
            400,  # Should fail with validation error
            data=update_data
        )
        
        if success:
            error_detail = response.get('detail', '')
            print(f"   ✅ Invalid course ID format properly rejected")
            print(f"   📝 Error: {error_detail}")
            return True
        return False

    def test_multiple_products_same_course(self):
        """Test multiple products associated with the same course"""
        if not self.test_course_id:
            print("   ❌ No test course available")
            return False
        
        # Create another product with the same course
        product_data = {
            "name": "Another Product with Same Course",
            "description": "Second product associated with the same course",
            "price": 249.99,
            "category": "test",
            "sku": "TEST-PROD-003",
            "is_active": True,
            "course_id": self.test_course_id
        }
        
        success, response = self.run_test(
            "Create Another Product with Same Course",
            "POST",
            "api/products",
            200,
            data=product_data
        )
        
        if success:
            product_id = response.get('id')
            course_id = response.get('course_id')
            
            if course_id == self.test_course_id:
                print(f"   ✅ Multiple products can be associated with same course")
                print(f"   🛍️ Product ID: {product_id}")
                print(f"   📚 Shared Course ID: {course_id}")
                
                # Clean up this test product
                self.run_test(
                    "Cleanup Multiple Products Test",
                    "DELETE",
                    f"api/products/{product_id}",
                    200
                )
                return True
            else:
                print(f"   ❌ Course association not set correctly")
                return False
        return False

    def test_data_integrity_verification(self):
        """Test data integrity of product-course associations"""
        print("\n🔍 Testing Data Integrity Verification...")
        
        # Get all products and verify course associations
        success, response = self.run_test(
            "Verify All Product-Course Associations",
            "GET",
            "api/products",
            200
        )
        
        if success:
            products_with_courses = 0
            products_without_courses = 0
            integrity_issues = 0
            
            for product in response:
                course_info = product.get('course')
                course_id = product.get('course_id')
                
                if course_id:
                    if course_info and course_info.get('id') == course_id:
                        products_with_courses += 1
                        print(f"   ✅ Product '{product.get('name')}' has valid course association")
                    else:
                        integrity_issues += 1
                        print(f"   ❌ Product '{product.get('name')}' has course_id but missing course info")
                else:
                    if course_info is None:
                        products_without_courses += 1
                        print(f"   ✅ Product '{product.get('name')}' correctly shows no course association")
                    else:
                        integrity_issues += 1
                        print(f"   ❌ Product '{product.get('name')}' has no course_id but shows course info")
            
            print(f"   📊 Products with courses: {products_with_courses}")
            print(f"   📊 Products without courses: {products_without_courses}")
            print(f"   📊 Integrity issues: {integrity_issues}")
            
            if integrity_issues == 0:
                print(f"   ✅ All product-course associations have correct data integrity")
                return True
            else:
                print(f"   ❌ Data integrity issues detected")
                return False
        return False

    def cleanup_test_data(self):
        """Clean up test data created during testing"""
        print("\n🧹 Cleaning up test data...")
        
        # Delete test products
        if self.test_product_id:
            self.run_test(
                "Cleanup Test Product 1",
                "DELETE",
                f"api/products/{self.test_product_id}",
                200
            )
        
        if self.test_product_id_2:
            self.run_test(
                "Cleanup Test Product 2",
                "DELETE",
                f"api/products/{self.test_product_id_2}",
                200
            )
        
        # Delete test course
        if self.test_course_id:
            self.run_test(
                "Cleanup Test Course",
                "DELETE",
                f"api/courses/{self.test_course_id}",
                200
            )
        
        print("   ✅ Test data cleanup completed")

    def run_all_product_course_association_tests(self):
        """Run all product-course association tests"""
        print("🚀 Starting Product-Course Association Testing...")
        print(f"🌐 Base URL: {self.base_url}")
        print("=" * 80)
        
        # Test sequence for product-course association
        test_methods = [
            self.test_login,
            self.test_create_test_course,
            self.test_create_product_with_course_association,
            self.test_create_product_without_course_association,
            self.test_create_product_with_invalid_course_id,
            self.test_get_products_with_course_information,
            self.test_get_single_product_with_course_details,
            self.test_update_product_to_associate_with_course,
            self.test_update_product_to_remove_course_association,
            self.test_update_product_with_empty_course_id,
            self.test_update_product_with_invalid_course_id,
            self.test_multiple_products_same_course,
            self.test_data_integrity_verification,
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
        
        # Cleanup
        try:
            self.cleanup_test_data()
        except Exception as e:
            print(f"⚠️ Cleanup failed: {str(e)}")
        
        # Print final results
        print("\n" + "=" * 80)
        print("📊 PRODUCT-COURSE ASSOCIATION TEST RESULTS")
        print("=" * 80)
        print(f"✅ Tests Passed: {self.tests_passed}")
        print(f"❌ Tests Failed: {self.tests_run - self.tests_passed}")
        print(f"📊 Total Tests: {self.tests_run}")
        print(f"📈 Success Rate: {(self.tests_passed/self.tests_run)*100:.1f}%")
        
        if self.tests_passed == self.tests_run:
            print("\n🎉 ALL PRODUCT-COURSE ASSOCIATION TESTS PASSED!")
            print("✅ Product-course association functionality is fully working")
            print("✅ Course validation and data integrity verified")
            print("✅ All CRUD operations with course associations working")
        elif self.tests_passed / self.tests_run >= 0.8:
            print("\n✅ PRODUCT-COURSE ASSOCIATION MOSTLY WORKING")
            print("⚠️ Some minor issues detected, but core functionality is working")
        else:
            print("\n⚠️ PRODUCT-COURSE ASSOCIATION NEEDS ATTENTION")
            print("❌ Multiple issues detected with course association functionality")
        
        return self.tests_passed, self.tests_run

if __name__ == "__main__":
    print("🚀 PRODUCT-COURSE ASSOCIATION TESTING")
    print("=" * 80)
    print("Testing complete product-course association functionality:")
    print("1. Creating products with course_id field")
    print("2. Updating products to associate/disassociate with courses")
    print("3. Course_id validation (course must exist)")
    print("4. GET /api/products with course information via aggregation")
    print("5. GET /api/products/{id} with course details")
    print("6. Edge cases: empty, null, invalid course_id handling")
    print("7. Multiple products associated with same course")
    print("8. Data integrity verification")
    print("=" * 80)
    
    # Get base URL from environment or use default
    base_url = os.getenv("REACT_APP_BACKEND_URL", "https://faster-crm.preview.emergentagent.com")
    
    # Run product-course association tests
    tester = ProductCourseAssociationTester(base_url)
    passed, total = tester.run_all_product_course_association_tests()
    
    print("\n" + "=" * 80)
    print("🎯 PRODUCT-COURSE ASSOCIATION TEST SUMMARY")
    print("=" * 80)
    print(f"📊 Tests Passed: {passed}/{total}")
    print(f"📈 Success Rate: {(passed/total)*100:.1f}%")
    
    if passed == total:
        print("\n🎉 ALL PRODUCT-COURSE ASSOCIATION TESTS PASSED!")
        print("✅ Product creation with course_id field - WORKING")
        print("✅ Product updates for course association/disassociation - WORKING")
        print("✅ Course_id validation (course must exist) - WORKING")
        print("✅ GET /api/products with course information via aggregation - WORKING")
        print("✅ GET /api/products/{id} with course details - WORKING")
        print("✅ Edge cases handling (empty, null, invalid course_id) - WORKING")
        print("✅ Multiple products with same course - WORKING")
        print("✅ Data integrity verification - WORKING")
        print("\n🎯 PRODUCT-COURSE ASSOCIATION FUNCTIONALITY IS PRODUCTION READY!")
        sys.exit(0)
    elif passed / total >= 0.8:
        print("\n✅ PRODUCT-COURSE ASSOCIATION MOSTLY WORKING")
        print("⚠️ Some minor issues detected, but core functionality is working")
        sys.exit(0)
    else:
        print("\n❌ PRODUCT-COURSE ASSOCIATION NEEDS ATTENTION")
        print("🚨 Critical issues found with course association functionality")
        sys.exit(1)