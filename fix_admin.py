#!/usr/bin/env python3

from pymongo import MongoClient
import os
from datetime import datetime

# MongoDB connection
MONGO_URL = os.getenv("MONGO_URL", "mongodb://localhost:27017/")
DB_NAME = os.getenv("DB_NAME", "grabovoi_crm")
client = MongoClient(MONGO_URL)
db = client[DB_NAME]

def fix_admin_user():
    """Fix admin user to be verified and have proper fields"""
    print("Fixing admin user...")
    
    # Find admin user
    admin_user = db.users.find_one({"email": "admin@grabovoi.com"})
    
    if not admin_user:
        print("❌ Admin user not found!")
        return False
    
    # Update admin user to be verified and have proper fields
    update_data = {
        "is_verified": True,
        "username": admin_user.get("username", "admin"),
        "updated_at": datetime.utcnow()
    }
    
    # Add username if missing
    if "username" not in admin_user:
        update_data["username"] = "admin"
    
    result = db.users.update_one(
        {"email": "admin@grabovoi.com"},
        {"$set": update_data}
    )
    
    if result.modified_count > 0:
        print("✅ Admin user updated successfully!")
        print("   - is_verified: True")
        print("   - username: admin")
        return True
    else:
        print("ℹ️  Admin user was already up to date")
        return True

if __name__ == "__main__":
    fix_admin_user()