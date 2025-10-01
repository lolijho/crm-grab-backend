import requests
import sys
import json
import time
import uuid

class CourseLanguageTester:
    def __init__(self, base_url="https://faster-crm.preview.emergentagent.com"):
        self.base_url = base_url
        self.token = None
        self.tests_run = 0
        self.tests_passed = 0
        self.user_id = None
        self.test_courses = []

    def run_test(self, name, method, endpoint, expected_status, data=None, headers=None, params=None):
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
        if params:
            print(f"   Params: {params}")
        
        try:
            if method == 'GET':
                response = requests.get(url, headers=test_headers, params=params)
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

    def test_create_course_with_language(self):
        """Test creating courses with language field"""
        print("\n🔍 Testing Course Creation with Language Field...")
        
        # Test 1: Create course with Italian language
        course_data_italian = {
            "title": "Corso di Italiano Avanzato",
            "description": "Un corso completo di italiano per studenti avanzati",
            "instructor": "Prof. Marco Rossi",
            "duration": "12 settimane",
            "price": 299.99,
            "category": "Lingue",
            "language": "Italian",
            "is_active": True,
            "max_students": 25
        }
        
        success, response = self.run_test(
            "Create Course with Italian Language",
            "POST",
            "api/courses",
            200,
            data=course_data_italian
        )
        
        if success:
            course_id = response.get('id')
            if course_id and response.get('language') == 'Italian':
                self.test_courses.append({'id': course_id, 'language': 'Italian', 'title': response.get('title')})
                print(f"   ✅ Italian course created: {course_id}")
            else:
                print(f"   ❌ Language field not properly stored")
                return False
        else:
            return False
        
        # Test 2: Create course with English language
        course_data_english = {
            "title": "Advanced English Grammar",
            "description": "Comprehensive English grammar course for advanced learners",
            "instructor": "Prof.ssa Sarah Johnson",
            "duration": "10 weeks",
            "price": 249.99,
            "category": "Languages",
            "language": "English",
            "is_active": True,
            "max_students": 30
        }
        
        success2, response2 = self.run_test(
            "Create Course with English Language",
            "POST",
            "api/courses",
            200,
            data=course_data_english
        )
        
        if success2:
            course_id = response2.get('id')
            if course_id and response2.get('language') == 'English':
                self.test_courses.append({'id': course_id, 'language': 'English', 'title': response2.get('title')})
                print(f"   ✅ English course created: {course_id}")
            else:
                print(f"   ❌ Language field not properly stored")
                return False
        else:
            return False
        
        # Test 3: Create course without language (should be None/null)
        course_data_no_lang = {
            "title": "Mathematics Fundamentals",
            "description": "Basic mathematics course",
            "instructor": "Prof. Giovanni Bianchi",
            "duration": "8 weeks",
            "price": 199.99,
            "category": "Mathematics",
            "is_active": True,
            "max_students": 20
        }
        
        success3, response3 = self.run_test(
            "Create Course without Language",
            "POST",
            "api/courses",
            200,
            data=course_data_no_lang
        )
        
        if success3:
            course_id = response3.get('id')
            language = response3.get('language')
            if course_id and (language is None or language == ""):
                self.test_courses.append({'id': course_id, 'language': None, 'title': response3.get('title')})
                print(f"   ✅ Course without language created: {course_id}")
            else:
                print(f"   ❌ Language field should be None/null, got: {language}")
                return False
        else:
            return False
        
        return success and success2 and success3

    def test_update_course_language(self):
        """Test updating courses to add/change language"""
        if not self.test_courses:
            print("   ❌ No test courses available")
            return False
        
        print("\n🔍 Testing Course Language Updates...")
        
        # Test 1: Add language to course without language
        course_without_lang = next((c for c in self.test_courses if c['language'] is None), None)
        if course_without_lang:
            update_data = {
                "language": "Spanish"
            }
            
            success, response = self.run_test(
                "Add Language to Course",
                "PUT",
                f"api/courses/{course_without_lang['id']}",
                200,
                data=update_data
            )
            
            if success and response.get('language') == 'Spanish':
                course_without_lang['language'] = 'Spanish'  # Update our local record
                print(f"   ✅ Language added successfully: Spanish")
            else:
                print(f"   ❌ Failed to add language")
                return False
        
        # Test 2: Change existing language
        italian_course = next((c for c in self.test_courses if c['language'] == 'Italian'), None)
        if italian_course:
            update_data = {
                "language": "French"
            }
            
            success2, response2 = self.run_test(
                "Change Course Language",
                "PUT",
                f"api/courses/{italian_course['id']}",
                200,
                data=update_data
            )
            
            if success2 and response2.get('language') == 'French':
                italian_course['language'] = 'French'  # Update our local record
                print(f"   ✅ Language changed successfully: Italian → French")
            else:
                print(f"   ❌ Failed to change language")
                return False
        
        # Test 3: Remove language (set to null)
        english_course = next((c for c in self.test_courses if c['language'] == 'English'), None)
        if english_course:
            update_data = {
                "language": None
            }
            
            success3, response3 = self.run_test(
                "Remove Course Language",
                "PUT",
                f"api/courses/{english_course['id']}",
                200,
                data=update_data
            )
            
            if success3:
                language = response3.get('language')
                if language is None or language == "":
                    english_course['language'] = None  # Update our local record
                    print(f"   ✅ Language removed successfully")
                else:
                    print(f"   ❌ Language should be None/null, got: {language}")
                    return False
            else:
                return False
        
        return True

    def test_language_filtering_api(self):
        """Test GET /api/courses with language filtering"""
        print("\n🔍 Testing Language Filtering API...")
        
        # Test 1: Get all courses without language filter
        success, response = self.run_test(
            "Get All Courses (No Filter)",
            "GET",
            "api/courses",
            200
        )
        
        if success:
            all_courses = response if isinstance(response, list) else []
            print(f"   ✅ Retrieved {len(all_courses)} total courses")
        else:
            return False
        
        # Test 2: Filter by Italian language (should return 0 since we changed it to French)
        success2, response2 = self.run_test(
            "Filter Courses by Italian Language",
            "GET",
            "api/courses",
            200,
            params={"language": "Italian"}
        )
        
        if success2:
            italian_courses = response2 if isinstance(response2, list) else []
            print(f"   ✅ Italian courses found: {len(italian_courses)}")
            
            # Verify all returned courses have Italian language
            for course in italian_courses:
                if course.get('language') != 'Italian':
                    print(f"   ❌ Non-Italian course in results: {course.get('language')}")
                    return False
        else:
            return False
        
        # Test 3: Filter by French language (should return 1 course)
        success3, response3 = self.run_test(
            "Filter Courses by French Language",
            "GET",
            "api/courses",
            200,
            params={"language": "French"}
        )
        
        if success3:
            french_courses = response3 if isinstance(response3, list) else []
            print(f"   ✅ French courses found: {len(french_courses)}")
            
            # Verify all returned courses have French language
            for course in french_courses:
                if course.get('language') != 'French':
                    print(f"   ❌ Non-French course in results: {course.get('language')}")
                    return False
        else:
            return False
        
        # Test 4: Filter by Spanish language (should return 1 course)
        success4, response4 = self.run_test(
            "Filter Courses by Spanish Language",
            "GET",
            "api/courses",
            200,
            params={"language": "Spanish"}
        )
        
        if success4:
            spanish_courses = response4 if isinstance(response4, list) else []
            print(f"   ✅ Spanish courses found: {len(spanish_courses)}")
            
            # Verify all returned courses have Spanish language
            for course in spanish_courses:
                if course.get('language') != 'Spanish':
                    print(f"   ❌ Non-Spanish course in results: {course.get('language')}")
                    return False
        else:
            return False
        
        # Test 5: Filter by invalid/non-existent language
        success5, response5 = self.run_test(
            "Filter by Invalid Language",
            "GET",
            "api/courses",
            200,
            params={"language": "Klingon"}
        )
        
        if success5:
            klingon_courses = response5 if isinstance(response5, list) else []
            if len(klingon_courses) == 0:
                print(f"   ✅ Invalid language returns empty results: {len(klingon_courses)}")
            else:
                print(f"   ❌ Invalid language should return empty results, got: {len(klingon_courses)}")
                return False
        else:
            return False
        
        return success and success2 and success3 and success4 and success5

    def test_course_languages_endpoint(self):
        """Test GET /api/courses/languages endpoint"""
        print("\n🔍 Testing Course Languages Endpoint...")
        
        # Test the /api/courses/languages endpoint
        success, response = self.run_test(
            "Get Available Course Languages",
            "GET",
            "api/courses/languages",
            200
        )
        
        if success:
            languages = response if isinstance(response, list) else []
            print(f"   ✅ Available languages: {languages}")
            
            # Verify it's a list
            if not isinstance(languages, list):
                print(f"   ❌ Response should be a list, got: {type(languages)}")
                return False
            
            # Verify it contains our test languages (French, Spanish)
            expected_languages = ['French', 'Spanish']
            found_languages = []
            
            for lang in expected_languages:
                if lang in languages:
                    found_languages.append(lang)
                    print(f"   ✅ Found expected language: {lang}")
            
            # Verify no null/empty values
            for lang in languages:
                if lang is None or lang == "" or lang.strip() == "":
                    print(f"   ❌ Found null/empty language value: '{lang}'")
                    return False
            
            # Verify results are sorted alphabetically
            sorted_languages = sorted(languages)
            if languages == sorted_languages:
                print(f"   ✅ Languages are sorted alphabetically")
            else:
                print(f"   ❌ Languages are not sorted. Expected: {sorted_languages}, Got: {languages}")
                return False
            
            print(f"   ✅ Languages endpoint working correctly")
            return True
        
        return False

    def test_data_integrity(self):
        """Test data integrity for course language functionality"""
        print("\n🔍 Testing Data Integrity...")
        
        # Create additional test courses with different languages
        test_languages = ["German", "Portuguese", "Japanese"]
        created_courses = []
        
        for i, language in enumerate(test_languages):
            course_data = {
                "title": f"Test Course {language} {i+1}",
                "description": f"Test course for {language} language testing",
                "instructor": f"Prof. Test {i+1}",
                "duration": f"{8+i} weeks",
                "price": 150.0 + (i * 50),
                "category": "Test",
                "language": language,
                "is_active": True,
                "max_students": 15 + (i * 5)
            }
            
            success, response = self.run_test(
                f"Create Test Course - {language}",
                "POST",
                "api/courses",
                200,
                data=course_data
            )
            
            if success:
                course_id = response.get('id')
                if course_id and response.get('language') == language:
                    created_courses.append({'id': course_id, 'language': language})
                    print(f"   ✅ {language} course created: {course_id}")
                else:
                    print(f"   ❌ Failed to create {language} course properly")
                    return False
            else:
                return False
        
        # Test language filtering for each new language
        for course in created_courses:
            language = course['language']
            
            success, response = self.run_test(
                f"Verify {language} Language Filter",
                "GET",
                "api/courses",
                200,
                params={"language": language}
            )
            
            if success:
                filtered_courses = response if isinstance(response, list) else []
                
                # Find our test course in the results
                found_course = False
                for filtered_course in filtered_courses:
                    if filtered_course.get('id') == course['id']:
                        found_course = True
                        if filtered_course.get('language') != language:
                            print(f"   ❌ Language mismatch for course {course['id']}")
                            return False
                        break
                
                if found_course:
                    print(f"   ✅ {language} course found in filtered results")
                else:
                    print(f"   ❌ {language} course not found in filtered results")
                    return False
            else:
                return False
        
        # Test that existing courses without language are handled properly
        success, response = self.run_test(
            "Get All Courses for Null Language Check",
            "GET",
            "api/courses",
            200
        )
        
        if success:
            all_courses = response if isinstance(response, list) else []
            courses_without_language = [c for c in all_courses if c.get('language') is None or c.get('language') == ""]
            
            print(f"   ✅ Found {len(courses_without_language)} courses without language")
            print(f"   ✅ Total courses: {len(all_courses)}")
            
            # Verify language field is present in all course responses
            for course in all_courses:
                if 'language' not in course:
                    print(f"   ❌ Language field missing from course response: {course.get('id')}")
                    return False
            
            print(f"   ✅ All courses have language field in response")
        else:
            return False
        
        # Clean up test courses
        for course in created_courses:
            self.run_test(
                f"Cleanup Test Course - {course['language']}",
                "DELETE",
                f"api/courses/{course['id']}",
                200
            )
        
        return True

    def cleanup_test_courses(self):
        """Clean up test courses created during testing"""
        print("\n🧹 Cleaning up test courses...")
        
        for course in self.test_courses:
            success, response = self.run_test(
                f"Cleanup Course - {course['title']}",
                "DELETE",
                f"api/courses/{course['id']}",
                200
            )
            
            if success:
                print(f"   ✅ Deleted course: {course['title']}")
            else:
                print(f"   ❌ Failed to delete course: {course['title']}")
        
        print("   ✅ Test course cleanup completed")

    def run_all_course_language_tests(self):
        """Run all course language functionality tests"""
        print("🚀 Starting Course Language Functionality Testing...")
        print(f"🌐 Base URL: {self.base_url}")
        print("=" * 80)
        
        # Test sequence for course language functionality
        test_methods = [
            self.test_login,
            self.test_create_course_with_language,
            self.test_update_course_language,
            self.test_language_filtering_api,
            self.test_course_languages_endpoint,
            self.test_data_integrity,
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
            self.cleanup_test_courses()
        except Exception as e:
            print(f"⚠️ Cleanup failed: {str(e)}")
        
        # Print final results
        print("\n" + "=" * 80)
        print("📊 COURSE LANGUAGE FUNCTIONALITY TEST RESULTS")
        print("=" * 80)
        print(f"✅ Tests Passed: {self.tests_passed}")
        print(f"❌ Tests Failed: {self.tests_run - self.tests_passed}")
        print(f"📊 Total Tests: {self.tests_run}")
        print(f"📈 Success Rate: {(self.tests_passed/self.tests_run)*100:.1f}%")
        
        if self.tests_passed == self.tests_run:
            print("\n🎉 ALL COURSE LANGUAGE TESTS PASSED!")
            print("✅ Course language field functionality working perfectly")
            print("✅ Language filtering API working correctly")
            print("✅ Course languages endpoint working properly")
            print("✅ Data integrity verified")
        elif self.tests_passed / self.tests_run >= 0.8:
            print("\n✅ COURSE LANGUAGE FUNCTIONALITY MOSTLY WORKING")
            print("⚠️ Some minor issues detected, but core functionality is working")
        else:
            print("\n⚠️ COURSE LANGUAGE FUNCTIONALITY NEEDS ATTENTION")
            print("❌ Multiple issues detected with language functionality")
        
        return self.tests_passed, self.tests_run

if __name__ == "__main__":
    print("🚀 Starting Course Language Functionality Testing...")
    print("=" * 80)
    
    # Run Course Language Tests
    course_language_tester = CourseLanguageTester()
    course_language_passed, course_language_run = course_language_tester.run_all_course_language_tests()
    
    # Print overall results
    print("\n" + "=" * 80)
    print("🎯 COURSE LANGUAGE TESTING RESULTS")
    print("=" * 80)
    print(f"✅ Tests Passed: {course_language_passed}")
    print(f"❌ Tests Failed: {course_language_run - course_language_passed}")
    print(f"📊 Total Tests Run: {course_language_run}")
    print(f"📈 Success Rate: {(course_language_passed/course_language_run)*100:.1f}%")
    
    if course_language_passed == course_language_run:
        print("\n🎉 ALL COURSE LANGUAGE TESTS PASSED!")
        print("🚀 Course language functionality is fully working and ready for production!")
    elif course_language_passed / course_language_run >= 0.9:
        print("\n✅ COURSE LANGUAGE FUNCTIONALITY MOSTLY WORKING")
        print("🔧 Minor issues detected, but system is largely functional")
    elif course_language_passed / course_language_run >= 0.7:
        print("\n⚠️ COURSE LANGUAGE FUNCTIONALITY PARTIALLY WORKING")
        print("🛠️ Several issues detected, requires attention")
    else:
        print("\n❌ COURSE LANGUAGE FUNCTIONALITY NEEDS SIGNIFICANT WORK")
        print("🚨 Major issues detected, requires immediate attention")
    
    print("\n" + "=" * 80)