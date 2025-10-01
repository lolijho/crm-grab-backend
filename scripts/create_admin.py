#!/usr/bin/env python3
"""
Script per creare il primo utente admin del sistema
"""

import sys
import os
import bcrypt
from datetime import datetime
from pymongo import MongoClient
from bson import ObjectId

# Add the backend directory to the path
sys.path.append('/app/backend')

def hash_password(password: str) -> str:
    """Hash password using bcrypt"""
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(password.encode('utf-8'), salt)
    return hashed.decode('utf-8')

def create_admin_user():
    """Create the first admin user"""
    try:
        # Get MongoDB URL from environment
        mongo_url = os.environ.get('MONGO_URL', 'mongodb://localhost:27017/')
        db_name = os.environ.get('DB_NAME', 'grabovoi_crm')
        
        # Connect to MongoDB
        client = MongoClient(mongo_url)
        db = client[db_name]
        users_collection = db.users
        
        # Check if admin user already exists
        existing_admin = users_collection.find_one({"role": "admin"})
        if existing_admin:
            print("✅ Admin user already exists:")
            print(f"   Email: {existing_admin['email']}")
            print(f"   Username: {existing_admin['username']}")
            return
        
        # Create admin user
        admin_user = {
            "username": "admin",
            "email": "admin@grabovoi.com",
            "password": hash_password("admin123"),
            "name": "Administrator",
            "role": "admin",
            "is_verified": True,
            "created_at": datetime.utcnow(),
            "last_login": None
        }
        
        result = users_collection.insert_one(admin_user)
        
        print("🎉 Admin user created successfully!")
        print(f"   User ID: {result.inserted_id}")
        print(f"   Email: admin@grabovoi.com")
        print(f"   Password: admin123")
        print(f"   Username: admin")
        print(f"   Role: admin")
        print("   ✅ Email verified: Yes")
        print()
        print("🔐 You can now login with these credentials and create more users from the Settings page.")
        
        client.close()
        
    except Exception as e:
        print(f"❌ Error creating admin user: {e}")
        return False
    
    return True

if __name__ == "__main__":
    print("🚀 Creating first admin user...")
    print("=" * 50)
    
    success = create_admin_user()
    
    if success:
        print("=" * 50)
        print("✅ Setup completed successfully!")
    else:
        print("❌ Setup failed!")
        sys.exit(1)