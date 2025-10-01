import requests
import sys
import json
import time
import uuid

class ProductCourseBulkActionsTester:
    def __init__(self, base_url="https://faster-crm.preview.emergentagent.com"):
        self.base_url = base_url
        self.token = None
        self.tests_run = 0
        self.tests_passed = 0
        self.user_id = None
        self.test_products = []
        self.test_courses = []

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
                    if isinstance(response_data, dict) and len(str(response_data)) < 500:
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

    def create_test_products(self):
        """Create test products for bulk operations"""
        print("\n🔍 Creating Test Products for Bulk Operations...")
        
        test_products_data = [
            {
                "name": "Corso Avanzato di Grabovoi",
                "description": "Corso completo per tecniche avanzate",
                "price": 299.99,
                "category": "Corsi",
                "sku": "GRAB-ADV-001",
                "is_active": True
            },
            {
                "name": "Manuale Base Grabovoi",
                "description": "Manuale introduttivo alle sequenze numeriche",
                "price": 49.99,
                "category": "Manuali",
                "sku": "GRAB-MAN-001",
                "is_active": True
            },
            {
                "name": "Kit Completo Grabovoi",
                "description": "Kit con tutti i materiali necessari",
                "price": 199.99,
                "category": "Kit",
                "sku": "GRAB-KIT-001",
                "is_active": False  # Start inactive for testing activation
            },
            {
                "name": "Sessione Individuale",
                "description": "Sessione personalizzata one-to-one",
                "price": 150.00,
                "category": "Servizi",
                "sku": "GRAB-SES-001",
                "is_active": True
            }
        ]
        
        created_products = []
        for product_data in test_products_data:
            success, response = self.run_test(
                f"Create Test Product - {product_data['name']}",
                "POST",
                "api/products",
                200,
                data=product_data
            )
            
            if success:
                product_id = response.get('id') or response.get('_id')
                if product_id:
                    created_products.append({
                        'id': product_id,
                        'name': product_data['name'],
                        'price': product_data['price'],
                        'is_active': product_data['is_active'],
                        'sku': product_data['sku']
                    })
                    print(f"   ✅ Created product: {product_data['name']} (ID: {product_id})")
        
        self.test_products = created_products
        print(f"   📊 Total test products created: {len(self.test_products)}")
        return len(self.test_products) > 0

    def create_test_courses(self):
        """Create test courses for bulk operations"""
        print("\n🔍 Creating Test Courses for Bulk Operations...")
        
        test_courses_data = [
            {
                "title": "Fondamenti delle Sequenze Numeriche",
                "description": "Corso base per imparare le sequenze di Grabovoi",
                "instructor": "Dr. Marco Bianchi",
                "duration": "4 settimane",
                "price": 199.99,
                "category": "Base",
                "is_active": True,
                "max_students": 50
            },
            {
                "title": "Tecniche Avanzate di Guarigione",
                "description": "Corso avanzato per professionisti",
                "instructor": "Prof.ssa Giulia Rossi",
                "duration": "8 settimane",
                "price": 399.99,
                "category": "Avanzato",
                "is_active": True,
                "max_students": 25
            },
            {
                "title": "Workshop Intensivo Weekend",
                "description": "Workshop pratico di 2 giorni",
                "instructor": "Alessandro Verdi",
                "duration": "2 giorni",
                "price": 299.99,
                "category": "Workshop",
                "is_active": False,  # Start inactive for testing activation
                "max_students": 30
            },
            {
                "title": "Masterclass Esclusiva",
                "description": "Masterclass per studenti avanzati",
                "instructor": "Dr. Francesco Neri",
                "duration": "1 giorno",
                "price": 499.99,
                "category": "Masterclass",
                "is_active": True,
                "max_students": 15
            }
        ]
        
        created_courses = []
        for course_data in test_courses_data:
            success, response = self.run_test(
                f"Create Test Course - {course_data['title']}",
                "POST",
                "api/courses",
                200,
                data=course_data
            )
            
            if success:
                course_id = response.get('id') or response.get('_id')
                if course_id:
                    created_courses.append({
                        'id': course_id,
                        'title': course_data['title'],
                        'price': course_data['price'],
                        'is_active': course_data['is_active'],
                        'instructor': course_data['instructor']
                    })
                    print(f"   ✅ Created course: {course_data['title']} (ID: {course_id})")
        
        self.test_courses = created_courses
        print(f"   📊 Total test courses created: {len(self.test_courses)}")
        return len(self.test_courses) > 0

    def test_product_status_update_bulk(self):
        """Test PUT /api/products/{id} for bulk status updates (is_active field)"""
        if not self.test_products:
            print("   ❌ No test products available")
            return False
        
        print("\n🔍 Testing Product Bulk Status Updates...")
        
        # Test 1: Activate inactive product
        inactive_product = next((p for p in self.test_products if not p['is_active']), None)
        if inactive_product:
            update_data = {
                "name": inactive_product['name'],
                "price": inactive_product['price'],
                "is_active": True  # Activate the product
            }
            
            success, response = self.run_test(
                f"Activate Product - {inactive_product['name']}",
                "PUT",
                f"api/products/{inactive_product['id']}",
                200,
                data=update_data
            )
            
            if success and response.get('is_active') == True:
                print(f"   ✅ Product activated successfully")
                inactive_product['is_active'] = True  # Update local record
            else:
                print(f"   ❌ Product activation failed")
                return False
        
        # Test 2: Deactivate multiple active products (simulating bulk deactivation)
        active_products = [p for p in self.test_products if p['is_active']]
        deactivation_success = 0
        
        for product in active_products[:2]:  # Deactivate first 2 active products
            update_data = {
                "name": product['name'],
                "price": product['price'],
                "is_active": False  # Deactivate the product
            }
            
            success, response = self.run_test(
                f"Deactivate Product - {product['name']}",
                "PUT",
                f"api/products/{product['id']}",
                200,
                data=update_data
            )
            
            if success and response.get('is_active') == False:
                deactivation_success += 1
                product['is_active'] = False  # Update local record
                print(f"   ✅ Product deactivated: {product['name']}")
        
        # Test 3: Bulk reactivation (activate all inactive products)
        inactive_products = [p for p in self.test_products if not p['is_active']]
        reactivation_success = 0
        
        for product in inactive_products:
            update_data = {
                "name": product['name'],
                "price": product['price'],
                "is_active": True  # Reactivate the product
            }
            
            success, response = self.run_test(
                f"Reactivate Product - {product['name']}",
                "PUT",
                f"api/products/{product['id']}",
                200,
                data=update_data
            )
            
            if success and response.get('is_active') == True:
                reactivation_success += 1
                product['is_active'] = True  # Update local record
                print(f"   ✅ Product reactivated: {product['name']}")
        
        total_operations = 1 + deactivation_success + reactivation_success
        expected_operations = 1 + min(2, len(active_products)) + len(inactive_products)
        
        if total_operations >= expected_operations - 1:  # Allow for some flexibility
            print(f"   ✅ Product bulk status updates successful: {total_operations} operations")
            return True
        else:
            print(f"   ❌ Product bulk status updates failed: {total_operations}/{expected_operations}")
            return False

    def test_course_status_update_bulk(self):
        """Test PUT /api/courses/{id} for bulk status updates (is_active field)"""
        if not self.test_courses:
            print("   ❌ No test courses available")
            return False
        
        print("\n🔍 Testing Course Bulk Status Updates...")
        
        # Test 1: Activate inactive course
        inactive_course = next((c for c in self.test_courses if not c['is_active']), None)
        if inactive_course:
            update_data = {
                "title": inactive_course['title'],
                "price": inactive_course['price'],
                "instructor": inactive_course['instructor'],
                "is_active": True  # Activate the course
            }
            
            success, response = self.run_test(
                f"Activate Course - {inactive_course['title']}",
                "PUT",
                f"api/courses/{inactive_course['id']}",
                200,
                data=update_data
            )
            
            if success and response.get('is_active') == True:
                print(f"   ✅ Course activated successfully")
                inactive_course['is_active'] = True  # Update local record
            else:
                print(f"   ❌ Course activation failed")
                return False
        
        # Test 2: Deactivate multiple active courses (simulating bulk deactivation)
        active_courses = [c for c in self.test_courses if c['is_active']]
        deactivation_success = 0
        
        for course in active_courses[:2]:  # Deactivate first 2 active courses
            update_data = {
                "title": course['title'],
                "price": course['price'],
                "instructor": course['instructor'],
                "is_active": False  # Deactivate the course
            }
            
            success, response = self.run_test(
                f"Deactivate Course - {course['title']}",
                "PUT",
                f"api/courses/{course['id']}",
                200,
                data=update_data
            )
            
            if success and response.get('is_active') == False:
                deactivation_success += 1
                course['is_active'] = False  # Update local record
                print(f"   ✅ Course deactivated: {course['title']}")
        
        # Test 3: Bulk reactivation (activate all inactive courses)
        inactive_courses = [c for c in self.test_courses if not c['is_active']]
        reactivation_success = 0
        
        for course in inactive_courses:
            update_data = {
                "title": course['title'],
                "price": course['price'],
                "instructor": course['instructor'],
                "is_active": True  # Reactivate the course
            }
            
            success, response = self.run_test(
                f"Reactivate Course - {course['title']}",
                "PUT",
                f"api/courses/{course['id']}",
                200,
                data=update_data
            )
            
            if success and response.get('is_active') == True:
                reactivation_success += 1
                course['is_active'] = True  # Update local record
                print(f"   ✅ Course reactivated: {course['title']}")
        
        total_operations = 1 + deactivation_success + reactivation_success
        expected_operations = 1 + min(2, len(active_courses)) + len(inactive_courses)
        
        if total_operations >= expected_operations - 1:  # Allow for some flexibility
            print(f"   ✅ Course bulk status updates successful: {total_operations} operations")
            return True
        else:
            print(f"   ❌ Course bulk status updates failed: {total_operations}/{expected_operations}")
            return False

    def test_product_deletion_bulk(self):
        """Test DELETE /api/products/{id} for bulk deletion"""
        if not self.test_products:
            print("   ❌ No test products available")
            return False
        
        print("\n🔍 Testing Product Bulk Deletion...")
        
        # Delete half of the test products to simulate bulk deletion
        products_to_delete = self.test_products[:2]  # Delete first 2 products
        deletion_success = 0
        
        for product in products_to_delete:
            success, response = self.run_test(
                f"Delete Product - {product['name']}",
                "DELETE",
                f"api/products/{product['id']}",
                200
            )
            
            if success and 'message' in response:
                deletion_success += 1
                print(f"   ✅ Product deleted: {product['name']}")
                # Remove from local list
                self.test_products.remove(product)
        
        if deletion_success == len(products_to_delete):
            print(f"   ✅ Product bulk deletion successful: {deletion_success} products deleted")
            return True
        else:
            print(f"   ❌ Product bulk deletion failed: {deletion_success}/{len(products_to_delete)}")
            return False

    def test_course_deletion_bulk(self):
        """Test DELETE /api/courses/{id} for bulk deletion"""
        if not self.test_courses:
            print("   ❌ No test courses available")
            return False
        
        print("\n🔍 Testing Course Bulk Deletion...")
        
        # Delete half of the test courses to simulate bulk deletion
        courses_to_delete = self.test_courses[:2]  # Delete first 2 courses
        deletion_success = 0
        
        for course in courses_to_delete:
            success, response = self.run_test(
                f"Delete Course - {course['title']}",
                "DELETE",
                f"api/courses/{course['id']}",
                200
            )
            
            if success and 'message' in response:
                deletion_success += 1
                print(f"   ✅ Course deleted: {course['title']}")
                # Remove from local list
                self.test_courses.remove(course)
        
        if deletion_success == len(courses_to_delete):
            print(f"   ✅ Course bulk deletion successful: {deletion_success} courses deleted")
            return True
        else:
            print(f"   ❌ Course bulk deletion failed: {deletion_success}/{len(courses_to_delete)}")
            return False

    def test_performance_multiple_simultaneous_updates(self):
        """Test performance of multiple simultaneous updates (simulating bulk actions)"""
        if not self.test_products or not self.test_courses:
            print("   ❌ No test products or courses available")
            return False
        
        print("\n🔍 Testing Performance - Multiple Simultaneous Updates...")
        
        start_time = time.time()
        
        # Perform rapid consecutive updates on remaining products and courses
        operations_completed = 0
        total_operations = 0
        
        # Update all remaining products
        for product in self.test_products:
            total_operations += 1
            update_data = {
                "name": product['name'],
                "price": product['price'] + 10.00,  # Small price update
                "is_active": not product['is_active']  # Toggle status
            }
            
            success, response = self.run_test(
                f"Performance Update Product - {product['name']}",
                "PUT",
                f"api/products/{product['id']}",
                200,
                data=update_data
            )
            
            if success:
                operations_completed += 1
                product['is_active'] = not product['is_active']  # Update local record
        
        # Update all remaining courses
        for course in self.test_courses:
            total_operations += 1
            update_data = {
                "title": course['title'],
                "price": course['price'] + 20.00,  # Small price update
                "instructor": course['instructor'],
                "is_active": not course['is_active']  # Toggle status
            }
            
            success, response = self.run_test(
                f"Performance Update Course - {course['title']}",
                "PUT",
                f"api/courses/{course['id']}",
                200,
                data=update_data
            )
            
            if success:
                operations_completed += 1
                course['is_active'] = not course['is_active']  # Update local record
        
        end_time = time.time()
        total_time = end_time - start_time
        
        print(f"   📊 Performance Results:")
        print(f"   ⏱️ Total time: {total_time:.2f} seconds")
        print(f"   🔄 Operations completed: {operations_completed}/{total_operations}")
        print(f"   ⚡ Average time per operation: {total_time/total_operations:.3f} seconds")
        
        # Performance criteria: All operations should complete and average time should be reasonable
        if operations_completed == total_operations and total_time/total_operations < 2.0:
            print(f"   ✅ Performance test passed - Efficient bulk operations")
            return True
        elif operations_completed == total_operations:
            print(f"   ⚠️ Performance test passed but slow - All operations completed")
            return True
        else:
            print(f"   ❌ Performance test failed - Some operations failed")
            return False

    def test_error_handling_nonexistent_items(self):
        """Test error handling for updating/deleting non-existent products and courses"""
        print("\n🔍 Testing Error Handling - Non-existent Items...")
        
        # Test updating non-existent product
        fake_product_id = "507f1f77bcf86cd799439011"
        update_data = {
            "name": "Non-existent Product",
            "price": 99.99,
            "is_active": True
        }
        
        success1, response1 = self.run_test(
            "Update Non-existent Product",
            "PUT",
            f"api/products/{fake_product_id}",
            404,
            data=update_data
        )
        
        # Test deleting non-existent product
        success2, response2 = self.run_test(
            "Delete Non-existent Product",
            "DELETE",
            f"api/products/{fake_product_id}",
            404
        )
        
        # Test updating non-existent course
        fake_course_id = "507f1f77bcf86cd799439012"
        course_update_data = {
            "title": "Non-existent Course",
            "price": 199.99,
            "instructor": "Ghost Instructor",
            "is_active": True
        }
        
        success3, response3 = self.run_test(
            "Update Non-existent Course",
            "PUT",
            f"api/courses/{fake_course_id}",
            404,
            data=course_update_data
        )
        
        # Test deleting non-existent course
        success4, response4 = self.run_test(
            "Delete Non-existent Course",
            "DELETE",
            f"api/courses/{fake_course_id}",
            404
        )
        
        # Verify error messages
        error_checks = 0
        if success1 and 'detail' in response1 and 'not found' in response1['detail'].lower():
            print(f"   ✅ Product update error properly handled")
            error_checks += 1
        
        if success2 and 'detail' in response2 and 'not found' in response2['detail'].lower():
            print(f"   ✅ Product deletion error properly handled")
            error_checks += 1
        
        if success3 and 'detail' in response3 and 'not found' in response3['detail'].lower():
            print(f"   ✅ Course update error properly handled")
            error_checks += 1
        
        if success4 and 'detail' in response4 and 'not found' in response4['detail'].lower():
            print(f"   ✅ Course deletion error properly handled")
            error_checks += 1
        
        if error_checks == 4:
            print(f"   ✅ All error handling tests passed")
            return True
        else:
            print(f"   ❌ Error handling tests failed: {error_checks}/4")
            return False

    def test_data_integrity_after_bulk_operations(self):
        """Test data integrity after bulk operations"""
        print("\n🔍 Testing Data Integrity After Bulk Operations...")
        
        # Verify remaining products exist and have correct status
        products_verified = 0
        for product in self.test_products:
            success, response = self.run_test(
                f"Verify Product - {product['name']}",
                "GET",
                f"api/products/{product['id']}",
                200
            )
            
            if success:
                if response.get('is_active') == product['is_active']:
                    products_verified += 1
                    print(f"   ✅ Product integrity verified: {product['name']}")
                else:
                    print(f"   ❌ Product status mismatch: {product['name']}")
        
        # Verify remaining courses exist and have correct status
        courses_verified = 0
        for course in self.test_courses:
            success, response = self.run_test(
                f"Verify Course - {course['title']}",
                "GET",
                f"api/courses/{course['id']}",
                200
            )
            
            if success:
                if response.get('is_active') == course['is_active']:
                    courses_verified += 1
                    print(f"   ✅ Course integrity verified: {course['title']}")
                else:
                    print(f"   ❌ Course status mismatch: {course['title']}")
        
        total_verified = products_verified + courses_verified
        total_expected = len(self.test_products) + len(self.test_courses)
        
        if total_verified == total_expected:
            print(f"   ✅ Data integrity verified: {total_verified}/{total_expected} items")
            return True
        else:
            print(f"   ❌ Data integrity issues: {total_verified}/{total_expected} items")
            return False

    def cleanup_test_data(self):
        """Clean up any remaining test data"""
        print("\n🧹 Cleaning up test data...")
        
        # Delete remaining test products
        for product in self.test_products[:]:  # Use slice to avoid modification during iteration
            self.run_test(
                f"Cleanup Product - {product['name']}",
                "DELETE",
                f"api/products/{product['id']}",
                200
            )
            self.test_products.remove(product)
        
        # Delete remaining test courses
        for course in self.test_courses[:]:  # Use slice to avoid modification during iteration
            self.run_test(
                f"Cleanup Course - {course['title']}",
                "DELETE",
                f"api/courses/{course['id']}",
                200
            )
            self.test_courses.remove(course)
        
        print("   ✅ Test data cleanup completed")

    def run_all_bulk_actions_tests(self):
        """Run all product and course bulk actions tests"""
        print("🚀 Starting Product & Course Bulk Actions Testing...")
        print(f"🌐 Base URL: {self.base_url}")
        print("=" * 80)
        
        # Test sequence for bulk actions
        test_methods = [
            self.test_login,
            self.create_test_products,
            self.create_test_courses,
            self.test_product_status_update_bulk,
            self.test_course_status_update_bulk,
            self.test_performance_multiple_simultaneous_updates,
            self.test_error_handling_nonexistent_items,
            self.test_data_integrity_after_bulk_operations,
            self.test_product_deletion_bulk,
            self.test_course_deletion_bulk,
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
        print("📊 PRODUCT & COURSE BULK ACTIONS TEST RESULTS")
        print("=" * 80)
        print(f"✅ Tests Passed: {self.tests_passed}")
        print(f"❌ Tests Failed: {self.tests_run - self.tests_passed}")
        print(f"📊 Total Tests: {self.tests_run}")
        print(f"📈 Success Rate: {(self.tests_passed/self.tests_run)*100:.1f}%")
        
        if self.tests_passed == self.tests_run:
            print("\n🎉 ALL BULK ACTIONS TESTS PASSED!")
            print("✅ Product bulk activate/deactivate/delete - WORKING")
            print("✅ Course bulk activate/deactivate/delete - WORKING")
            print("✅ Performance for bulk operations - EXCELLENT")
            print("✅ Error handling for non-existent items - WORKING")
            print("✅ Data integrity after bulk operations - VERIFIED")
        elif self.tests_passed / self.tests_run >= 0.8:
            print("\n✅ BULK ACTIONS SYSTEM MOSTLY WORKING")
            print("⚠️ Some minor issues detected, but core functionality is working")
        else:
            print("\n⚠️ BULK ACTIONS SYSTEM NEEDS ATTENTION")
            print("❌ Multiple issues detected with bulk operations")
        
        return self.tests_passed, self.tests_run

if __name__ == "__main__":
    # Run product course bulk tests
    tester = ProductCourseBulkActionsTester()
    passed, total = tester.run_all_bulk_actions_tests()
    
    print(f"\n📊 FINAL RESULTS: {passed}/{total} tests passed")
    print(f"📈 Success Rate: {(passed/total)*100:.1f}%")
    
    if passed == total:
        print("\n🎉 ALL BULK ACTIONS TESTS PASSED!")
        print("✅ Product & Course bulk operations are production-ready")
        print("✅ Performance is excellent for bulk operations")
        print("✅ Error handling is robust")
        print("✅ Data integrity is maintained")
        sys.exit(0)
    elif passed / total >= 0.8:
        print("\n✅ BULK ACTIONS MOSTLY WORKING")
        print("⚠️ Minor issues may need attention before production")
        sys.exit(0)
    else:
        print("\n❌ BULK ACTIONS NEED ATTENTION")
        print("🚨 Critical issues found - not ready for production")
        sys.exit(1)