import requests
import sys
import json
import time
from datetime import datetime

class CourseContactAssociationTester:
    def __init__(self, base_url="https://faster-crm.preview.emergentagent.com"):
        self.base_url = base_url
        self.token = None
        self.tests_run = 0
        self.tests_passed = 0
        self.user_id = None
        self.test_course_id = None
        self.test_contact_ids = []
        self.test_enrollment_ids = []

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
                    elif isinstance(response_data, dict):
                        print(f"   Response: Dict with keys: {list(response_data.keys())}")
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

    def setup_test_data(self):
        """Create test course and contacts for association testing"""
        print("\n🔍 Setting up test data...")
        
        # First, check if "Corso Base Grabovoi CRM" already exists
        success, response = self.run_test(
            "Get Existing Courses",
            "GET",
            "api/courses",
            200
        )
        
        existing_course = None
        if success and isinstance(response, list):
            for course in response:
                if "Corso Base Grabovoi CRM" in course.get('title', ''):
                    existing_course = course
                    break
        
        if existing_course:
            self.test_course_id = existing_course['id']
            print(f"   ✅ Found existing course: {existing_course['title']} (ID: {self.test_course_id})")
        else:
            # Create the test course
            course_data = {
                "title": "Corso Base Grabovoi CRM",
                "description": "Corso di base per testare le associazioni corso-contatto",
                "instructor": "Grigori Grabovoi",
                "duration": "4 settimane",
                "price": 299.99,
                "category": "Formazione Base",
                "language": "Italian",
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
                print(f"   ✅ Created test course: {course_data['title']} (ID: {self.test_course_id})")
            else:
                print(f"   ❌ Failed to create test course")
                return False
        
        # Create test contacts
        test_contacts_data = [
            {
                "first_name": "Mario",
                "last_name": "Rossi",
                "email": "mario.rossi@testcorso.com",
                "phone": "+39 123 456 789",
                "city": "Milano",
                "status": "lead",
                "notes": "Contatto test per associazione corso"
            },
            {
                "first_name": "Giulia",
                "last_name": "Bianchi",
                "email": "giulia.bianchi@testcorso.com",
                "phone": "+39 987 654 321",
                "city": "Roma",
                "status": "client",
                "notes": "Contatto test per associazione corso"
            },
            {
                "first_name": "Francesco",
                "last_name": "Verdi",
                "email": "francesco.verdi@testcorso.com",
                "phone": "+39 555 123 456",
                "city": "Napoli",
                "status": "lead",
                "notes": "Contatto test per associazione corso"
            }
        ]
        
        for contact_data in test_contacts_data:
            success, response = self.run_test(
                f"Create Test Contact - {contact_data['first_name']} {contact_data['last_name']}",
                "POST",
                "api/contacts",
                200,
                data=contact_data
            )
            
            if success:
                contact_id = response.get('id')
                self.test_contact_ids.append(contact_id)
                print(f"   ✅ Created contact: {contact_data['first_name']} {contact_data['last_name']} (ID: {contact_id})")
        
        return len(self.test_contact_ids) > 0 and self.test_course_id is not None

    def test_get_course_students_empty(self):
        """Test GET /api/courses/{course_id}/students - Should return empty initially"""
        if not self.test_course_id:
            print("   ❌ No test course ID available")
            return False
        
        success, response = self.run_test(
            "Get Course Students - Empty Initially",
            "GET",
            f"api/courses/{self.test_course_id}/students",
            200
        )
        
        if success:
            # Verify response structure
            expected_fields = ['course', 'students', 'total_enrolled']
            for field in expected_fields:
                if field not in response:
                    print(f"   ❌ Missing response field: {field}")
                    return False
            
            course_info = response.get('course', {})
            students = response.get('students', [])
            total_enrolled = response.get('total_enrolled', 0)
            
            print(f"   📚 Course: {course_info.get('title', 'N/A')}")
            print(f"   👥 Students enrolled: {total_enrolled}")
            print(f"   📊 Students list: {len(students)} items")
            
            return True
        
        return False

    def test_enroll_contact_in_course(self):
        """Test POST /api/courses/{course_id}/enroll/{contact_id} - Enroll contacts in course"""
        if not self.test_course_id or not self.test_contact_ids:
            print("   ❌ No test course or contacts available")
            return False
        
        successful_enrollments = 0
        
        for contact_id in self.test_contact_ids:
            success, response = self.run_test(
                f"Enroll Contact in Course - Contact ID: {contact_id}",
                "POST",
                f"api/courses/{self.test_course_id}/enroll/{contact_id}",
                200
            )
            
            if success:
                # Verify response structure
                expected_fields = ['id', 'contact_id', 'course_id', 'enrolled_at', 'status', 'source', 'course']
                for field in expected_fields:
                    if field not in response:
                        print(f"   ❌ Missing response field: {field}")
                        return False
                
                enrollment_id = response.get('id')
                course_info = response.get('course', {})
                
                if enrollment_id:
                    self.test_enrollment_ids.append(enrollment_id)
                    successful_enrollments += 1
                    print(f"   ✅ Enrollment created: ID {enrollment_id}")
                    print(f"   📚 Course: {course_info.get('title', 'N/A')}")
                    print(f"   📅 Enrolled at: {response.get('enrolled_at', 'N/A')}")
                    print(f"   🔄 Status: {response.get('status', 'N/A')}")
                    print(f"   📝 Source: {response.get('source', 'N/A')}")
        
        if successful_enrollments == len(self.test_contact_ids):
            print(f"   ✅ All contacts enrolled successfully: {successful_enrollments}/{len(self.test_contact_ids)}")
            return True
        else:
            print(f"   ❌ Enrollment failed: {successful_enrollments}/{len(self.test_contact_ids)}")
            return False

    def test_get_course_students_with_enrollments(self):
        """Test GET /api/courses/{course_id}/students - Should return enrolled students"""
        if not self.test_course_id:
            print("   ❌ No test course ID available")
            return False
        
        success, response = self.run_test(
            "Get Course Students - With Enrollments",
            "GET",
            f"api/courses/{self.test_course_id}/students",
            200
        )
        
        if success:
            course_info = response.get('course', {})
            students = response.get('students', [])
            total_enrolled = response.get('total_enrolled', 0)
            
            print(f"   📚 Course: {course_info.get('title', 'N/A')}")
            print(f"   👥 Students enrolled: {total_enrolled}")
            print(f"   📊 Students list: {len(students)} items")
            
            # Verify we have the expected number of students
            if total_enrolled != len(self.test_contact_ids):
                print(f"   ❌ Expected {len(self.test_contact_ids)} students, got {total_enrolled}")
                return False
            
            # Verify student structure
            if len(students) > 0:
                student = students[0]
                expected_fields = ['id', 'first_name', 'last_name', 'email', 'status', 'enrollment']
                for field in expected_fields:
                    if field not in student:
                        print(f"   ❌ Missing student field: {field}")
                        return False
                
                enrollment = student.get('enrollment', {})
                enrollment_fields = ['id', 'contact_id', 'course_id', 'enrolled_at', 'status', 'source']
                for field in enrollment_fields:
                    if field not in enrollment:
                        print(f"   ❌ Missing enrollment field: {field}")
                        return False
                
                print(f"   ✅ Student structure correct")
                print(f"   👤 First student: {student.get('first_name')} {student.get('last_name')}")
                print(f"   📧 Email: {student.get('email')}")
                print(f"   🔄 Status: {student.get('status')}")
            
            return True
        
        return False

    def test_get_contact_courses(self):
        """Test GET /api/contacts/{contact_id}/courses - Get courses for each contact"""
        if not self.test_contact_ids:
            print("   ❌ No test contacts available")
            return False
        
        successful_tests = 0
        
        for contact_id in self.test_contact_ids:
            success, response = self.run_test(
                f"Get Contact Courses - Contact ID: {contact_id}",
                "GET",
                f"api/contacts/{contact_id}/courses",
                200
            )
            
            if success:
                courses = response if isinstance(response, list) else []
                print(f"   📚 Courses for contact {contact_id}: {len(courses)}")
                
                if len(courses) > 0:
                    course = courses[0]
                    expected_fields = ['id', 'title', 'instructor', 'price', 'enrollment']
                    for field in expected_fields:
                        if field not in course:
                            print(f"   ❌ Missing course field: {field}")
                            return False
                    
                    enrollment = course.get('enrollment', {})
                    enrollment_fields = ['id', 'contact_id', 'course_id', 'enrolled_at', 'status', 'source']
                    for field in enrollment_fields:
                        if field not in enrollment:
                            print(f"   ❌ Missing enrollment field: {field}")
                            return False
                    
                    print(f"   ✅ Course structure correct")
                    print(f"   📚 Course: {course.get('title', 'N/A')}")
                    print(f"   👨‍🏫 Instructor: {course.get('instructor', 'N/A')}")
                    print(f"   💰 Price: €{course.get('price', 0)}")
                    print(f"   📅 Enrolled: {enrollment.get('enrolled_at', 'N/A')}")
                    
                    successful_tests += 1
                else:
                    print(f"   ❌ No courses found for contact {contact_id}")
        
        if successful_tests == len(self.test_contact_ids):
            print(f"   ✅ All contacts have courses: {successful_tests}/{len(self.test_contact_ids)}")
            return True
        else:
            print(f"   ❌ Some contacts missing courses: {successful_tests}/{len(self.test_contact_ids)}")
            return False

    def test_get_all_enrollments(self):
        """Test GET /api/enrollments - Get all enrollments with filters"""
        # Test 1: Get all enrollments
        success1, response1 = self.run_test(
            "Get All Enrollments - No Filters",
            "GET",
            "api/enrollments",
            200
        )
        
        if not success1:
            return False
        
        # Verify response structure
        expected_fields = ['enrollments', 'total']
        for field in expected_fields:
            if field not in response1:
                print(f"   ❌ Missing response field: {field}")
                return False
        
        enrollments = response1.get('enrollments', [])
        total = response1.get('total', 0)
        
        print(f"   📊 Total enrollments: {total}")
        print(f"   📋 Enrollments list: {len(enrollments)} items")
        
        if len(enrollments) > 0:
            enrollment = enrollments[0]
            expected_fields = ['id', 'contact_id', 'course_id', 'enrolled_at', 'status', 'source', 'course', 'contact']
            for field in expected_fields:
                if field not in enrollment:
                    print(f"   ❌ Missing enrollment field: {field}")
                    return False
            
            course_info = enrollment.get('course', {})
            contact_info = enrollment.get('contact', {})
            
            print(f"   ✅ Enrollment structure correct")
            print(f"   📚 Course: {course_info.get('title', 'N/A')}")
            print(f"   👤 Contact: {contact_info.get('first_name', 'N/A')} {contact_info.get('last_name', 'N/A')}")
        
        # Test 2: Filter by course_id
        if self.test_course_id:
            success2, response2 = self.run_test(
                "Get Enrollments - Filter by Course ID",
                "GET",
                f"api/enrollments?course_id={self.test_course_id}",
                200
            )
            
            if success2:
                filtered_enrollments = response2.get('enrollments', [])
                filtered_total = response2.get('total', 0)
                
                print(f"   📊 Filtered enrollments (course): {filtered_total}")
                
                # Should match our test enrollments
                if filtered_total != len(self.test_contact_ids):
                    print(f"   ❌ Expected {len(self.test_contact_ids)} enrollments, got {filtered_total}")
                    return False
                
                print(f"   ✅ Course filter working correctly")
        
        # Test 3: Filter by contact_id
        if self.test_contact_ids:
            contact_id = self.test_contact_ids[0]
            success3, response3 = self.run_test(
                "Get Enrollments - Filter by Contact ID",
                "GET",
                f"api/enrollments?contact_id={contact_id}",
                200
            )
            
            if success3:
                contact_enrollments = response3.get('enrollments', [])
                contact_total = response3.get('total', 0)
                
                print(f"   📊 Contact enrollments: {contact_total}")
                
                if contact_total > 0:
                    print(f"   ✅ Contact filter working correctly")
                else:
                    print(f"   ❌ No enrollments found for contact {contact_id}")
                    return False
        
        # Test 4: Filter by status
        success4, response4 = self.run_test(
            "Get Enrollments - Filter by Status",
            "GET",
            "api/enrollments?status=active",
            200
        )
        
        if success4:
            active_enrollments = response4.get('enrollments', [])
            active_total = response4.get('total', 0)
            
            print(f"   📊 Active enrollments: {active_total}")
            print(f"   ✅ Status filter working correctly")
        
        return success1 and (not self.test_course_id or success2) and (not self.test_contact_ids or success3) and success4

    def test_cancel_enrollment(self):
        """Test DELETE /api/enrollments/{enrollment_id} - Cancel an enrollment"""
        if not self.test_enrollment_ids:
            print("   ❌ No test enrollment IDs available")
            return False
        
        # Cancel the first enrollment
        enrollment_id = self.test_enrollment_ids[0]
        
        success, response = self.run_test(
            f"Cancel Enrollment - ID: {enrollment_id}",
            "DELETE",
            f"api/enrollments/{enrollment_id}",
            200
        )
        
        if success:
            # Verify response structure
            if 'message' not in response:
                print(f"   ❌ Missing message in response")
                return False
            
            message = response.get('message', '')
            print(f"   ✅ Enrollment cancelled successfully")
            print(f"   📝 Message: {message}")
            
            # Verify the enrollment is actually cancelled by checking enrollments
            verify_success, verify_response = self.run_test(
                "Verify Enrollment Cancelled",
                "GET",
                "api/enrollments",
                200
            )
            
            if verify_success:
                enrollments = verify_response.get('enrollments', [])
                cancelled_enrollment = None
                
                for enrollment in enrollments:
                    if enrollment.get('id') == enrollment_id:
                        cancelled_enrollment = enrollment
                        break
                
                if cancelled_enrollment:
                    if cancelled_enrollment.get('status') == 'cancelled':
                        print(f"   ✅ Enrollment status updated to 'cancelled'")
                        print(f"   📅 Cancelled at: {cancelled_enrollment.get('cancelled_at', 'N/A')}")
                        return True
                    else:
                        print(f"   ❌ Enrollment status not updated: {cancelled_enrollment.get('status')}")
                        return False
                else:
                    print(f"   ❌ Cancelled enrollment not found in list")
                    return False
        
        return False

    def test_error_handling(self):
        """Test error handling for invalid IDs and scenarios"""
        print("\n🔍 Testing Error Handling...")
        
        fake_id = "507f1f77bcf86cd799439011"
        
        # Test 1: Non-existent course ID
        success1, response1 = self.run_test(
            "Get Students - Non-existent Course",
            "GET",
            f"api/courses/{fake_id}/students",
            404
        )
        
        # Test 2: Non-existent contact ID for courses
        success2, response2 = self.run_test(
            "Get Courses - Non-existent Contact",
            "GET",
            f"api/contacts/{fake_id}/courses",
            200  # Should return empty list
        )
        
        # Test 3: Non-existent enrollment ID
        success3, response3 = self.run_test(
            "Cancel Non-existent Enrollment",
            "DELETE",
            f"api/enrollments/{fake_id}",
            404
        )
        
        # Test 4: Enroll non-existent contact
        if self.test_course_id:
            success4, response4 = self.run_test(
                "Enroll Non-existent Contact",
                "POST",
                f"api/courses/{self.test_course_id}/enroll/{fake_id}",
                404
            )
        else:
            success4 = True
        
        # Test 5: Enroll contact in non-existent course
        if self.test_contact_ids:
            success5, response5 = self.run_test(
                "Enroll in Non-existent Course",
                "POST",
                f"api/courses/{fake_id}/enroll/{self.test_contact_ids[0]}",
                404
            )
        else:
            success5 = True
        
        if success1 and success2 and success3 and success4 and success5:
            print(f"   ✅ Error handling working correctly")
            return True
        else:
            print(f"   ❌ Some error handling tests failed")
            return False

    def test_contact_status_transformation(self):
        """Test that contacts are transformed to 'student' status when enrolled"""
        if not self.test_contact_ids:
            print("   ❌ No test contacts available")
            return False
        
        successful_checks = 0
        
        for contact_id in self.test_contact_ids:
            success, response = self.run_test(
                f"Check Contact Status - ID: {contact_id}",
                "GET",
                f"api/contacts/{contact_id}",
                200
            )
            
            if success:
                contact_status = response.get('status', '')
                print(f"   👤 Contact {contact_id} status: {contact_status}")
                
                if contact_status == 'student':
                    print(f"   ✅ Contact transformed to student status")
                    successful_checks += 1
                else:
                    print(f"   ❌ Contact not transformed to student: {contact_status}")
        
        if successful_checks == len(self.test_contact_ids):
            print(f"   ✅ All contacts transformed to student status: {successful_checks}/{len(self.test_contact_ids)}")
            return True
        else:
            print(f"   ❌ Some contacts not transformed: {successful_checks}/{len(self.test_contact_ids)}")
            return False

    def cleanup_test_data(self):
        """Clean up test data"""
        print("\n🧹 Cleaning up test data...")
        
        # Delete test contacts
        for contact_id in self.test_contact_ids:
            success, response = self.run_test(
                f"Delete Test Contact - ID: {contact_id}",
                "DELETE",
                f"api/contacts/{contact_id}",
                200
            )
            
            if success:
                print(f"   ✅ Deleted contact: {contact_id}")
            else:
                print(f"   ⚠️ Failed to delete contact: {contact_id}")
        
        # Note: We don't delete the course as it might be the existing "Corso Base Grabovoi CRM"
        # that was mentioned in the review request
        
        print(f"   📊 Cleanup completed")

    def run_all_course_contact_tests(self):
        """Run all course-contact association tests"""
        print("🚀 Starting Course-Contact Association Testing...")
        print(f"🌐 Base URL: {self.base_url}")
        print("=" * 80)
        
        # Test sequence
        test_methods = [
            self.test_login,
            self.setup_test_data,
            self.test_get_course_students_empty,
            self.test_enroll_contact_in_course,
            self.test_get_course_students_with_enrollments,
            self.test_get_contact_courses,
            self.test_get_all_enrollments,
            self.test_contact_status_transformation,
            self.test_cancel_enrollment,
            self.test_error_handling,
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
        print("📊 COURSE-CONTACT ASSOCIATION TEST RESULTS")
        print("=" * 80)
        print(f"✅ Tests Passed: {self.tests_passed}")
        print(f"❌ Tests Failed: {self.tests_run - self.tests_passed}")
        print(f"📊 Total Tests: {self.tests_run}")
        print(f"📈 Success Rate: {(self.tests_passed/self.tests_run)*100:.1f}%")
        
        if self.tests_passed == self.tests_run:
            print("\n🎉 ALL COURSE-CONTACT ASSOCIATION TESTS PASSED!")
        elif self.tests_passed / self.tests_run >= 0.8:
            print("\n✅ COURSE-CONTACT ASSOCIATION SYSTEM MOSTLY WORKING")
        else:
            print("\n⚠️ COURSE-CONTACT ASSOCIATION SYSTEM NEEDS ATTENTION")
        
        return self.tests_passed, self.tests_run

if __name__ == "__main__":
    tester = CourseContactAssociationTester()
    passed, total = tester.run_all_course_contact_tests()
    
    # Exit with appropriate code
    if passed == total:
        sys.exit(0)
    else:
        sys.exit(1)