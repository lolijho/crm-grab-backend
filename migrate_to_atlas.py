#!/usr/bin/env python3
"""
Migration script from local MongoDB to MongoDB Atlas
Migrates all CRM data: contacts, products, courses, orders, users, etc.
"""

import os
import sys
from pymongo import MongoClient
from datetime import datetime
import json

# Database configurations
OLD_MONGO_URL = "mongodb://localhost:27017/"
OLD_DB_NAME = "crm_db"

NEW_MONGO_URL = "mongodb+srv://codex-admin:DU1uq7KeNthC69rS@crmgrab.yninkne.mongodb.net/crmgrab?retryWrites=true&w=majority&appName=crmgrab"
NEW_DB_NAME = "crmgrab"

def migrate_collection(old_db, new_db, collection_name, description):
    """Migrate a single collection"""
    try:
        print(f"📦 Migrating {description} ({collection_name})...")
        
        # Get source collection
        old_collection = old_db[collection_name]
        document_count = old_collection.count_documents({})
        
        if document_count == 0:
            print(f"   ⚠️  Empty collection - skipping")
            return 0
        
        print(f"   📊 Found {document_count} documents")
        
        # Get all documents
        documents = list(old_collection.find())
        
        # Insert into new database
        new_collection = new_db[collection_name]
        
        # Clear existing data in new collection (optional)
        existing_count = new_collection.count_documents({})
        if existing_count > 0:
            print(f"   🧹 Clearing {existing_count} existing documents")
            new_collection.delete_many({})
        
        # Insert documents in batches
        batch_size = 100
        migrated_count = 0
        
        for i in range(0, len(documents), batch_size):
            batch = documents[i:i + batch_size]
            new_collection.insert_many(batch)
            migrated_count += len(batch)
            print(f"   ✅ Migrated {migrated_count}/{document_count} documents")
        
        print(f"   🎉 Successfully migrated {migrated_count} documents")
        return migrated_count
        
    except Exception as e:
        print(f"   ❌ Error migrating {collection_name}: {e}")
        return 0

def main():
    print("🚀 CRM GRABOVOI FOUNDATION - DATABASE MIGRATION")
    print("=" * 60)
    print(f"📍 FROM: {OLD_MONGO_URL}{OLD_DB_NAME}")
    print(f"📍 TO:   MongoDB Atlas - {NEW_DB_NAME}")
    print("=" * 60)
    
    try:
        # Connect to old database
        print("🔗 Connecting to old database...")
        old_client = MongoClient(OLD_MONGO_URL)
        old_db = old_client[OLD_DB_NAME]
        
        # Test old connection
        old_client.admin.command('ping')
        print("✅ Connected to old database")
        
        # Connect to new database
        print("🔗 Connecting to MongoDB Atlas...")
        new_client = MongoClient(NEW_MONGO_URL)
        new_db = new_client[NEW_DB_NAME]
        
        # Test new connection
        new_client.admin.command('ping')
        print("✅ Connected to MongoDB Atlas")
        
        # Get list of collections to migrate
        collections_to_migrate = [
            ("contacts", "👥 Contatti"),
            ("products", "📦 Prodotti"),
            ("courses", "🎓 Corsi"),
            ("orders", "🛒 Ordini"),
            ("users", "👤 Utenti"),
            ("clients", "🏢 Clienti"),
            ("students", "🎓 Studenti"),
            ("tags", "🏷️  Tag"),
            ("rules", "⚙️  Regole"),
            ("wc_sync_settings", "🔧 Impostazioni WooCommerce"),
            ("deleted_courses", "🗑️  Corsi eliminati"),
            ("password_resets", "🔑 Reset password"),
            ("email_verifications", "📧 Verifiche email"),
        ]
        
        print(f"\n📋 Found {len(collections_to_migrate)} collections to migrate")
        print("-" * 60)
        
        # Start migration
        migration_summary = {}
        total_documents = 0
        successful_collections = 0
        
        for collection_name, description in collections_to_migrate:
            migrated_count = migrate_collection(old_db, new_db, collection_name, description)
            migration_summary[collection_name] = migrated_count
            total_documents += migrated_count
            
            if migrated_count > 0:
                successful_collections += 1
            
            print()  # Empty line for readability
        
        # Migration summary
        print("=" * 60)
        print("🎉 MIGRATION COMPLETED!")
        print("=" * 60)
        print(f"✅ Successfully migrated: {successful_collections} collections")
        print(f"📊 Total documents migrated: {total_documents}")
        print("\n📋 Detailed Summary:")
        
        for collection_name, count in migration_summary.items():
            if count > 0:
                print(f"   ✅ {collection_name}: {count} documents")
            else:
                print(f"   ⚪ {collection_name}: 0 documents (empty)")
        
        # Save migration report
        report = {
            "migration_date": datetime.utcnow().isoformat(),
            "source": f"{OLD_MONGO_URL}{OLD_DB_NAME}",
            "destination": f"MongoDB Atlas - {NEW_DB_NAME}",
            "total_documents": total_documents,
            "successful_collections": successful_collections,
            "details": migration_summary
        }
        
        with open('/app/migration_report.json', 'w') as f:
            json.dump(report, f, indent=2)
        
        print(f"\n💾 Migration report saved to: /app/migration_report.json")
        
        # Close connections
        old_client.close()
        new_client.close()
        
        print("\n🚀 Ready to restart backend with new database!")
        return True
        
    except Exception as e:
        print(f"❌ Migration failed: {e}")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)