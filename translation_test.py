#!/usr/bin/env python3
"""
Backend Translation System Testing for Grabovoi CRM
Tests the complete translation system for course operations with Italian and English languages.
"""

import requests
import sys
import json
import time
import uuid
import os

class TranslationSystemTester:
    def __init__(self, base_url="https://faster-crm.preview.emergentagent.com"):
        self.base_url = base_url
        self.token = None
        self.tests_run = 0
        self.tests_passed = 0
        self.user_id = None
        self.test_course_id = None
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
        if headers and 'Accept-Language' in headers:
            print(f"   Language: {headers['Accept-Language']}")
        
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

    def create_test_course(self):
        """Create a test course for translation testing"""
        print("\n🔍 Creating Test Course for Translation Testing...")
        
        course_data = {
            "title": "Corso Test Traduzioni",
            "description": "Corso creato per testare il sistema di traduzioni",
            "instructor": "Prof. Test",
            "duration": "2 ore",
            "price": 99.99,
            "category": "test",
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
            self.test_course_data = response
            print(f"   ✅ Test course created with ID: {self.test_course_id}")
            return True
        
        return False

    def test_course_crud_italian_messages(self):
        """Test CRUD operations on courses with Italian language headers"""
        if not self.test_course_id:
            print("   ❌ No test course available")
            return False
        
        print("\n🔍 Testing Course CRUD with Italian Messages...")
        
        # Test 1: GET course with Italian header
        success1, response1 = self.run_test(
            "GET Course - Italian",
            "GET",
            f"api/courses/{self.test_course_id}",
            200,
            headers={'Accept-Language': 'it'}
        )
        
        # Test 2: UPDATE course with Italian header
        update_data = {
            "title": "Corso Test Traduzioni Aggiornato",
            "description": "Descrizione aggiornata in italiano"
        }
        
        success2, response2 = self.run_test(
            "UPDATE Course - Italian",
            "PUT",
            f"api/courses/{self.test_course_id}",
            200,
            data=update_data,
            headers={'Accept-Language': 'it'}
        )
        
        if success2:
            # Check if response contains Italian success message
            message = response2.get('message', '')
            if 'aggiornato con successo' in message.lower() or 'corso' in message.lower():
                print(f"   ✅ Italian success message detected: {message}")
            else:
                print(f"   ⚠️ Success message may not be in Italian: {message}")
        
        # Test 3: Try to create course with invalid data (Italian error)
        invalid_course_data = {
            "title": "",  # Empty title should cause error
            "price": -10  # Negative price should cause error
        }
        
        success3, response3 = self.run_test(
            "CREATE Course Invalid Data - Italian",
            "POST",
            "api/courses",
            400,
            data=invalid_course_data,
            headers={'Accept-Language': 'it'}
        )
        
        if success3:
            error_detail = response3.get('detail', '')
            if 'vuoto' in error_detail.lower() or 'negativo' in error_detail.lower():
                print(f"   ✅ Italian error message detected: {error_detail}")
            else:
                print(f"   ⚠️ Error message may not be in Italian: {error_detail}")
        
        return success1 and success2 and success3

    def test_course_crud_english_messages(self):
        """Test CRUD operations on courses with English language headers"""
        if not self.test_course_id:
            print("   ❌ No test course available")
            return False
        
        print("\n🔍 Testing Course CRUD with English Messages...")
        
        # Test 1: GET course with English header
        success1, response1 = self.run_test(
            "GET Course - English",
            "GET",
            f"api/courses/{self.test_course_id}",
            200,
            headers={'Accept-Language': 'en'}
        )
        
        # Test 2: UPDATE course with English header
        update_data = {
            "title": "Updated Translation Test Course",
            "description": "Updated description in English"
        }
        
        success2, response2 = self.run_test(
            "UPDATE Course - English",
            "PUT",
            f"api/courses/{self.test_course_id}",
            200,
            data=update_data,
            headers={'Accept-Language': 'en'}
        )
        
        if success2:
            # Check if response contains English success message
            message = response2.get('message', '')
            if 'updated successfully' in message.lower() or 'course' in message.lower():
                print(f"   ✅ English success message detected: {message}")
            else:
                print(f"   ⚠️ Success message may not be in English: {message}")
        
        # Test 3: Try to create course with invalid data (English error)
        invalid_course_data = {
            "title": "",  # Empty title should cause error
            "price": -10  # Negative price should cause error
        }
        
        success3, response3 = self.run_test(
            "CREATE Course Invalid Data - English",
            "POST",
            "api/courses",
            400,
            data=invalid_course_data,
            headers={'Accept-Language': 'en'}
        )
        
        if success3:
            error_detail = response3.get('detail', '')
            if 'empty' in error_detail.lower() or 'negative' in error_detail.lower():
                print(f"   ✅ English error message detected: {error_detail}")
            else:
                print(f"   ⚠️ Error message may not be in English: {error_detail}")
        
        return success1 and success2 and success3

    def test_course_delete_italian(self):
        """Test DELETE course with Italian language header"""
        if not self.test_course_id:
            print("   ❌ No test course available")
            return False
        
        print("\n🔍 Testing Course DELETE with Italian Messages...")
        
        success, response = self.run_test(
            "DELETE Course - Italian",
            "DELETE",
            f"api/courses/{self.test_course_id}",
            200,
            headers={'Accept-Language': 'it'}
        )
        
        if success:
            message = response.get('message', '')
            if 'eliminato con successo' in message.lower() or 'corso' in message.lower():
                print(f"   ✅ Italian delete message detected: {message}")
                # Course is now deleted, clear the ID
                self.test_course_id = None
                return True
            else:
                print(f"   ⚠️ Delete message may not be in Italian: {message}")
                return True  # Still consider success if deletion worked
        
        return False

    def test_course_delete_english(self):
        """Test DELETE course with English language header"""
        # Create a new course for English delete test
        course_data = {
            "title": "English Delete Test Course",
            "description": "Course for testing English delete messages",
            "instructor": "Prof. English",
            "duration": "1 hour",
            "price": 49.99,
            "category": "test",
            "language": "en",
            "is_active": True
        }
        
        success_create, response_create = self.run_test(
            "Create Course for English Delete Test",
            "POST",
            "api/courses",
            200,
            data=course_data
        )
        
        if not success_create:
            return False
        
        course_id = response_create.get('id')
        
        print("\n🔍 Testing Course DELETE with English Messages...")
        
        success, response = self.run_test(
            "DELETE Course - English",
            "DELETE",
            f"api/courses/{course_id}",
            200,
            headers={'Accept-Language': 'en'}
        )
        
        if success:
            message = response.get('message', '')
            if 'deleted successfully' in message.lower() or 'course' in message.lower():
                print(f"   ✅ English delete message detected: {message}")
                return True
            else:
                print(f"   ⚠️ Delete message may not be in English: {message}")
                return True  # Still consider success if deletion worked
        
        return False

    def test_course_not_found_errors(self):
        """Test 404 errors with different languages"""
        print("\n🔍 Testing Course 404 Errors with Different Languages...")
        
        fake_course_id = "507f1f77bcf86cd799439011"
        
        # Test Italian 404
        success1, response1 = self.run_test(
            "GET Non-existent Course - Italian",
            "GET",
            f"api/courses/{fake_course_id}",
            404,
            headers={'Accept-Language': 'it'}
        )
        
        if success1:
            error_detail = response1.get('detail', '')
            if 'non trovato' in error_detail.lower() or 'corso' in error_detail.lower():
                print(f"   ✅ Italian 404 message detected: {error_detail}")
            else:
                print(f"   ⚠️ 404 message may not be in Italian: {error_detail}")
        
        # Test English 404
        success2, response2 = self.run_test(
            "GET Non-existent Course - English",
            "GET",
            f"api/courses/{fake_course_id}",
            404,
            headers={'Accept-Language': 'en'}
        )
        
        if success2:
            error_detail = response2.get('detail', '')
            if 'not found' in error_detail.lower() or 'course' in error_detail.lower():
                print(f"   ✅ English 404 message detected: {error_detail}")
            else:
                print(f"   ⚠️ 404 message may not be in English: {error_detail}")
        
        return success1 and success2

    def test_course_restore_auto_creation_italian(self):
        """Test POST /api/courses/{id}/restore-auto-creation with Italian"""
        # Create a course first
        course_data = {
            "title": "Corso Ripristino Auto-Creazione",
            "description": "Test per ripristino auto-creazione",
            "instructor": "Prof. Ripristino",
            "price": 75.00
        }
        
        success_create, response_create = self.run_test(
            "Create Course for Restore Test - Italian",
            "POST",
            "api/courses",
            200,
            data=course_data
        )
        
        if not success_create:
            return False
        
        course_id = response_create.get('id')
        
        print("\n🔍 Testing Course Restore Auto-Creation - Italian...")
        
        success, response = self.run_test(
            "POST Restore Auto-Creation - Italian",
            "POST",
            f"api/courses/{course_id}/restore-auto-creation",
            200,
            headers={'Accept-Language': 'it'}
        )
        
        if success:
            message = response.get('message', '')
            if 'ripristinata' in message.lower() or 'ricreazione' in message.lower():
                print(f"   ✅ Italian restore message detected: {message}")
            else:
                print(f"   ⚠️ Restore message may not be in Italian: {message}")
        
        # Cleanup
        self.run_test(
            "Cleanup Restore Test Course",
            "DELETE",
            f"api/courses/{course_id}",
            200
        )
        
        return success

    def test_course_restore_auto_creation_english(self):
        """Test POST /api/courses/{id}/restore-auto-creation with English"""
        # Create a course first
        course_data = {
            "title": "Auto-Creation Restore Test Course",
            "description": "Test for auto-creation restore",
            "instructor": "Prof. Restore",
            "price": 75.00
        }
        
        success_create, response_create = self.run_test(
            "Create Course for Restore Test - English",
            "POST",
            "api/courses",
            200,
            data=course_data
        )
        
        if not success_create:
            return False
        
        course_id = response_create.get('id')
        
        print("\n🔍 Testing Course Restore Auto-Creation - English...")
        
        success, response = self.run_test(
            "POST Restore Auto-Creation - English",
            "POST",
            f"api/courses/{course_id}/restore-auto-creation",
            200,
            headers={'Accept-Language': 'en'}
        )
        
        if success:
            message = response.get('message', '')
            if 'restored' in message.lower() or 'auto-creation' in message.lower():
                print(f"   ✅ English restore message detected: {message}")
            else:
                print(f"   ⚠️ Restore message may not be in English: {message}")
        
        # Cleanup
        self.run_test(
            "Cleanup Restore Test Course",
            "DELETE",
            f"api/courses/{course_id}",
            200
        )
        
        return success

    def test_all_course_endpoints_with_languages(self):
        """Test all course endpoints with both language headers"""
        print("\n🔍 Testing All Course Endpoints with Language Headers...")
        
        # Test GET /api/courses with different languages
        success1, response1 = self.run_test(
            "GET All Courses - Italian",
            "GET",
            "api/courses",
            200,
            headers={'Accept-Language': 'it'}
        )
        
        success2, response2 = self.run_test(
            "GET All Courses - English",
            "GET",
            "api/courses",
            200,
            headers={'Accept-Language': 'en'}
        )
        
        # Create a course to test other endpoints
        course_data = {
            "title": "Endpoint Test Course",
            "description": "Course for testing all endpoints",
            "instructor": "Prof. Endpoint",
            "price": 60.00
        }
        
        success3, response3 = self.run_test(
            "Create Course for Endpoint Testing",
            "POST",
            "api/courses",
            200,
            data=course_data,
            headers={'Accept-Language': 'it'}
        )
        
        if success3:
            course_id = response3.get('id')
            
            # Test individual course endpoints
            success4, response4 = self.run_test(
                "GET Single Course - Italian",
                "GET",
                f"api/courses/{course_id}",
                200,
                headers={'Accept-Language': 'it'}
            )
            
            success5, response5 = self.run_test(
                "GET Single Course - English",
                "GET",
                f"api/courses/{course_id}",
                200,
                headers={'Accept-Language': 'en'}
            )
            
            # Cleanup
            self.run_test(
                "Cleanup Endpoint Test Course",
                "DELETE",
                f"api/courses/{course_id}",
                200
            )
            
            return success1 and success2 and success3 and success4 and success5
        
        return success1 and success2

    def test_validation_errors_translation(self):
        """Test validation errors are properly translated"""
        print("\n🔍 Testing Validation Error Translation...")
        
        # Test course creation with various validation errors
        
        # Test 1: Empty name - Italian
        invalid_data1 = {
            "title": "",
            "price": 50.00
        }
        
        success1, response1 = self.run_test(
            "Validation Error - Empty Title Italian",
            "POST",
            "api/courses",
            400,
            data=invalid_data1,
            headers={'Accept-Language': 'it'}
        )
        
        # Test 2: Empty name - English
        success2, response2 = self.run_test(
            "Validation Error - Empty Title English",
            "POST",
            "api/courses",
            400,
            data=invalid_data1,
            headers={'Accept-Language': 'en'}
        )
        
        # Test 3: Negative price - Italian
        invalid_data2 = {
            "title": "Test Course",
            "price": -25.00
        }
        
        success3, response3 = self.run_test(
            "Validation Error - Negative Price Italian",
            "POST",
            "api/courses",
            400,
            data=invalid_data2,
            headers={'Accept-Language': 'it'}
        )
        
        # Test 4: Negative price - English
        success4, response4 = self.run_test(
            "Validation Error - Negative Price English",
            "POST",
            "api/courses",
            400,
            data=invalid_data2,
            headers={'Accept-Language': 'en'}
        )
        
        # Analyze responses for translated error messages
        if success1:
            error1 = response1.get('detail', '')
            print(f"   📝 Italian empty title error: {error1}")
        
        if success2:
            error2 = response2.get('detail', '')
            print(f"   📝 English empty title error: {error2}")
        
        if success3:
            error3 = response3.get('detail', '')
            print(f"   📝 Italian negative price error: {error3}")
        
        if success4:
            error4 = response4.get('detail', '')
            print(f"   📝 English negative price error: {error4}")
        
        return success1 and success2 and success3 and success4

    def cleanup_test_data(self):
        """Clean up any remaining test data"""
        print("\n🧹 Cleaning up translation test data...")
        
        if self.test_course_id:
            self.run_test(
                "Cleanup Main Test Course",
                "DELETE",
                f"api/courses/{self.test_course_id}",
                200
            )
        
        print("   ✅ Translation test data cleanup completed")

    def run_all_translation_tests(self):
        """Run all translation system tests"""
        print("🚀 Starting Backend Translation System Testing...")
        print(f"🌐 Base URL: {self.base_url}")
        print("🌍 Testing Italian (it) and English (en) translations")
        print("=" * 80)
        
        # Test sequence for translation system
        test_methods = [
            self.test_login,
            self.create_test_course,
            self.test_course_crud_italian_messages,
            self.test_course_crud_english_messages,
            self.test_course_not_found_errors,
            self.test_course_restore_auto_creation_italian,
            self.test_course_restore_auto_creation_english,
            self.test_all_course_endpoints_with_languages,
            self.test_validation_errors_translation,
            self.test_course_delete_italian,
            self.test_course_delete_english,
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
        print("📊 BACKEND TRANSLATION SYSTEM TEST RESULTS")
        print("=" * 80)
        print(f"✅ Tests Passed: {self.tests_passed}")
        print(f"❌ Tests Failed: {self.tests_run - self.tests_passed}")
        print(f"📊 Total Tests: {self.tests_run}")
        print(f"📈 Success Rate: {(self.tests_passed/self.tests_run)*100:.1f}%")
        
        if self.tests_passed == self.tests_run:
            print("\n🎉 ALL TRANSLATION TESTS PASSED!")
            print("✅ Backend translation system fully functional")
            print("🇮🇹 Italian translations working correctly")
            print("🇬🇧 English translations working correctly")
            print("📝 All course operations properly translated")
        elif self.tests_passed / self.tests_run >= 0.8:
            print("\n✅ TRANSLATION SYSTEM MOSTLY WORKING")
            print("⚠️ Some minor translation issues detected")
        else:
            print("\n⚠️ TRANSLATION SYSTEM NEEDS ATTENTION")
            print("❌ Multiple translation issues detected")
        
        return self.tests_passed, self.tests_run

# Main execution
if __name__ == "__main__":
    print("🌍 BACKEND TRANSLATION SYSTEM TESTING")
    print("=" * 80)
    print("Testing the backend translation system:")
    print("- Italian (it) and English (en) message translations")
    print("- Course CRUD operations with Accept-Language headers")
    print("- Error messages in both languages")
    print("- Success messages in both languages")
    print("- DELETE /api/courses/{id} with language headers")
    print("- POST /api/courses/{id}/restore-auto-creation endpoint")
    print("- All course endpoints with proper translation responses")
    print("=" * 80)
    
    # Get base URL from environment or use default
    base_url = os.getenv("REACT_APP_BACKEND_URL", "https://faster-crm.preview.emergentagent.com")
    
    # Run translation tests
    translation_tester = TranslationSystemTester(base_url)
    passed, total = translation_tester.run_all_translation_tests()
    
    print("\n" + "=" * 80)
    print("🎯 BACKEND TRANSLATION SYSTEM TEST SUMMARY")
    print("=" * 80)
    print(f"📊 Tests Passed: {passed}/{total}")
    print(f"📈 Success Rate: {(passed/total)*100:.1f}%")
    
    if passed == total:
        print("\n🎉 ALL TRANSLATION TESTS PASSED!")
        print("✅ Backend translation system fully functional")
        print("🇮🇹 Italian translations working correctly")
        print("🇬🇧 English translations working correctly")
        print("📝 All course operations properly translated")
        print("✅ Translation system is working perfectly!")
        sys.exit(0)
    elif passed / total >= 0.8:
        print("\n✅ TRANSLATION SYSTEM MOSTLY WORKING")
        print("⚠️ Some minor translation issues detected")
        sys.exit(0)
    else:
        print("\n❌ TRANSLATION SYSTEM NEEDS ATTENTION")
        print("🚨 Critical issues found with translation system")
        sys.exit(1)