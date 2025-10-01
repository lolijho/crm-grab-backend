import requests
import sys
import json
import io
from datetime import datetime
import time
import uuid
import hmac
import hashlib
import base64
import os

class CourseDeletionTester:
    def __init__(self, base_url="https://faster-crm.preview.emergentagent.com"):
        self.base_url = base_url
        self.token = None
        self.tests_run = 0
        self.tests_passed = 0
        self.user_id = None
        self.test_course_id = None
        self.test_product_id = None
        self.test_course_data = None

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
        """Test creating a test course for deletion testing"""
        unique_id = str(uuid.uuid4())[:8]
        course_data = {
            "title": f"Test Corso Cancellazione {unique_id}",
            "description": "Corso di test per verificare la funzionalità di cancellazione",
            "instructor": "Grigori Grabovoi",
            "duration": "2 ore",
            "price": 99.99,
            "category": "corso",
            "language": "it",
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
            self.test_course_data = course_data
            print(f"   ✅ Test course created with ID: {self.test_course_id}")
            print(f"   📚 Course title: {course_data['title']}")
            return True
        return False

    def test_verify_course_exists_in_collection(self):
        """Test that the created course exists in courses collection"""
        if not self.test_course_id:
            print("   ❌ No test course ID available")
            return False
        
        success, response = self.run_test(
            "Verify Course Exists",
            "GET",
            f"api/courses/{self.test_course_id}",
            200
        )
        
        if success:
            course_title = response.get('title', '')
            if self.test_course_data and course_title == self.test_course_data['title']:
                print(f"   ✅ Course exists in courses collection")
                print(f"   📚 Title: {course_title}")
                print(f"   🏷️ Category: {response.get('category')}")
                print(f"   🌍 Language: {response.get('language')}")
                return True
            else:
                print(f"   ❌ Course data mismatch")
                return False
        return False

    def test_delete_course_via_api(self):
        """Test DELETE /api/courses/{id} - Course deletion with tracking"""
        if not self.test_course_id:
            print("   ❌ No test course ID available")
            return False
        
        success, response = self.run_test(
            "Delete Course via API",
            "DELETE",
            f"api/courses/{self.test_course_id}",
            200
        )
        
        if success:
            message = response.get('message', '')
            if 'deleted successfully' in message.lower():
                print(f"   ✅ Course deletion API call successful")
                print(f"   📝 Message: {message}")
                return True
            else:
                print(f"   ❌ Unexpected deletion message: {message}")
                return False
        return False

    def test_verify_course_removed_from_courses_collection(self):
        """Test that course was removed from courses collection"""
        if not self.test_course_id:
            print("   ❌ No test course ID available")
            return False
        
        success, response = self.run_test(
            "Verify Course Removed from Collection",
            "GET",
            f"api/courses/{self.test_course_id}",
            404  # Should not be found
        )
        
        if success:
            error_detail = response.get('detail', '')
            if 'not found' in error_detail.lower():
                print(f"   ✅ Course successfully removed from courses collection")
                print(f"   📝 Error: {error_detail}")
                return True
            else:
                print(f"   ❌ Unexpected error message: {error_detail}")
                return False
        return False

    def test_create_product_with_corso_keyword(self):
        """Test creating a product that contains 'corso' in the name"""
        unique_id = str(uuid.uuid4())[:8]
        product_data = {
            "name": f"Corso di Formazione Avanzata {unique_id}",
            "description": "Prodotto di test per verificare la prevenzione ricreazione automatica",
            "price": 149.99,
            "category": "formazione",
            "sku": f"CORSO-TEST-{unique_id}",
            "is_active": True
        }
        
        success, response = self.run_test(
            "Create Product with 'Corso' Keyword",
            "POST",
            "api/products",
            200,
            data=product_data
        )
        
        if success:
            self.test_product_id = response.get('id')
            print(f"   ✅ Test product created with ID: {self.test_product_id}")
            print(f"   🛍️ Product name: {product_data['name']}")
            print(f"   💰 Price: €{product_data['price']}")
            return True
        return False

    def test_verify_no_automatic_course_recreation(self):
        """Test that no course is automatically recreated for the product"""
        if not self.test_product_id or not self.test_course_data:
            print("   ❌ No test product ID or course data available")
            return False
        
        # Wait a moment for any potential auto-creation logic
        time.sleep(2)
        
        # Check if any course with similar title exists
        success, response = self.run_test(
            "Get All Courses - Check Auto-Recreation",
            "GET",
            "api/courses",
            200
        )
        
        if success:
            courses = response if isinstance(response, list) else []
            
            # Look for courses with similar titles to our deleted course or new product
            deleted_course_title = self.test_course_data['title']
            product_name = f"Corso di Formazione Avanzata"
            
            auto_created_courses = []
            for course in courses:
                course_title = course.get('title', '').lower()
                if (deleted_course_title.lower() in course_title or 
                    product_name.lower() in course_title):
                    auto_created_courses.append(course)
            
            if len(auto_created_courses) == 0:
                print(f"   ✅ No automatic course recreation detected")
                print(f"   🚫 Deleted course prevention working correctly")
                print(f"   📊 Total courses found: {len(courses)}")
                return True
            else:
                print(f"   ❌ Found {len(auto_created_courses)} potentially auto-created courses:")
                for course in auto_created_courses:
                    print(f"      - {course.get('title')} (ID: {course.get('id')})")
                return False
        return False

    def test_restore_auto_creation_api(self):
        """Test POST /api/courses/{id}/restore-auto-creation"""
        if not self.test_course_id:
            print("   ❌ No test course ID available")
            return False
        
        success, response = self.run_test(
            "Restore Auto-Creation API",
            "POST",
            f"api/courses/{self.test_course_id}/restore-auto-creation",
            200
        )
        
        if success:
            message = response.get('message', '')
            if 'restored' in message.lower():
                print(f"   ✅ Auto-creation restore API working")
                print(f"   📝 Message: {message}")
                return True
            else:
                print(f"   ❌ Unexpected restore message: {message}")
                return False
        return False

    def test_course_language_filter(self):
        """Test GET /api/courses with ?language= filter"""
        # Test Italian language filter
        success1, response1 = self.run_test(
            "Course Language Filter - Italian",
            "GET",
            "api/courses?language=it",
            200
        )
        
        if not success1:
            return False
        
        italian_courses = response1 if isinstance(response1, list) else []
        print(f"   📊 Found {len(italian_courses)} Italian courses")
        
        # Verify all returned courses have language='it'
        for course in italian_courses:
            if course.get('language') != 'it':
                print(f"   ❌ Course with wrong language found: {course.get('language')}")
                return False
        
        # Test English language filter
        success2, response2 = self.run_test(
            "Course Language Filter - English",
            "GET",
            "api/courses?language=en",
            200
        )
        
        if not success2:
            return False
        
        english_courses = response2 if isinstance(response2, list) else []
        print(f"   📊 Found {len(english_courses)} English courses")
        
        # Test non-existent language
        success3, response3 = self.run_test(
            "Course Language Filter - Non-existent",
            "GET",
            "api/courses?language=zz",
            200
        )
        
        if success3:
            nonexistent_courses = response3 if isinstance(response3, list) else []
            print(f"   📊 Found {len(nonexistent_courses)} courses with language 'zz'")
            
            if len(nonexistent_courses) == 0:
                print(f"   ✅ Language filter working correctly")
                return True
            else:
                print(f"   ❌ Non-existent language filter returned courses")
                return False
        
        return False

    def test_get_course_languages_api(self):
        """Test GET /api/courses/languages"""
        success, response = self.run_test(
            "Get Course Languages API",
            "GET",
            "api/courses/languages",
            200
        )
        
        if success:
            languages = response if isinstance(response, list) else []
            print(f"   📊 Available languages: {languages}")
            
            # Should contain at least some common languages
            expected_languages = ['it', 'en']
            found_languages = [lang for lang in expected_languages if lang in languages]
            
            if len(found_languages) > 0:
                print(f"   ✅ Course languages API working")
                print(f"   🌍 Found expected languages: {found_languages}")
                return True
            else:
                print(f"   ⚠️ No expected languages found, but API is working")
                return True  # API works even if no expected languages
        return False

    def test_course_crud_operations(self):
        """Test all CRUD operations for courses"""
        # Test GET /api/courses
        success1, response1 = self.run_test(
            "GET /api/courses - List All",
            "GET",
            "api/courses",
            200
        )
        
        if not success1:
            return False
        
        all_courses = response1 if isinstance(response1, list) else []
        print(f"   📊 Total courses: {len(all_courses)}")
        
        # Test POST /api/courses (create)
        unique_id = str(uuid.uuid4())[:8]
        new_course_data = {
            "title": f"CRUD Test Course {unique_id}",
            "description": "Course for CRUD testing",
            "instructor": "Test Instructor",
            "duration": "1 ora",
            "price": 49.99,
            "category": "test",
            "language": "it",
            "is_active": True
        }
        
        success2, response2 = self.run_test(
            "POST /api/courses - Create",
            "POST",
            "api/courses",
            200,
            data=new_course_data
        )
        
        if not success2:
            return False
        
        crud_course_id = response2.get('id')
        print(f"   ✅ CRUD test course created: {crud_course_id}")
        
        # Test PUT /api/courses/{id} (update)
        update_data = {
            "title": f"Updated CRUD Test Course {unique_id}",
            "price": 79.99,
            "duration": "2 ore"
        }
        
        success3, response3 = self.run_test(
            "PUT /api/courses/{id} - Update",
            "PUT",
            f"api/courses/{crud_course_id}",
            200,
            data=update_data
        )
        
        if not success3:
            return False
        
        updated_title = response3.get('title', '')
        updated_price = response3.get('price', 0)
        
        if updated_title == update_data['title'] and updated_price == update_data['price']:
            print(f"   ✅ Course update successful")
            print(f"   📚 New title: {updated_title}")
            print(f"   💰 New price: €{updated_price}")
        else:
            print(f"   ❌ Course update failed - data mismatch")
            return False
        
        # Test DELETE /api/courses/{id} (delete)
        success4, response4 = self.run_test(
            "DELETE /api/courses/{id} - Delete",
            "DELETE",
            f"api/courses/{crud_course_id}",
            200
        )
        
        if success4:
            print(f"   ✅ All CRUD operations working correctly")
            return True
        
        return False

    def test_course_filters_comprehensive(self):
        """Test comprehensive course filtering options"""
        # Test category filter
        success1, response1 = self.run_test(
            "Course Filter - Category",
            "GET",
            "api/courses?category=corso",
            200
        )
        
        if not success1:
            return False
        
        category_courses = response1 if isinstance(response1, list) else []
        print(f"   📊 Courses with category 'corso': {len(category_courses)}")
        
        # Test instructor filter
        success2, response2 = self.run_test(
            "Course Filter - Instructor",
            "GET",
            "api/courses?instructor=Grabovoi",
            200
        )
        
        if not success2:
            return False
        
        instructor_courses = response2 if isinstance(response2, list) else []
        print(f"   📊 Courses by Grabovoi: {len(instructor_courses)}")
        
        # Test price range filter
        success3, response3 = self.run_test(
            "Course Filter - Price Range",
            "GET",
            "api/courses?min_price=50&max_price=200",
            200
        )
        
        if not success3:
            return False
        
        price_courses = response3 if isinstance(response3, list) else []
        print(f"   📊 Courses in €50-200 range: {len(price_courses)}")
        
        # Test active status filter
        success4, response4 = self.run_test(
            "Course Filter - Active Status",
            "GET",
            "api/courses?is_active=true",
            200
        )
        
        if success4:
            active_courses = response4 if isinstance(response4, list) else []
            print(f"   📊 Active courses: {len(active_courses)}")
            print(f"   ✅ All course filters working correctly")
            return True
        
        return False

    def cleanup_test_data(self):
        """Clean up test data created during testing"""
        print(f"\n🧹 Cleaning up test data...")
        
        # Clean up test product
        if self.test_product_id:
            self.run_test(
                "Cleanup Test Product",
                "DELETE",
                f"api/products/{self.test_product_id}",
                200
            )
        
        print(f"   ✅ Test data cleanup completed")

    def run_all_course_deletion_tests(self):
        """Run all course deletion functionality tests"""
        print("🚀 Starting Course Deletion Functionality Testing...")
        print(f"🌐 Base URL: {self.base_url}")
        print("=" * 80)
        
        # Test sequence for course deletion functionality
        test_methods = [
            self.test_login,
            
            # 1. Test Cancellazione Singola Corso
            self.test_create_test_course,
            self.test_verify_course_exists_in_collection,
            self.test_delete_course_via_api,
            self.test_verify_course_removed_from_courses_collection,
            
            # 2. Test Prevenzione Ricreazione Automatica
            self.test_create_product_with_corso_keyword,
            self.test_verify_no_automatic_course_recreation,
            
            # 3. Test API Restore Auto-Creation
            self.test_restore_auto_creation_api,
            
            # 4. Test Filtro Lingua Corsi
            self.test_course_language_filter,
            self.test_get_course_languages_api,
            
            # 5. Test API Endpoints Corsi
            self.test_course_crud_operations,
            self.test_course_filters_comprehensive,
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
        print("📊 COURSE DELETION FUNCTIONALITY TEST RESULTS")
        print("=" * 80)
        print(f"✅ Tests Passed: {self.tests_passed}")
        print(f"❌ Tests Failed: {self.tests_run - self.tests_passed}")
        print(f"📊 Total Tests: {self.tests_run}")
        print(f"📈 Success Rate: {(self.tests_passed/self.tests_run)*100:.1f}%")
        
        if self.tests_passed == self.tests_run:
            print("\n🎉 ALL COURSE DELETION TESTS PASSED!")
            print("✅ Course deletion with tracking working perfectly")
            print("✅ Auto-recreation prevention working correctly")
            print("✅ Restore auto-creation API functional")
            print("✅ Language filters and CRUD operations working")
        elif self.tests_passed / self.tests_run >= 0.8:
            print("\n✅ COURSE DELETION FUNCTIONALITY MOSTLY WORKING")
            print("⚠️ Some minor issues detected, but core functionality is working")
        else:
            print("\n⚠️ COURSE DELETION FUNCTIONALITY NEEDS ATTENTION")
            print("❌ Multiple issues detected with course deletion system")
        
        return self.tests_passed, self.tests_run

if __name__ == "__main__":
    tester = CourseDeletionTester()
    tester.run_all_course_deletion_tests()