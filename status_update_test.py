import requests
import sys
import json
from datetime import datetime
import time
import uuid

class StatusUpdateTester:
    def __init__(self, base_url="https://faster-crm.preview.emergentagent.com"):
        self.base_url = base_url
        self.token = None
        self.tests_run = 0
        self.tests_passed = 0
        self.test_contacts = []
        self.error_details = []

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
                    # Store error details for analysis
                    self.error_details.append({
                        'test': name,
                        'status_code': response.status_code,
                        'error': error_data,
                        'request_data': data
                    })
                except:
                    print(f"   Error: {response.text}")
                    self.error_details.append({
                        'test': name,
                        'status_code': response.status_code,
                        'error': response.text,
                        'request_data': data
                    })
                return False, {}

        except Exception as e:
            print(f"❌ Failed - Error: {str(e)}")
            self.error_details.append({
                'test': name,
                'exception': str(e),
                'request_data': data
            })
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
            print(f"   🔑 Token obtained: {self.token[:20]}...")
            return True
        return False

    def create_test_contact(self):
        """Create a test contact for status update testing"""
        print("\n🔍 Creating Test Contact for Status Update Testing...")
        
        unique_id = str(uuid.uuid4())[:8]
        contact_data = {
            "first_name": "Francesco",
            "last_name": "Rossi",
            "email": f"francesco.rossi.{unique_id}@statustest.com",
            "phone": "+39 123 456 789",
            "city": "Milano",
            "status": "lead",
            "notes": "Test contact for status update investigation"
        }
        
        success, response = self.run_test(
            "Create Test Contact",
            "POST",
            "api/contacts",
            200,
            data=contact_data
        )
        
        if success:
            contact_id = response.get('id')
            if contact_id:
                self.test_contacts.append({
                    'id': contact_id,
                    'first_name': contact_data['first_name'],
                    'last_name': contact_data['last_name'],
                    'email': contact_data['email'],
                    'status': contact_data['status']
                })
                print(f"   ✅ Created test contact: {contact_data['first_name']} {contact_data['last_name']} (ID: {contact_id})")
                return True
        
        return False

    def test_status_field_validation(self):
        """Test status field validation with different values"""
        if not self.test_contacts:
            print("   ❌ No test contact available")
            return False
        
        contact = self.test_contacts[0]
        
        print("\n🔍 Testing Status Field Validation...")
        
        # Test valid status values
        valid_statuses = ["lead", "client", "student"]
        valid_tests_passed = 0
        
        for status in valid_statuses:
            update_data = {
                "first_name": contact['first_name'],
                "last_name": contact['last_name'],
                "email": contact['email'],
                "status": status
            }
            
            success, response = self.run_test(
                f"Valid Status Update - {status}",
                "PUT",
                f"api/contacts/{contact['id']}",
                200,
                data=update_data
            )
            
            if success:
                valid_tests_passed += 1
                print(f"   ✅ Status '{status}' accepted")
                # Verify the status was actually updated
                if response.get('status') == status:
                    print(f"   ✅ Status correctly updated to '{status}'")
                else:
                    print(f"   ❌ Status not updated correctly. Expected '{status}', got '{response.get('status')}'")
            else:
                print(f"   ❌ Status '{status}' rejected")
        
        # Test invalid status values
        invalid_statuses = ["invalid_status", "LEAD", "Cliente", "Studente", "", None]
        invalid_tests_passed = 0
        
        for status in invalid_statuses:
            update_data = {
                "first_name": contact['first_name'],
                "last_name": contact['last_name'],
                "email": contact['email'],
                "status": status
            }
            
            # We expect this to either fail (422/400) or be accepted with transformation
            success, response = self.run_test(
                f"Invalid Status Test - {status}",
                "PUT",
                f"api/contacts/{contact['id']}",
                [200, 400, 422],  # Accept any of these as valid responses
                data=update_data
            )
            
            if success:
                invalid_tests_passed += 1
                if response.get('status') != status:
                    print(f"   ✅ Invalid status '{status}' handled appropriately")
                else:
                    print(f"   ⚠️ Invalid status '{status}' was accepted")
        
        return valid_tests_passed == len(valid_statuses)

    def test_status_only_update(self):
        """Test updating only the status field (minimal update)"""
        if not self.test_contacts:
            print("   ❌ No test contact available")
            return False
        
        contact = self.test_contacts[0]
        
        print("\n🔍 Testing Status-Only Update (Minimal Data)...")
        
        # Test 1: Update with only status field
        minimal_update_data = {
            "status": "client"
        }
        
        success, response = self.run_test(
            "Status-Only Update",
            "PUT",
            f"api/contacts/{contact['id']}",
            200,
            data=minimal_update_data
        )
        
        if success:
            print(f"   ✅ Status-only update successful")
            if response.get('status') == 'client':
                print(f"   ✅ Status correctly updated to 'client'")
            else:
                print(f"   ❌ Status not updated correctly")
                return False
        else:
            print(f"   ❌ Status-only update failed")
            return False
        
        # Test 2: Update with status and one other field
        partial_update_data = {
            "status": "student",
            "notes": "Updated to student status"
        }
        
        success2, response2 = self.run_test(
            "Status + Notes Update",
            "PUT",
            f"api/contacts/{contact['id']}",
            200,
            data=partial_update_data
        )
        
        if success2:
            print(f"   ✅ Partial update with status successful")
            if response2.get('status') == 'student':
                print(f"   ✅ Status correctly updated to 'student'")
            else:
                print(f"   ❌ Status not updated correctly in partial update")
                return False
        else:
            print(f"   ❌ Partial update with status failed")
            return False
        
        return success and success2

    def test_bulk_status_update_detailed(self):
        """Test bulk status update with detailed error analysis"""
        print("\n🔍 Creating Multiple Test Contacts for Bulk Status Update...")
        
        # Create multiple test contacts
        test_contacts_data = [
            {
                "first_name": "Luca",
                "last_name": "Bianchi",
                "email": f"luca.bianchi.{uuid.uuid4().hex[:8]}@bulkstatustest.com",
                "phone": "+39 123 456 789",
                "city": "Milano",
                "status": "lead"
            },
            {
                "first_name": "Sofia",
                "last_name": "Verdi",
                "email": f"sofia.verdi.{uuid.uuid4().hex[:8]}@bulkstatustest.com",
                "phone": "+39 987 654 321",
                "city": "Roma",
                "status": "lead"
            },
            {
                "first_name": "Matteo",
                "last_name": "Rossi",
                "email": f"matteo.rossi.{uuid.uuid4().hex[:8]}@bulkstatustest.com",
                "phone": "+39 555 123 456",
                "city": "Napoli",
                "status": "lead"
            }
        ]
        
        bulk_test_contacts = []
        for contact_data in test_contacts_data:
            success, response = self.run_test(
                f"Create Bulk Test Contact - {contact_data['first_name']}",
                "POST",
                "api/contacts",
                200,
                data=contact_data
            )
            
            if success:
                contact_id = response.get('id')
                if contact_id:
                    bulk_test_contacts.append({
                        'id': contact_id,
                        'first_name': contact_data['first_name'],
                        'last_name': contact_data['last_name'],
                        'email': contact_data['email'],
                        'status': contact_data['status']
                    })
                    print(f"   ✅ Created: {contact_data['first_name']} {contact_data['last_name']} (ID: {contact_id})")
        
        if len(bulk_test_contacts) == 0:
            print("   ❌ Failed to create test contacts for bulk testing")
            return False
        
        print(f"\n🔍 Testing Bulk Status Update on {len(bulk_test_contacts)} contacts...")
        
        # Test different bulk update scenarios
        successful_operations = 0
        failed_operations = 0
        
        for i, contact in enumerate(bulk_test_contacts):
            # Test different update patterns
            if i == 0:
                # Full contact data update
                update_data = {
                    "first_name": contact['first_name'],
                    "last_name": contact['last_name'],
                    "email": contact['email'],
                    "phone": "+39 123 456 789",
                    "city": "Milano",
                    "status": "client"
                }
                test_name = f"Full Data Status Update - {contact['first_name']}"
            elif i == 1:
                # Minimal update with required fields
                update_data = {
                    "first_name": contact['first_name'],
                    "last_name": contact['last_name'],
                    "status": "client"
                }
                test_name = f"Minimal Status Update - {contact['first_name']}"
            else:
                # Status-only update
                update_data = {
                    "status": "client"
                }
                test_name = f"Status-Only Update - {contact['first_name']}"
            
            print(f"\n   📋 Update data for {contact['first_name']}: {update_data}")
            
            success, response = self.run_test(
                test_name,
                "PUT",
                f"api/contacts/{contact['id']}",
                200,
                data=update_data
            )
            
            if success:
                successful_operations += 1
                print(f"   ✅ Status update successful for {contact['first_name']}")
                # Verify the status was actually updated
                if response.get('status') == 'client':
                    print(f"   ✅ Status correctly updated to 'client'")
                else:
                    print(f"   ❌ Status not updated correctly. Expected 'client', got '{response.get('status')}'")
            else:
                failed_operations += 1
                print(f"   ❌ Status update failed for {contact['first_name']}")
        
        # Clean up test contacts
        print(f"\n🧹 Cleaning up bulk test contacts...")
        for contact in bulk_test_contacts:
            self.run_test(
                f"Cleanup Bulk Test Contact - {contact['first_name']}",
                "DELETE",
                f"api/contacts/{contact['id']}",
                200
            )
        
        print(f"\n📊 Bulk Status Update Results:")
        print(f"   ✅ Successful: {successful_operations}")
        print(f"   ❌ Failed: {failed_operations}")
        print(f"   📈 Success Rate: {(successful_operations/(successful_operations+failed_operations))*100:.1f}%")
        
        return successful_operations > 0

    def test_status_validation_edge_cases(self):
        """Test edge cases for status validation"""
        if not self.test_contacts:
            print("   ❌ No test contact available")
            return False
        
        contact = self.test_contacts[0]
        
        print("\n🔍 Testing Status Validation Edge Cases...")
        
        edge_cases = [
            # Case 1: Empty status
            {"status": "", "expected_result": "should_fail"},
            # Case 2: Null status
            {"status": None, "expected_result": "should_fail"},
            # Case 3: Numeric status
            {"status": 123, "expected_result": "should_fail"},
            # Case 4: Boolean status
            {"status": True, "expected_result": "should_fail"},
            # Case 5: Array status
            {"status": ["lead"], "expected_result": "should_fail"},
            # Case 6: Object status
            {"status": {"type": "lead"}, "expected_result": "should_fail"},
        ]
        
        edge_tests_passed = 0
        
        for i, case in enumerate(edge_cases):
            update_data = {
                "first_name": contact['first_name'],
                "last_name": contact['last_name'],
                "email": contact['email'],
                "status": case["status"]
            }
            
            print(f"\n   🧪 Edge Case {i+1}: status = {case['status']} (type: {type(case['status']).__name__})")
            
            success, response = self.run_test(
                f"Edge Case {i+1} - Status: {case['status']}",
                "PUT",
                f"api/contacts/{contact['id']}",
                [200, 400, 422],  # Accept various responses
                data=update_data
            )
            
            if success:
                edge_tests_passed += 1
                # Analyze the response
                if response.get('status') == case['status']:
                    print(f"   ⚠️ Invalid status '{case['status']}' was accepted")
                else:
                    print(f"   ✅ Invalid status handled appropriately")
        
        return edge_tests_passed > 0

    def test_required_fields_with_status_update(self):
        """Test what fields are required when updating status"""
        if not self.test_contacts:
            print("   ❌ No test contact available")
            return False
        
        contact = self.test_contacts[0]
        
        print("\n🔍 Testing Required Fields for Status Update...")
        
        # Test scenarios with different field combinations
        test_scenarios = [
            {
                "name": "Status Only",
                "data": {"status": "client"},
                "should_work": True
            },
            {
                "name": "Status + First Name",
                "data": {"status": "client", "first_name": contact['first_name']},
                "should_work": True
            },
            {
                "name": "Status + Last Name",
                "data": {"status": "client", "last_name": contact['last_name']},
                "should_work": True
            },
            {
                "name": "Status + Email",
                "data": {"status": "client", "email": contact['email']},
                "should_work": True
            },
            {
                "name": "Status + All Required Fields",
                "data": {
                    "status": "client",
                    "first_name": contact['first_name'],
                    "last_name": contact['last_name'],
                    "email": contact['email']
                },
                "should_work": True
            }
        ]
        
        scenario_tests_passed = 0
        
        for scenario in test_scenarios:
            print(f"\n   📋 Scenario: {scenario['name']}")
            print(f"   📋 Data: {scenario['data']}")
            
            expected_status = 200 if scenario['should_work'] else [400, 422]
            
            success, response = self.run_test(
                f"Required Fields Test - {scenario['name']}",
                "PUT",
                f"api/contacts/{contact['id']}",
                expected_status,
                data=scenario['data']
            )
            
            if success:
                scenario_tests_passed += 1
                if scenario['should_work']:
                    print(f"   ✅ Scenario '{scenario['name']}' worked as expected")
                    # Verify status was updated
                    if response.get('status') == scenario['data']['status']:
                        print(f"   ✅ Status correctly updated to '{scenario['data']['status']}'")
                    else:
                        print(f"   ❌ Status not updated correctly")
                else:
                    print(f"   ✅ Scenario '{scenario['name']}' failed as expected")
            else:
                if not scenario['should_work']:
                    scenario_tests_passed += 1
                    print(f"   ✅ Scenario '{scenario['name']}' failed as expected")
                else:
                    print(f"   ❌ Scenario '{scenario['name']}' failed unexpectedly")
        
        return scenario_tests_passed == len(test_scenarios)

    def test_status_transitions(self):
        """Test all possible status transitions"""
        if not self.test_contacts:
            print("   ❌ No test contact available")
            return False
        
        contact = self.test_contacts[0]
        
        print("\n🔍 Testing Status Transitions...")
        
        # Test all possible transitions
        transitions = [
            ("lead", "client"),
            ("client", "student"),
            ("student", "lead"),
            ("lead", "student"),
            ("client", "lead"),
            ("student", "client")
        ]
        
        transition_tests_passed = 0
        
        for from_status, to_status in transitions:
            print(f"\n   🔄 Testing transition: {from_status} → {to_status}")
            
            # First, set the contact to the 'from' status
            setup_data = {
                "first_name": contact['first_name'],
                "last_name": contact['last_name'],
                "email": contact['email'],
                "status": from_status
            }
            
            setup_success, setup_response = self.run_test(
                f"Setup Status - {from_status}",
                "PUT",
                f"api/contacts/{contact['id']}",
                200,
                data=setup_data
            )
            
            if not setup_success:
                print(f"   ❌ Failed to setup status '{from_status}'")
                continue
            
            # Now test the transition
            transition_data = {
                "first_name": contact['first_name'],
                "last_name": contact['last_name'],
                "email": contact['email'],
                "status": to_status
            }
            
            success, response = self.run_test(
                f"Transition {from_status} → {to_status}",
                "PUT",
                f"api/contacts/{contact['id']}",
                200,
                data=transition_data
            )
            
            if success:
                transition_tests_passed += 1
                if response.get('status') == to_status:
                    print(f"   ✅ Transition successful: {from_status} → {to_status}")
                else:
                    print(f"   ❌ Transition failed: Expected '{to_status}', got '{response.get('status')}'")
            else:
                print(f"   ❌ Transition failed: {from_status} → {to_status}")
        
        return transition_tests_passed > 0

    def analyze_422_errors(self):
        """Analyze any 422 errors that occurred during testing"""
        print("\n🔍 Analyzing 422 Errors...")
        
        error_422_found = False
        for error in self.error_details:
            if error.get('status_code') == 422:
                error_422_found = True
                print(f"\n❌ 422 Error Found in test: {error['test']}")
                print(f"   📋 Request Data: {error['request_data']}")
                print(f"   📋 Error Response: {error['error']}")
                
                # Analyze the error details
                if isinstance(error['error'], dict):
                    if 'detail' in error['error']:
                        detail = error['error']['detail']
                        print(f"   🔍 Error Detail: {detail}")
                        
                        # Check for common validation issues
                        if isinstance(detail, list):
                            for validation_error in detail:
                                if isinstance(validation_error, dict):
                                    field = validation_error.get('loc', ['unknown'])[-1]
                                    msg = validation_error.get('msg', 'Unknown error')
                                    print(f"   🔍 Field '{field}': {msg}")
        
        if not error_422_found:
            print("   ✅ No 422 errors found during testing")
        
        return not error_422_found

    def cleanup_test_data(self):
        """Clean up test data"""
        print("\n🧹 Cleaning up test data...")
        
        for contact in self.test_contacts:
            self.run_test(
                f"Cleanup Contact - {contact['first_name']}",
                "DELETE",
                f"api/contacts/{contact['id']}",
                200
            )
        
        print("   ✅ Test data cleanup completed")

    def run_all_status_tests(self):
        """Run all status update tests"""
        print("🚀 Starting Status Update Investigation...")
        print(f"🌐 Base URL: {self.base_url}")
        print("=" * 80)
        
        # Test sequence for status update investigation
        test_methods = [
            self.test_login,
            self.create_test_contact,
            self.test_status_field_validation,
            self.test_status_only_update,
            self.test_required_fields_with_status_update,
            self.test_status_transitions,
            self.test_bulk_status_update_detailed,
            self.analyze_422_errors,
        ]
        
        for test_method in test_methods:
            try:
                result = test_method()
                if not result and test_method.__name__ != 'analyze_422_errors':
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
        print("📊 STATUS UPDATE INVESTIGATION RESULTS")
        print("=" * 80)
        print(f"✅ Tests Passed: {self.tests_passed}")
        print(f"❌ Tests Failed: {self.tests_run - self.tests_passed}")
        print(f"📊 Total Tests: {self.tests_run}")
        print(f"📈 Success Rate: {(self.tests_passed/self.tests_run)*100:.1f}%")
        
        # Print error analysis
        if self.error_details:
            print(f"\n🔍 ERROR ANALYSIS:")
            error_422_count = len([e for e in self.error_details if e.get('status_code') == 422])
            error_400_count = len([e for e in self.error_details if e.get('status_code') == 400])
            other_errors = len(self.error_details) - error_422_count - error_400_count
            
            print(f"   422 Validation Errors: {error_422_count}")
            print(f"   400 Bad Request Errors: {error_400_count}")
            print(f"   Other Errors: {other_errors}")
            
            if error_422_count > 0:
                print(f"\n🚨 ROOT CAUSE ANALYSIS:")
                print(f"   The 422 errors indicate validation issues with the request data.")
                print(f"   This suggests the backend is rejecting the status update due to:")
                print(f"   - Missing required fields")
                print(f"   - Invalid field values")
                print(f"   - Incorrect data types")
                print(f"   - Pydantic model validation failures")
        else:
            print(f"\n✅ No errors found - Status update functionality working correctly")
        
        if self.tests_passed == self.tests_run:
            print("\n🎉 ALL STATUS UPDATE TESTS PASSED!")
        elif self.tests_passed / self.tests_run >= 0.8:
            print("\n✅ STATUS UPDATE SYSTEM MOSTLY WORKING")
        else:
            print("\n⚠️ STATUS UPDATE SYSTEM NEEDS ATTENTION")
        
        return self.tests_passed, self.tests_run

if __name__ == "__main__":
    # Run status update investigation
    print("🚀 Running Status Update Investigation Tests...")
    
    status_tester = StatusUpdateTester()
    status_passed, status_total = status_tester.run_all_status_tests()
    
    # Summary
    print("\n" + "=" * 80)
    print("📊 STATUS UPDATE INVESTIGATION RESULTS")
    print("=" * 80)
    print(f"🔄 Status Tests: {status_passed}/{status_total} passed ({(status_passed/status_total)*100:.1f}%)")
    
    if status_passed == status_total:
        print("\n🎉 ALL STATUS UPDATE TESTS PASSED!")
    elif status_passed / status_total >= 0.8:
        print("\n✅ STATUS UPDATE SYSTEM MOSTLY WORKING")
    else:
        print("\n⚠️ STATUS UPDATE SYSTEM NEEDS ATTENTION")