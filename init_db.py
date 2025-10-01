from pymongo import MongoClient
import bcrypt
from datetime import datetime
import os

# MongoDB connection
MONGO_URL = os.getenv("MONGO_URL", "mongodb://localhost:27017/")
DB_NAME = os.getenv("DB_NAME", "grabovoi_crm")
client = MongoClient(MONGO_URL)
db = client[DB_NAME]

def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

def init_database():
    print("Initializing database with sample data...")
    
    # Create admin user
    admin_user = {
        "name": "Amministratore",
        "email": "admin@grabovoi.com",
        "password": hash_password("admin123"),
        "role": "admin",
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow()
    }
    
    # Check if admin already exists
    existing_admin = db.users.find_one({"email": "admin@grabovoi.com"})
    if not existing_admin:
        db.users.insert_one(admin_user)
        print("✅ Created admin user: admin@grabovoi.com / admin123")
    else:
        print("ℹ️  Admin user already exists")
    
    # Create sample tags
    sample_tags = [
        {"name": "Lead Caldo", "category": "status", "color": "#EF4444", "created_at": datetime.utcnow()},
        {"name": "Cliente VIP", "category": "status", "color": "#10B981", "created_at": datetime.utcnow()},
        {"name": "Sito Web", "category": "source", "color": "#3B82F6", "created_at": datetime.utcnow()},
        {"name": "Social Media", "category": "source", "color": "#8B5CF6", "created_at": datetime.utcnow()},
        {"name": "Numerologia", "category": "interest", "color": "#F59E0B", "created_at": datetime.utcnow()},
    ]
    
    for tag in sample_tags:
        existing_tag = db.tags.find_one({"name": tag["name"]})
        if not existing_tag:
            db.tags.insert_one(tag)
            print(f"✅ Created tag: {tag['name']}")
    
    # Create sample products
    sample_products = [
        {
            "name": "Corso Base Grabovoi",
            "description": "Introduzione ai metodi di Grigori Grabovoi",
            "price": 97.0,
            "category": "Corsi",
            "sku": "CORSO-BASE-001",
            "is_active": True,
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        },
        {
            "name": "Libro Sequenze Numeriche",
            "description": "Collezione completa delle sequenze numeriche",
            "price": 29.99,
            "category": "Libri",
            "sku": "LIBRO-SEQ-001",
            "is_active": True,
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        }
    ]
    
    for product in sample_products:
        existing_product = db.products.find_one({"sku": product["sku"]})
        if not existing_product:
            db.products.insert_one(product)
            print(f"✅ Created product: {product['name']}")
    
    # Create sample courses
    sample_courses = [
        {
            "title": "Numerologia Applicata",
            "description": "Corso completo di numerologia con metodi pratici",
            "instructor": "Dr. Maria Rossi",
            "duration": "8 settimane",
            "price": 147.0,
            "category": "Numerologia",
            "is_active": True,
            "max_students": 20,
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        },
        {
            "title": "Pilotaggio della Realtà",
            "description": "Tecniche avanzate per il controllo della realtà",
            "instructor": "Prof. Luigi Bianchi",
            "duration": "12 settimane",
            "price": 297.0,
            "category": "Avanzato",
            "is_active": True,
            "max_students": 15,
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        }
    ]
    
    for course in sample_courses:
        existing_course = db.courses.find_one({"title": course["title"]})
        if not existing_course:
            db.courses.insert_one(course)
            print(f"✅ Created course: {course['title']}")
    
    print("✅ Database initialization completed!")
    print("\n🔑 Login credentials:")
    print("Email: admin@grabovoi.com")
    print("Password: admin123")

if __name__ == "__main__":
    init_database()