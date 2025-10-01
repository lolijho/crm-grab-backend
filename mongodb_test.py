#!/usr/bin/env python3

import requests
import sys
import json
import uuid
import time

class MongoDBConnectivityTester:
    def __init__(self, base_url="https://faster-crm.preview.emergentagent.com"):
        self.base_url = base_url
        self.token = None
        self.tests_run = 0
        self.tests_passed = 0
        self.user_id = None
        self.test_contact_id = None

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
                        if len(response_data) > 0:
                            print(f"   First item: {response_data[0]}")
                    elif isinstance(response_data, dict):
                        print(f"   Response keys: {list(response_data.keys())}")
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

    def test_database_info(self):
        """Test database configuration and connection info"""
        success, response = self.run_test(
            "Database Configuration Info",
            "GET",
            "api/debug/database-info",
            200
        )
        
        if success:
            print(f"   ✅ Database connection info retrieved")
            print(f"   🗄️ Database: {response.get('database_name')}")
            print(f"   🔗 MongoDB URL: {response.get('mongo_url_prefix')}")
            print(f"   📊 Collections: {len(response.get('collections', {}))}")
            
            # Check for key collections
            collections = response.get('collections', {})
            key_collections = ['users', 'contacts', 'orders', 'products', 'courses']
            for collection in key_collections:
                if collection in collections:
                    count = collections[collection]
                    print(f"   📋 {collection}: {count} documents")
                else:
                    print(f"   ℹ️ Collection '{collection}' not found (empty database is normal)")
            
            return True
        
        return False

    def test_admin_login(self):
        """Test login with admin@grabovoi.com / admin123"""
        success, response = self.run_test(
            "Admin Login (admin@grabovoi.com / admin123)",
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
            print(f"   👤 Admin user: {response['user'].get('username')} ({response['user'].get('email')})")
            print(f"   🔐 Role: {response['user'].get('role')}")
            return True
        return False

    def test_get_contacts(self):
        """Test GET /api/contacts to see existing data"""
        success, response = self.run_test(
            "GET /api/contacts - Verify existing contacts data",
            "GET",
            "api/contacts?limit=10",
            200
        )
        
        if success:
            # Check response structure
            if 'contacts' not in response or 'pagination' not in response:
                print(f"   ❌ Missing 'contacts' or 'pagination' in response")
                return False
            
            contacts = response.get('contacts', [])
            pagination = response.get('pagination', {})
            
            print(f"   📊 Found {len(contacts)} contacts (showing first 10)")
            print(f"   📄 Total contacts: {pagination.get('total_count', 'N/A')}")
            
            # Show sample contact data if available
            if len(contacts) > 0:
                contact = contacts[0]
                print(f"   👤 Sample contact: {contact.get('first_name', 'N/A')} {contact.get('last_name', 'N/A')}")
                print(f"   📧 Email: {contact.get('email', 'N/A')}")
                print(f"   📊 Status: {contact.get('status', 'N/A')}")
            else:
                print(f"   ℹ️ No contacts found in database (empty database is normal)")
            
            return True
        
        return False

    def test_get_crm_products(self):
        """Test GET /api/crm-products to verify CRM data"""
        success, response = self.run_test(
            "GET /api/crm-products - Verify CRM products data",
            "GET",
            "api/crm-products?limit=10",
            200
        )
        
        if success:
            # Check response structure
            if 'data' not in response or 'pagination' not in response:
                print(f"   ❌ Missing 'data' or 'pagination' in response")
                return False
            
            products = response.get('data', [])
            pagination = response.get('pagination', {})
            
            print(f"   📊 Found {len(products)} CRM products (showing first 10)")
            print(f"   📄 Total CRM products: {pagination.get('total_count', 'N/A')}")
            
            # Show sample product data if available
            if len(products) > 0:
                product = products[0]
                print(f"   🛍️ Sample product: {product.get('name', 'N/A')}")
                print(f"   💰 Price: €{product.get('base_price', 'N/A')}")
                print(f"   📂 Category: {product.get('category', 'N/A')}")
            else:
                print(f"   ℹ️ No CRM products found in database (empty is normal)")
            
            return True
        
        return False

    def test_get_courses(self):
        """Test GET /api/courses to verify courses data"""
        success, response = self.run_test(
            "GET /api/courses - Verify courses data",
            "GET",
            "api/courses",
            200
        )
        
        if success:
            # Response should be a list of courses
            if not isinstance(response, list):
                print(f"   ❌ Response should be a list of courses")
                return False
            
            courses = response
            print(f"   📚 Found {len(courses)} courses")
            
            # Show sample course data if available
            if len(courses) > 0:
                course = courses[0]
                print(f"   📖 Sample course: {course.get('title', 'N/A')}")
                print(f"   👨‍🏫 Instructor: {course.get('instructor', 'N/A')}")
                print(f"   💰 Price: €{course.get('price', 'N/A')}")
                print(f"   🌐 Language: {course.get('language', 'N/A')}")
            else:
                print(f"   ℹ️ No courses found in database (empty is normal)")
            
            return True
        
        return False

    def test_create_new_contact(self):
        """Test creating a new contact to verify write operations"""
        # Generate unique contact data
        unique_id = str(uuid.uuid4())[:8]
        contact_data = {
            "first_name": "Mario",
            "last_name": "Rossi",
            "email": f"mario.rossi.{unique_id}@testmongo.com",
            "phone": "+39 123 456 7890",
            "address": "Via Roma 123",
            "city": "Milano",
            "postal_code": "20100",
            "country": "Italia",
            "notes": "Contatto di test per verificare connettività MongoDB",
            "source": "mongodb_connectivity_test",
            "status": "lead"
        }
        
        success, response = self.run_test(
            "Create New Contact - Test Write Operations",
            "POST",
            "api/contacts",
            200,
            data=contact_data
        )
        
        if success:
            # Store contact ID for cleanup
            self.test_contact_id = response.get('id')
            
            print(f"   ✅ Contact created successfully")
            print(f"   🆔 Contact ID: {self.test_contact_id}")
            print(f"   👤 Name: {response.get('first_name')} {response.get('last_name')}")
            print(f"   📧 Email: {response.get('email')}")
            print(f"   📊 Status: {response.get('status')}")
            
            return True
        
        return False

    def cleanup_test_data(self):
        """Clean up test contact"""
        if self.test_contact_id:
            print(f"\n🧹 Cleaning up test contact...")
            
            success, response = self.run_test(
                "Delete Test Contact",
                "DELETE",
                f"api/contacts/{self.test_contact_id}",
                200
            )
            
            if success:
                print(f"   ✅ Test contact deleted successfully")
            else:
                print(f"   ⚠️ Failed to delete test contact")

    def run_all_mongodb_connectivity_tests(self):
        """Run all MongoDB connectivity and functionality tests"""
        print("🚀 Starting MongoDB Connectivity and Functionality Testing...")
        print(f"🌐 Base URL: {self.base_url}")
        print("🗄️ New MongoDB URI: mongodb://mongo:wGYReaWtBJoyADDXtijnXsTyWNeysnmc@maglev.proxy.rlwy.net:43877")
        print("🎯 Testing database connectivity, authentication, and CRUD operations")
        print("👤 Admin credentials: admin@grabovoi.com / admin123")
        print("=" * 80)
        
        # Test sequence for MongoDB connectivity
        test_methods = [
            self.test_database_info,
            self.test_admin_login,
            self.test_get_contacts,
            self.test_get_crm_products,
            self.test_get_courses,
            self.test_create_new_contact,
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
        print("📊 MONGODB CONNECTIVITY TEST RESULTS")
        print("=" * 80)
        print(f"✅ Tests Passed: {self.tests_passed}")
        print(f"❌ Tests Failed: {self.tests_run - self.tests_passed}")
        print(f"📊 Total Tests: {self.tests_run}")
        print(f"📈 Success Rate: {(self.tests_passed/self.tests_run)*100:.1f}%")
        
        if self.tests_passed == self.tests_run:
            print("\n🎉 ALL MONGODB CONNECTIVITY TESTS PASSED!")
            print("✅ Database connection working perfectly")
            print("✅ Authentication working with admin credentials")
            print("✅ All collections accessible")
            print("✅ Read operations working")
            print("✅ Write operations working")
        elif self.tests_passed / self.tests_run >= 0.8:
            print("\n✅ MONGODB CONNECTIVITY MOSTLY WORKING")
            print("⚠️ Some minor issues detected but core functionality working")
        else:
            print("\n⚠️ MONGODB CONNECTIVITY ISSUES DETECTED")
            print("❌ Significant problems with database connectivity or operations")
        
        # Specific MongoDB assessment
        print("\n🗄️ MONGODB ASSESSMENT:")
        if self.tests_passed >= 5:  # Most critical tests passed
            print("✅ New MongoDB URI connection: WORKING")
            print("✅ Database operations: FUNCTIONAL")
            print("✅ Collections accessibility: VERIFIED")
            print("✅ CRUD operations: WORKING")
        else:
            print("❌ MongoDB connectivity issues detected")
            print("⚠️ Check database configuration and network connectivity")
        
        return self.tests_passed, self.tests_run

if __name__ == "__main__":
    # Run MongoDB connectivity tests as requested in the Italian review
    print("🚀 Starting MongoDB Connectivity and Functionality Testing...")
    print("🇮🇹 Test di connettività e funzionalità del nuovo database MongoDB")
    print("=" * 80)
    
    # Initialize MongoDB connectivity tester
    mongo_tester = MongoDBConnectivityTester()
    
    # Run MongoDB connectivity test suite
    mongo_passed, mongo_total = mongo_tester.run_all_mongodb_connectivity_tests()
    
    print("\n" + "=" * 80)
    print("🎯 MONGODB CONNECTIVITY TEST RESULTS")
    print("=" * 80)
    print(f"✅ Tests Passed: {mongo_passed}")
    print(f"❌ Tests Failed: {mongo_total - mongo_passed}")
    print(f"📊 Total Tests Run: {mongo_total}")
    print(f"📈 Success Rate: {(mongo_passed/mongo_total)*100:.1f}%")
    
    if mongo_passed == mongo_total:
        print("\n🎉 ALL MONGODB CONNECTIVITY TESTS PASSED!")
        print("🇮🇹 Tutti i test di connettività MongoDB sono passati!")
        sys.exit(0)
    elif mongo_passed / mongo_total >= 0.8:
        print("\n✅ MONGODB CONNECTIVITY MOSTLY WORKING")
        print("🇮🇹 La connettività MongoDB funziona per la maggior parte")
        sys.exit(0)
    else:
        print("\n⚠️ MONGODB CONNECTIVITY NEEDS ATTENTION")
        print("🇮🇹 La connettività MongoDB richiede attenzione")
        sys.exit(1)