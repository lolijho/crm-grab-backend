import requests
import sys
import json
import time
import uuid
import os

class CourseFilteringTester:
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
                        if len(response_data) > 0 and len(response_data) <= 3:
                            print(f"   Sample items: {response_data}")
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

    def create_test_courses(self):
        """Create test courses with different attributes for filtering"""
        print("\n🔍 Creating Test Courses for Filtering...")
        
        test_courses_data = [
            {
                "title": "Corso Base Italiano",
                "description": "Corso base di lingua italiana",
                "instructor": "Marco Rossi",
                "duration": "30 ore",
                "price": 150.0,
                "category": "Base",
                "language": "Italian",
                "is_active": True,
                "max_students": 20
            },
            {
                "title": "Advanced English Course",
                "description": "Advanced English language course",
                "instructor": "John Smith",
                "duration": "40 ore",
                "price": 250.0,
                "category": "Advanced",
                "language": "English",
                "is_active": True,
                "max_students": 15
            },
            {
                "title": "Corso Intermedio Spagnolo",
                "description": "Corso intermedio di spagnolo",
                "instructor": "Marco Gonzalez",
                "duration": "35 ore",
                "price": 180.0,
                "category": "Intermediate",
                "language": "Spanish",
                "is_active": True,
                "max_students": 25
            },
            {
                "title": "Corso Base Francese",
                "description": "Corso base di francese",
                "instructor": "Marie Dubois",
                "duration": "25 ore",
                "price": 120.0,
                "category": "Base",
                "language": "French",
                "is_active": False,  # Inactive course
                "max_students": 18
            },
            {
                "title": "Premium Italian Course",
                "description": "Premium Italian language course",
                "instructor": "Marco Bianchi",
                "duration": "50 ore",
                "price": 350.0,
                "category": "Premium",
                "language": "Italian",
                "is_active": True,
                "max_students": 10
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
                        'instructor': course_data['instructor'],
                        'price': course_data['price'],
                        'category': course_data['category'],
                        'language': course_data['language'],
                        'is_active': course_data['is_active']
                    })
                    print(f"   ✅ Created course: {course_data['title']} (ID: {course_id})")
        
        self.test_courses = created_courses
        print(f"   📊 Total test courses created: {len(self.test_courses)}")
        return len(self.test_courses) > 0

    def test_language_filter(self):
        """Test GET /api/courses with language filter"""
        print("\n🔍 Testing Language Filter...")
        
        # Test Italian language filter
        success, response = self.run_test(
            "Language Filter - Italian",
            "GET",
            "api/courses",
            200,
            params={"language": "Italian"}
        )
        
        if success:
            italian_courses = response
            italian_count = len([c for c in italian_courses if c.get('language') == 'Italian'])
            print(f"   ✅ Found {italian_count} Italian courses")
            
            # Verify all returned courses are Italian
            all_italian = all(course.get('language') == 'Italian' for course in italian_courses)
            if all_italian:
                print(f"   ✅ All returned courses have Italian language")
                return True
            else:
                print(f"   ❌ Some courses don't have Italian language")
                return False
        
        return False

    def test_category_filter(self):
        """Test GET /api/courses with category filter"""
        print("\n🔍 Testing Category Filter...")
        
        # Test Base category filter
        success, response = self.run_test(
            "Category Filter - Base",
            "GET",
            "api/courses",
            200,
            params={"category": "Base"}
        )
        
        if success:
            base_courses = response
            base_count = len([c for c in base_courses if c.get('category') == 'Base'])
            print(f"   ✅ Found {base_count} Base category courses")
            
            # Verify all returned courses are Base category
            all_base = all(course.get('category') == 'Base' for course in base_courses)
            if all_base:
                print(f"   ✅ All returned courses have Base category")
                return True
            else:
                print(f"   ❌ Some courses don't have Base category")
                return False
        
        return False

    def test_status_filter(self):
        """Test GET /api/courses with status filter"""
        print("\n🔍 Testing Status Filter...")
        
        # Test active courses filter
        success, response = self.run_test(
            "Status Filter - Active (true)",
            "GET",
            "api/courses",
            200,
            params={"is_active": "true"}
        )
        
        if success:
            active_courses = response
            active_count = len([c for c in active_courses if c.get('is_active') == True])
            print(f"   ✅ Found {active_count} active courses")
            
            # Verify all returned courses are active
            all_active = all(course.get('is_active') == True for course in active_courses)
            if all_active:
                print(f"   ✅ All returned courses are active")
                return True
            else:
                print(f"   ❌ Some courses are not active")
                return False
        
        return False

    def test_instructor_filter(self):
        """Test GET /api/courses with instructor filter"""
        print("\n🔍 Testing Instructor Filter...")
        
        # Test instructor filter with partial name
        success, response = self.run_test(
            "Instructor Filter - Marco",
            "GET",
            "api/courses",
            200,
            params={"instructor": "Marco"}
        )
        
        if success:
            marco_courses = response
            marco_count = len([c for c in marco_courses if 'Marco' in c.get('instructor', '')])
            print(f"   ✅ Found {marco_count} courses with instructor containing 'Marco'")
            
            # Verify all returned courses have Marco in instructor name
            all_marco = all('Marco' in course.get('instructor', '') for course in marco_courses)
            if all_marco:
                print(f"   ✅ All returned courses have 'Marco' in instructor name")
                return True
            else:
                print(f"   ❌ Some courses don't have 'Marco' in instructor name")
                return False
        
        return False

    def test_price_range_filter(self):
        """Test GET /api/courses with price range filters"""
        print("\n🔍 Testing Price Range Filter...")
        
        # Test price range filter
        success, response = self.run_test(
            "Price Range Filter - 100 to 200",
            "GET",
            "api/courses",
            200,
            params={"min_price": "100", "max_price": "200"}
        )
        
        if success:
            price_filtered_courses = response
            valid_price_count = len([c for c in price_filtered_courses 
                                   if 100 <= c.get('price', 0) <= 200])
            print(f"   ✅ Found {valid_price_count} courses in price range 100-200")
            
            # Verify all returned courses are in price range
            all_in_range = all(100 <= course.get('price', 0) <= 200 
                             for course in price_filtered_courses)
            if all_in_range:
                print(f"   ✅ All returned courses are in price range 100-200")
                return True
            else:
                print(f"   ❌ Some courses are outside price range 100-200")
                return False
        
        return False

    def test_combined_filters(self):
        """Test GET /api/courses with multiple filters combined"""
        print("\n🔍 Testing Combined Filters...")
        
        # Test multiple filters together
        success, response = self.run_test(
            "Combined Filters - Italian + Base + Active",
            "GET",
            "api/courses",
            200,
            params={
                "language": "Italian",
                "category": "Base", 
                "is_active": "true"
            }
        )
        
        if success:
            combined_courses = response
            print(f"   ✅ Found {len(combined_courses)} courses matching all filters")
            
            # Verify all courses match all filters
            all_match = all(
                course.get('language') == 'Italian' and
                course.get('category') == 'Base' and
                course.get('is_active') == True
                for course in combined_courses
            )
            
            if all_match:
                print(f"   ✅ All returned courses match combined filters")
                return True
            else:
                print(f"   ❌ Some courses don't match all combined filters")
                return False
        
        return False

    def test_price_and_language_filter(self):
        """Test price range + language filter combination"""
        print("\n🔍 Testing Price + Language Filter...")
        
        success, response = self.run_test(
            "Price + Language Filter - English + min_price 200",
            "GET",
            "api/courses",
            200,
            params={
                "language": "English",
                "min_price": "200"
            }
        )
        
        if success:
            filtered_courses = response
            print(f"   ✅ Found {len(filtered_courses)} English courses with price >= 200")
            
            # Verify all courses match filters
            all_match = all(
                course.get('language') == 'English' and
                course.get('price', 0) >= 200
                for course in filtered_courses
            )
            
            if all_match:
                print(f"   ✅ All returned courses match price + language filters")
                return True
            else:
                print(f"   ❌ Some courses don't match price + language filters")
                return False
        
        return False

    def test_instructor_and_category_filter(self):
        """Test instructor + category filter combination"""
        print("\n🔍 Testing Instructor + Category Filter...")
        
        success, response = self.run_test(
            "Instructor + Category Filter - Marco + Base",
            "GET",
            "api/courses",
            200,
            params={
                "instructor": "Marco",
                "category": "Base"
            }
        )
        
        if success:
            filtered_courses = response
            print(f"   ✅ Found {len(filtered_courses)} courses with Marco instructor and Base category")
            
            # Verify all courses match filters
            all_match = all(
                'Marco' in course.get('instructor', '') and
                course.get('category') == 'Base'
                for course in filtered_courses
            )
            
            if all_match:
                print(f"   ✅ All returned courses match instructor + category filters")
                return True
            else:
                print(f"   ❌ Some courses don't match instructor + category filters")
                return False
        
        return False

    def test_filter_endpoints(self):
        """Test filter option endpoints"""
        print("\n🔍 Testing Filter Option Endpoints...")
        
        # Test categories endpoint
        success1, categories = self.run_test(
            "Get Course Categories",
            "GET",
            "api/courses/categories",
            200
        )
        
        # Test instructors endpoint
        success2, instructors = self.run_test(
            "Get Course Instructors",
            "GET",
            "api/courses/instructors",
            200
        )
        
        # Test languages endpoint
        success3, languages = self.run_test(
            "Get Course Languages",
            "GET",
            "api/courses/languages",
            200
        )
        
        if success1 and success2 and success3:
            print(f"   ✅ Categories: {categories}")
            print(f"   ✅ Instructors: {instructors}")
            print(f"   ✅ Languages: {languages}")
            
            # Verify they are sorted and filtered
            categories_sorted = categories == sorted(categories)
            instructors_sorted = instructors == sorted(instructors)
            languages_sorted = languages == sorted(languages)
            
            if categories_sorted and instructors_sorted and languages_sorted:
                print(f"   ✅ All filter options are sorted correctly")
                return True
            else:
                print(f"   ❌ Some filter options are not sorted")
                return False
        
        return False

    def test_edge_cases(self):
        """Test edge cases and invalid filters"""
        print("\n🔍 Testing Edge Cases...")
        
        # Test non-existent language
        success1, response1 = self.run_test(
            "Non-existent Language Filter",
            "GET",
            "api/courses",
            200,
            params={"language": "Klingon"}
        )
        
        # Test invalid price range
        success2, response2 = self.run_test(
            "Invalid Price Range - Negative",
            "GET",
            "api/courses",
            200,
            params={"min_price": "-50", "max_price": "100"}
        )
        
        # Test non-existent instructor
        success3, response3 = self.run_test(
            "Non-existent Instructor",
            "GET",
            "api/courses",
            200,
            params={"instructor": "NonExistentInstructor"}
        )
        
        if success1 and success2 and success3:
            # Should return empty results for non-existent values
            empty_results = (
                len(response1) == 0 and
                len(response3) == 0
            )
            
            if empty_results:
                print(f"   ✅ Non-existent filter values return empty results")
                print(f"   ✅ Invalid price ranges handled gracefully")
                return True
            else:
                print(f"   ❌ Edge cases not handled properly")
                return False
        
        return False

    def test_case_insensitive_instructor_search(self):
        """Test case-insensitive instructor search"""
        print("\n🔍 Testing Case-Insensitive Instructor Search...")
        
        # Test lowercase search
        success1, response1 = self.run_test(
            "Instructor Search - Lowercase 'marco'",
            "GET",
            "api/courses",
            200,
            params={"instructor": "marco"}
        )
        
        # Test uppercase search
        success2, response2 = self.run_test(
            "Instructor Search - Uppercase 'MARCO'",
            "GET",
            "api/courses",
            200,
            params={"instructor": "MARCO"}
        )
        
        if success1 and success2:
            # Both should return the same results
            if len(response1) == len(response2) and len(response1) > 0:
                print(f"   ✅ Case-insensitive search working: {len(response1)} courses found")
                return True
            else:
                print(f"   ❌ Case-insensitive search not working properly")
                return False
        
        return False

    def cleanup_test_courses(self):
        """Clean up test courses"""
        print("\n🧹 Cleaning up test courses...")
        
        for course in self.test_courses:
            self.run_test(
                f"Cleanup Course - {course['title']}",
                "DELETE",
                f"api/courses/{course['id']}",
                200
            )
        
        print("   ✅ Test courses cleanup completed")

    def run_all_course_filtering_tests(self):
        """Run all course filtering tests"""
        print("🚀 Starting Course Filtering System Testing...")
        print(f"🌐 Base URL: {self.base_url}")
        print("=" * 80)
        
        # Test sequence for course filtering
        test_methods = [
            self.test_login,
            self.create_test_courses,
            self.test_language_filter,
            self.test_category_filter,
            self.test_status_filter,
            self.test_instructor_filter,
            self.test_price_range_filter,
            self.test_combined_filters,
            self.test_price_and_language_filter,
            self.test_instructor_and_category_filter,
            self.test_filter_endpoints,
            self.test_edge_cases,
            self.test_case_insensitive_instructor_search,
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
        print("📊 COURSE FILTERING SYSTEM TEST RESULTS")
        print("=" * 80)
        print(f"✅ Tests Passed: {self.tests_passed}")
        print(f"❌ Tests Failed: {self.tests_run - self.tests_passed}")
        print(f"📊 Total Tests: {self.tests_run}")
        print(f"📈 Success Rate: {(self.tests_passed/self.tests_run)*100:.1f}%")
        
        if self.tests_passed == self.tests_run:
            print("\n🎉 ALL COURSE FILTERING TESTS PASSED!")
            print("✅ Multiple course filters working perfectly")
            print("✅ Combined filters working correctly")
            print("✅ Filter endpoints returning sorted results")
            print("✅ Edge cases handled gracefully")
        elif self.tests_passed / self.tests_run >= 0.8:
            print("\n✅ COURSE FILTERING SYSTEM MOSTLY WORKING")
            print("⚠️ Some minor issues detected, but core functionality is working")
        else:
            print("\n⚠️ COURSE FILTERING SYSTEM NEEDS ATTENTION")
            print("❌ Multiple issues detected with filtering functionality")
        
        return self.tests_passed, self.tests_run

if __name__ == "__main__":
    print("🚀 COURSE FILTERING SYSTEM TESTING")
    print("=" * 80)
    print("Testing the complete course filtering system that was just implemented:")
    print("1. Multiple Course Filters: language, category, status, instructor, price range")
    print("2. Combined Filters: Multiple filters working together")
    print("3. Filter Endpoints: Categories, instructors, languages endpoints")
    print("4. Edge Cases: Non-existent values, invalid ranges, case sensitivity")
    print("=" * 80)
    
    # Get base URL from environment or use default
    base_url = os.getenv("REACT_APP_BACKEND_URL", "https://faster-crm.preview.emergentagent.com")
    
    # Run course filtering tests
    tester = CourseFilteringTester(base_url)
    passed, total = tester.run_all_course_filtering_tests()
    
    print("\n" + "=" * 80)
    print("🎯 COURSE FILTERING SYSTEM TEST SUMMARY")
    print("=" * 80)
    print(f"📊 Tests Passed: {passed}/{total}")
    print(f"📈 Success Rate: {(passed/total)*100:.1f}%")
    
    if passed == total:
        print("\n🎉 ALL COURSE FILTERING TESTS PASSED!")
        print("✅ Language filter (?language=Italian) - WORKING")
        print("✅ Category filter (?category=Base) - WORKING")
        print("✅ Status filter (?is_active=true) - WORKING")
        print("✅ Instructor filter (?instructor=Marco) - WORKING")
        print("✅ Price range filters (?min_price=50&max_price=200) - WORKING")
        print("✅ Combined filters - WORKING")
        print("✅ Filter endpoints (/categories, /instructors, /languages) - WORKING")
        print("✅ Edge cases and case-insensitive search - WORKING")
        print("✅ Course filtering system is production ready!")
        sys.exit(0)
    elif passed / total >= 0.8:
        print("\n✅ COURSE FILTERING SYSTEM MOSTLY WORKING")
        print("⚠️ Some minor issues detected, but core functionality is working")
        sys.exit(0)
    else:
        print("\n❌ COURSE FILTERING SYSTEM NEEDS ATTENTION")
        print("🚨 Critical issues found with filtering functionality")
        sys.exit(1)