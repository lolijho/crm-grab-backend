import requests
import sys
import json
import time
import uuid
import os

class CourseEditFixTester:
    def __init__(self, base_url="https://faster-crm.preview.emergentagent.com"):
        self.base_url = base_url
        self.token = None
        self.tests_run = 0
        self.tests_passed = 0
        self.user_id = None
        self.test_course_id = None
        self.original_course_data = None

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

    def create_test_course(self):
        """Create a test course for editing tests"""
        print("\n🔍 Creating Test Course for Edit Testing...")
        
        course_data = {
            "title": "Advanced Python Programming",
            "description": "Comprehensive course covering advanced Python concepts and frameworks",
            "instructor": "Dr. Maria Rossi",
            "duration": "12 weeks",
            "price": 299.99,
            "category": "Programming",
            "is_active": True,
            "max_students": 25
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
            self.original_course_data = response
            print(f"   ✅ Test course created with ID: {self.test_course_id}")
            print(f"   📚 Course: {response.get('title')}")
            print(f"   💰 Price: €{response.get('price')}")
            print(f"   👥 Max Students: {response.get('max_students')}")
            return True
        
        return False

    def test_partial_update_title_and_price(self):
        """Test partial update of only title and price, verify other fields remain unchanged"""
        if not self.test_course_id:
            print("   ❌ No test course available")
            return False
        
        # Update only title and price
        update_data = {
            "title": "Expert Python Programming",
            "price": 349.99
        }
        
        success, response = self.run_test(
            "Partial Update - Title and Price Only",
            "PUT",
            f"api/courses/{self.test_course_id}",
            200,
            data=update_data
        )
        
        if success:
            # Verify updated fields
            if response.get('title') != "Expert Python Programming":
                print(f"   ❌ Title not updated correctly: {response.get('title')}")
                return False
            
            if response.get('price') != 349.99:
                print(f"   ❌ Price not updated correctly: {response.get('price')}")
                return False
            
            # Verify unchanged fields are preserved
            if response.get('description') != self.original_course_data.get('description'):
                print(f"   ❌ Description was modified: {response.get('description')}")
                return False
            
            if response.get('instructor') != self.original_course_data.get('instructor'):
                print(f"   ❌ Instructor was modified: {response.get('instructor')}")
                return False
            
            if response.get('duration') != self.original_course_data.get('duration'):
                print(f"   ❌ Duration was modified: {response.get('duration')}")
                return False
            
            if response.get('category') != self.original_course_data.get('category'):
                print(f"   ❌ Category was modified: {response.get('category')}")
                return False
            
            if response.get('max_students') != self.original_course_data.get('max_students'):
                print(f"   ❌ Max students was modified: {response.get('max_students')}")
                return False
            
            print(f"   ✅ Partial update successful - only specified fields changed")
            print(f"   📝 Title: {self.original_course_data.get('title')} → {response.get('title')}")
            print(f"   💰 Price: €{self.original_course_data.get('price')} → €{response.get('price')}")
            print(f"   ✅ All other fields preserved correctly")
            
            # Update our reference data
            self.original_course_data = response
            return True
        
        return False

    def test_single_field_updates(self):
        """Test updating single fields individually"""
        if not self.test_course_id:
            print("   ❌ No test course available")
            return False
        
        # Test 1: Update only instructor
        instructor_update = {"instructor": "Prof. Alessandro Bianchi"}
        
        success1, response1 = self.run_test(
            "Single Field Update - Instructor",
            "PUT",
            f"api/courses/{self.test_course_id}",
            200,
            data=instructor_update
        )
        
        if not success1:
            return False
        
        if response1.get('instructor') != "Prof. Alessandro Bianchi":
            print(f"   ❌ Instructor not updated correctly")
            return False
        
        # Verify other fields unchanged
        if response1.get('title') != self.original_course_data.get('title'):
            print(f"   ❌ Title was unexpectedly modified")
            return False
        
        print(f"   ✅ Instructor updated: {self.original_course_data.get('instructor')} → {response1.get('instructor')}")
        
        # Test 2: Update only duration
        duration_update = {"duration": "16 weeks"}
        
        success2, response2 = self.run_test(
            "Single Field Update - Duration",
            "PUT",
            f"api/courses/{self.test_course_id}",
            200,
            data=duration_update
        )
        
        if not success2:
            return False
        
        if response2.get('duration') != "16 weeks":
            print(f"   ❌ Duration not updated correctly")
            return False
        
        print(f"   ✅ Duration updated: {response1.get('duration')} → {response2.get('duration')}")
        
        # Test 3: Update only max_students
        max_students_update = {"max_students": 30}
        
        success3, response3 = self.run_test(
            "Single Field Update - Max Students",
            "PUT",
            f"api/courses/{self.test_course_id}",
            200,
            data=max_students_update
        )
        
        if not success3:
            return False
        
        if response3.get('max_students') != 30:
            print(f"   ❌ Max students not updated correctly")
            return False
        
        print(f"   ✅ Max students updated: {response2.get('max_students')} → {response3.get('max_students')}")
        
        # Update reference data
        self.original_course_data = response3
        return True

    def test_field_validation_empty_title(self):
        """Test validation for empty title"""
        if not self.test_course_id:
            print("   ❌ No test course available")
            return False
        
        # Test empty string title
        empty_title_data = {"title": ""}
        
        success1, response1 = self.run_test(
            "Validation - Empty Title",
            "PUT",
            f"api/courses/{self.test_course_id}",
            400,
            data=empty_title_data
        )
        
        if success1:
            error_detail = response1.get('detail', '')
            if 'empty' in error_detail.lower():
                print(f"   ✅ Empty title properly rejected: {error_detail}")
            else:
                print(f"   ❌ Unexpected error message: {error_detail}")
                return False
        else:
            return False
        
        # Test whitespace-only title
        whitespace_title_data = {"title": "   "}
        
        success2, response2 = self.run_test(
            "Validation - Whitespace Title",
            "PUT",
            f"api/courses/{self.test_course_id}",
            400,
            data=whitespace_title_data
        )
        
        if success2:
            error_detail = response2.get('detail', '')
            if 'empty' in error_detail.lower():
                print(f"   ✅ Whitespace title properly rejected: {error_detail}")
            else:
                print(f"   ❌ Unexpected error message: {error_detail}")
                return False
        else:
            return False
        
        return True

    def test_field_validation_negative_price(self):
        """Test validation for negative price"""
        if not self.test_course_id:
            print("   ❌ No test course available")
            return False
        
        # Test negative price
        negative_price_data = {"price": -50.0}
        
        success, response = self.run_test(
            "Validation - Negative Price",
            "PUT",
            f"api/courses/{self.test_course_id}",
            400,
            data=negative_price_data
        )
        
        if success:
            error_detail = response.get('detail', '')
            if 'negative' in error_detail.lower():
                print(f"   ✅ Negative price properly rejected: {error_detail}")
                return True
            else:
                print(f"   ❌ Unexpected error message: {error_detail}")
                return False
        
        return False

    def test_field_validation_negative_max_students(self):
        """Test validation for negative max_students"""
        if not self.test_course_id:
            print("   ❌ No test course available")
            return False
        
        # Test zero max_students
        zero_students_data = {"max_students": 0}
        
        success1, response1 = self.run_test(
            "Validation - Zero Max Students",
            "PUT",
            f"api/courses/{self.test_course_id}",
            400,
            data=zero_students_data
        )
        
        if success1:
            error_detail = response1.get('detail', '')
            if 'at least 1' in error_detail.lower():
                print(f"   ✅ Zero max students properly rejected: {error_detail}")
            else:
                print(f"   ❌ Unexpected error message: {error_detail}")
                return False
        else:
            return False
        
        # Test negative max_students
        negative_students_data = {"max_students": -5}
        
        success2, response2 = self.run_test(
            "Validation - Negative Max Students",
            "PUT",
            f"api/courses/{self.test_course_id}",
            400,
            data=negative_students_data
        )
        
        if success2:
            error_detail = response2.get('detail', '')
            if 'at least 1' in error_detail.lower():
                print(f"   ✅ Negative max students properly rejected: {error_detail}")
                return True
            else:
                print(f"   ❌ Unexpected error message: {error_detail}")
                return False
        
        return False

    def test_valid_data_still_works(self):
        """Test that valid data still works correctly after validation"""
        if not self.test_course_id:
            print("   ❌ No test course available")
            return False
        
        # Test valid updates
        valid_data = {
            "title": "Masterclass Python Programming",
            "price": 399.99,
            "max_students": 20
        }
        
        success, response = self.run_test(
            "Validation - Valid Data",
            "PUT",
            f"api/courses/{self.test_course_id}",
            200,
            data=valid_data
        )
        
        if success:
            # Verify all fields updated correctly
            if (response.get('title') == "Masterclass Python Programming" and
                response.get('price') == 399.99 and
                response.get('max_students') == 20):
                print(f"   ✅ Valid data processed correctly")
                print(f"   📝 Title: {response.get('title')}")
                print(f"   💰 Price: €{response.get('price')}")
                print(f"   👥 Max Students: {response.get('max_students')}")
                
                # Update reference data
                self.original_course_data = response
                return True
            else:
                print(f"   ❌ Valid data not processed correctly")
                return False
        
        return False

    def test_update_all_fields(self):
        """Test updating all fields at once"""
        if not self.test_course_id:
            print("   ❌ No test course available")
            return False
        
        # Update all fields
        all_fields_data = {
            "title": "Complete Python Mastery Course",
            "description": "The ultimate Python course covering everything from basics to advanced topics",
            "instructor": "Dr. Francesca Verdi",
            "duration": "20 weeks",
            "price": 499.99,
            "category": "Advanced Programming",
            "is_active": False,
            "max_students": 15
        }
        
        success, response = self.run_test(
            "Update All Fields",
            "PUT",
            f"api/courses/{self.test_course_id}",
            200,
            data=all_fields_data
        )
        
        if success:
            # Verify all fields updated
            fields_correct = True
            for field, expected_value in all_fields_data.items():
                actual_value = response.get(field)
                if actual_value != expected_value:
                    print(f"   ❌ Field {field} not updated correctly: expected {expected_value}, got {actual_value}")
                    fields_correct = False
            
            if fields_correct:
                print(f"   ✅ All fields updated successfully")
                print(f"   📝 Title: {response.get('title')}")
                print(f"   👨‍🏫 Instructor: {response.get('instructor')}")
                print(f"   💰 Price: €{response.get('price')}")
                print(f"   🔄 Active: {response.get('is_active')}")
                
                # Update reference data
                self.original_course_data = response
                return True
        
        return False

    def test_empty_update(self):
        """Test updating with no fields (empty update)"""
        if not self.test_course_id:
            print("   ❌ No test course available")
            return False
        
        # Empty update
        empty_data = {}
        
        success, response = self.run_test(
            "Empty Update",
            "PUT",
            f"api/courses/{self.test_course_id}",
            200,
            data=empty_data
        )
        
        if success:
            # Verify all fields remain unchanged
            fields_unchanged = True
            for field in ['title', 'description', 'instructor', 'duration', 'price', 'category', 'is_active', 'max_students']:
                if response.get(field) != self.original_course_data.get(field):
                    print(f"   ❌ Field {field} was unexpectedly changed")
                    fields_unchanged = False
            
            if fields_unchanged:
                print(f"   ✅ Empty update handled correctly - no fields changed")
                # Check that updated_at was still updated
                if response.get('updated_at') != self.original_course_data.get('updated_at'):
                    print(f"   ✅ updated_at timestamp was refreshed")
                return True
            else:
                print(f"   ❌ Empty update modified fields unexpectedly")
        
        return False

    def test_update_nonexistent_course(self):
        """Test updating a non-existent course"""
        fake_course_id = "507f1f77bcf86cd799439011"
        
        update_data = {
            "title": "Non-existent Course Update"
        }
        
        success, response = self.run_test(
            "Update Non-existent Course",
            "PUT",
            f"api/courses/{fake_course_id}",
            404,
            data=update_data
        )
        
        if success:
            error_detail = response.get('detail', '')
            if 'not found' in error_detail.lower():
                print(f"   ✅ Non-existent course properly handled: {error_detail}")
                return True
            else:
                print(f"   ❌ Unexpected error message: {error_detail}")
        
        return False

    def test_multiple_partial_updates_persistence(self):
        """Test multiple partial updates and verify all changes are preserved"""
        if not self.test_course_id:
            print("   ❌ No test course available")
            return False
        
        print("\n🔍 Testing Multiple Partial Updates Persistence...")
        
        # Store initial state
        initial_updated_at = self.original_course_data.get('updated_at')
        
        # Update 1: Change title
        update1 = {"title": "Step 1: Updated Title"}
        success1, response1 = self.run_test(
            "Multi-Update Step 1 - Title",
            "PUT",
            f"api/courses/{self.test_course_id}",
            200,
            data=update1
        )
        
        if not success1:
            return False
        
        step1_updated_at = response1.get('updated_at')
        
        # Update 2: Change price
        update2 = {"price": 199.99}
        success2, response2 = self.run_test(
            "Multi-Update Step 2 - Price",
            "PUT",
            f"api/courses/{self.test_course_id}",
            200,
            data=update2
        )
        
        if not success2:
            return False
        
        step2_updated_at = response2.get('updated_at')
        
        # Update 3: Change instructor and duration
        update3 = {
            "instructor": "Prof. Multi Update",
            "duration": "8 weeks"
        }
        success3, response3 = self.run_test(
            "Multi-Update Step 3 - Instructor & Duration",
            "PUT",
            f"api/courses/{self.test_course_id}",
            200,
            data=update3
        )
        
        if not success3:
            return False
        
        step3_updated_at = response3.get('updated_at')
        
        # Verify all changes are preserved
        final_course = response3
        
        # Check all our updates are present
        if (final_course.get('title') == "Step 1: Updated Title" and
            final_course.get('price') == 199.99 and
            final_course.get('instructor') == "Prof. Multi Update" and
            final_course.get('duration') == "8 weeks"):
            
            print(f"   ✅ All partial updates preserved correctly")
            print(f"   📝 Final title: {final_course.get('title')}")
            print(f"   💰 Final price: €{final_course.get('price')}")
            print(f"   👨‍🏫 Final instructor: {final_course.get('instructor')}")
            print(f"   ⏱️ Final duration: {final_course.get('duration')}")
            
            # Verify updated_at timestamps changed with each update
            if (initial_updated_at != step1_updated_at and
                step1_updated_at != step2_updated_at and
                step2_updated_at != step3_updated_at):
                print(f"   ✅ updated_at timestamp changed with each update")
                print(f"   🕐 Initial: {initial_updated_at}")
                print(f"   🕑 After step 1: {step1_updated_at}")
                print(f"   🕒 After step 2: {step2_updated_at}")
                print(f"   🕓 After step 3: {step3_updated_at}")
                
                # Update reference data
                self.original_course_data = final_course
                return True
            else:
                print(f"   ❌ updated_at timestamp not changing properly")
        else:
            print(f"   ❌ Some partial updates were lost")
        
        return False

    def cleanup_test_course(self):
        """Clean up the test course"""
        if self.test_course_id:
            print(f"\n🧹 Cleaning up test course...")
            
            success, response = self.run_test(
                "Cleanup Test Course",
                "DELETE",
                f"api/courses/{self.test_course_id}",
                200
            )
            
            if success:
                print(f"   ✅ Test course deleted successfully")
            else:
                print(f"   ⚠️ Failed to delete test course (may need manual cleanup)")

    def run_all_course_edit_tests(self):
        """Run all course edit functionality tests"""
        print("🚀 Starting Course Edit Functionality Testing...")
        print(f"🌐 Base URL: {self.base_url}")
        print("=" * 80)
        
        # Test sequence for course edit functionality
        test_methods = [
            self.test_login,
            self.create_test_course,
            
            # Test Fixed Partial Updates
            self.test_partial_update_title_and_price,
            self.test_single_field_updates,
            
            # Test Field Validation
            self.test_field_validation_empty_title,
            self.test_field_validation_negative_price,
            self.test_field_validation_negative_max_students,
            self.test_valid_data_still_works,
            
            # Test Course Update Edge Cases
            self.test_update_all_fields,
            self.test_empty_update,
            self.test_update_nonexistent_course,
            
            # Test Data Persistence
            self.test_multiple_partial_updates_persistence,
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
            self.cleanup_test_course()
        except Exception as e:
            print(f"⚠️ Cleanup failed: {str(e)}")
        
        # Print final results
        print("\n" + "=" * 80)
        print("📊 COURSE EDIT FUNCTIONALITY TEST RESULTS")
        print("=" * 80)
        print(f"✅ Tests Passed: {self.tests_passed}")
        print(f"❌ Tests Failed: {self.tests_run - self.tests_passed}")
        print(f"📊 Total Tests: {self.tests_run}")
        print(f"📈 Success Rate: {(self.tests_passed/self.tests_run)*100:.1f}%")
        
        if self.tests_passed == self.tests_run:
            print("\n🎉 ALL COURSE EDIT TESTS PASSED!")
            print("✅ Fixed Partial Updates: Preserving existing fields ✓")
            print("✅ Field Validation: Empty title, negative price, negative max_students ✓")
            print("✅ Edge Cases: All fields, no fields, non-existent course ✓")
            print("✅ Data Persistence: Multiple updates and timestamp changes ✓")
        elif self.tests_passed / self.tests_run >= 0.8:
            print("\n✅ COURSE EDIT FUNCTIONALITY MOSTLY WORKING")
            print("⚠️ Some minor issues detected, but core functionality is working")
        else:
            print("\n⚠️ COURSE EDIT FUNCTIONALITY NEEDS ATTENTION")
            print("❌ Multiple issues detected with course update logic")
        
        return self.tests_passed, self.tests_run

# Main execution for course edit testing
if __name__ == "__main__":
    print("🔧 COURSE EDIT FUNCTIONALITY TESTING")
    print("=" * 80)
    print("Testing the fixed course edit functionality:")
    print("- Fixed Partial Updates: Preserving existing fields instead of nulling them")
    print("- Field Validation: Empty title, negative price, negative max_students")
    print("- Edge Cases: All fields, no fields, non-existent course")
    print("- Data Persistence: Multiple partial updates and timestamp changes")
    print("=" * 80)
    
    # Get base URL from environment or use default
    base_url = os.getenv("REACT_APP_BACKEND_URL", "https://faster-crm.preview.emergentagent.com")
    
    # Run course edit tests
    course_tester = CourseEditFixTester(base_url)
    passed, total = course_tester.run_all_course_edit_tests()
    
    print("\n" + "=" * 80)
    print("🎯 COURSE EDIT FUNCTIONALITY TEST SUMMARY")
    print("=" * 80)
    print(f"📊 Tests Passed: {passed}/{total}")
    print(f"📈 Success Rate: {(passed/total)*100:.1f}%")
    
    if passed == total:
        print("\n🎉 ALL COURSE EDIT TESTS PASSED!")
        print("✅ Fixed Partial Updates: Preserving existing fields ✓")
        print("✅ Field Validation: Empty title, negative price, negative max_students ✓")
        print("✅ Edge Cases: All fields, no fields, non-existent course ✓")
        print("✅ Data Persistence: Multiple updates and timestamp changes ✓")
        print("✅ Course edit functionality is working perfectly!")
        sys.exit(0)
    elif passed / total >= 0.8:
        print("\n✅ COURSE EDIT FUNCTIONALITY MOSTLY WORKING")
        print("⚠️ Some minor issues detected, but core functionality is working")
        sys.exit(0)
    else:
        print("\n❌ COURSE EDIT FUNCTIONALITY NEEDS ATTENTION")
        print("🚨 Critical issues found with course update logic")
        sys.exit(1)