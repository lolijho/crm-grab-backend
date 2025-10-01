from fastapi import FastAPI, HTTPException, Depends, status, BackgroundTasks
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pymongo import MongoClient
from bson import ObjectId
from datetime import datetime, timedelta
import jwt
import bcrypt
import os
from typing import Optional, List, Dict, Any
import uuid
from pydantic import BaseModel, Field, EmailStr
import secrets
import logging
import pandas as pd
import io
from fastapi import UploadFile, File, Request
from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
import json
import aiosmtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from woocommerce import API as WooCommerceAPI
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
import asyncio
from dateutil import parser as date_parser

from translations import get_translation, get_entity_message, get_error_message
from fastapi import Request

# Load environment variables
from dotenv import load_dotenv
import os
load_dotenv(os.path.join(os.path.dirname(__file__), '.env'))

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Grabovoi CRM API", version="1.0.0")

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# MongoDB connection
MONGO_URL = os.getenv("MONGO_URL", "mongodb://localhost:27017/")
DB_NAME = os.getenv("DB_NAME", "grabovoi_crm")
client = MongoClient(MONGO_URL)
db = client[DB_NAME]

# JWT settings
JWT_SECRET = os.getenv("JWT_SECRET", "your-super-secret-jwt-key-here")
JWT_ALGORITHM = "HS256"
JWT_EXPIRATION_HOURS = 24

# Security
security = HTTPBearer()

# Database collections
users_collection = db.users
contacts_collection = db.contacts
orders_collection = db.orders
order_items_collection = db.order_items
products_collection = db.products
crm_products_collection = db.crm_products  # New CRM custom products
courses_collection = db.courses
tags_collection = db.tags
contact_tags_collection = db.contact_tags
rules_collection = db.rules
integrations_collection = db.integrations
messages_collection = db.messages
email_settings_collection = db.email_settings
course_enrollments_collection = db.course_enrollments
course_tags_collection = db.course_tags
users_collection = db.users
verification_tokens_collection = db.verification_tokens
inbound_emails_collection = db.inbound_emails
email_attachments_collection = db.email_attachments

# WooCommerce collections
wc_customers_collection = db.wc_customers
wc_products_collection = db.wc_products  
wc_orders_collection = db.wc_orders
wc_sync_logs_collection = db.wc_sync_logs
wc_sync_settings_collection = db.wc_sync_settings
deleted_courses_collection = db.deleted_courses  # Track manually deleted courses

# ===== HELPER FUNCTIONS =====

def detect_language_from_request(request: Request = None) -> str:
    """Detect language from request headers or return default"""
    if request:
        # Check Accept-Language header
        accept_language = request.headers.get('Accept-Language', '')
        if 'it' in accept_language.lower():
            return 'it'
        elif 'en' in accept_language.lower():
            return 'en'
    
    # Default to Italian
    return 'it'

# Initialize WooCommerce API client
woocommerce_client = None
try:
    woocommerce_client = WooCommerceAPI(
        url=os.getenv("WOOCOMMERCE_URL"),
        consumer_key=os.getenv("WOOCOMMERCE_CONSUMER_KEY"),
        consumer_secret=os.getenv("WOOCOMMERCE_CONSUMER_SECRET"),
        version="wc/v3",
        timeout=50,
        verify_ssl=True
    )
    logger.info("WooCommerce API client initialized successfully")
except Exception as e:
    logger.error(f"Failed to initialize WooCommerce client: {e}")
    woocommerce_client = None

# ===== PYDANTIC MODELS =====

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class UserCreate(BaseModel):
    username: str
    email: str
    password: str
    name: Optional[str] = None
    role: str = "user"  # user, admin, manager

class UserRegister(BaseModel):
    username: str
    email: str
    password: str
    name: Optional[str] = None

class UserResponse(BaseModel):
    id: str
    username: str
    email: str
    name: Optional[str] = None
    role: str
    is_verified: bool
    created_at: datetime
    last_login: Optional[datetime] = None

class EmailVerification(BaseModel):
    token: str

class UserUpdate(BaseModel):
    username: Optional[str] = None
    email: Optional[str] = None
    name: Optional[str] = None
    role: Optional[str] = None
    is_verified: Optional[bool] = None

class PasswordReset(BaseModel):
    email: str

class PasswordResetConfirm(BaseModel):
    token: str
    new_password: str

class ContactBase(BaseModel):
    first_name: str
    last_name: str
    email: Optional[str] = None
    phone: Optional[str] = None
    address: Optional[str] = None
    city: Optional[str] = None
    postal_code: Optional[str] = None
    country: Optional[str] = None
    notes: Optional[str] = None
    source: Optional[str] = None
    status: str = "lead"

class ContactCreate(ContactBase):
    tag_ids: Optional[List[str]] = []

class ContactUpdate(BaseModel):
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    address: Optional[str] = None
    city: Optional[str] = None
    postal_code: Optional[str] = None
    country: Optional[str] = None
    notes: Optional[str] = None
    source: Optional[str] = None
    status: Optional[str] = None
    tag_ids: Optional[List[str]] = []

class ContactResponse(ContactBase):
    id: str
    created_at: datetime
    updated_at: datetime
    tags: Optional[List[Dict]] = []

class ProductBase(BaseModel):
    name: str
    description: Optional[str] = None
    price: float = 0.0
    category: Optional[str] = None
    sku: Optional[str] = None
    is_active: bool = True
    course_id: Optional[str] = None
    crm_product_id: Optional[str] = None  # Association with CRM product
    source: Optional[str] = "manual"  # "woocommerce" or "manual"

class ProductCreate(ProductBase):
    pass

class ProductUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    price: Optional[float] = None
    category: Optional[str] = None
    sku: Optional[str] = None
    is_active: Optional[bool] = None
    course_id: Optional[str] = None
    crm_product_id: Optional[str] = None

class ProductResponse(ProductBase):
    id: str
    created_at: datetime
    updated_at: datetime

# CRM Products Models (Custom CRM products separate from WooCommerce)
class CrmProductBase(BaseModel):
    name: str
    description: Optional[str] = None
    base_price: float = 0.0
    category: Optional[str] = None
    is_active: bool = True

class CrmProductCreate(CrmProductBase):
    pass

class CrmProductUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    base_price: Optional[float] = None
    category: Optional[str] = None
    is_active: Optional[bool] = None

class CrmProductResponse(CrmProductBase):
    id: str
    payment_links_count: int = 0
    created_at: datetime
    updated_at: datetime

class OrderItemBase(BaseModel):
    product_id: Optional[str] = None
    product_name: str
    quantity: int = 1
    unit_price: float
    total_price: float

class OrderItemCreate(OrderItemBase):
    pass

class OrderItemResponse(OrderItemBase):
    id: str
    order_id: str
    created_at: datetime

class OrderBase(BaseModel):
    contact_id: Optional[str] = None
    status: str = "pending"
    payment_method: Optional[str] = None
    payment_status: str = "pending"
    notes: Optional[str] = None

class OrderCreate(OrderBase):
    items: List[OrderItemCreate]

class OrderUpdate(OrderBase):
    pass

class OrderResponse(OrderBase):
    id: str
    order_number: str
    total_amount: float
    created_at: datetime
    updated_at: datetime
    contact: Optional[Dict] = None
    items: Optional[List[OrderItemResponse]] = []

class TagBase(BaseModel):
    name: str
    category: str = "general"
    color: str = "#3B82F6"

class TagCreate(TagBase):
    pass

class TagResponse(TagBase):
    id: str
    created_at: datetime

class CourseBase(BaseModel):
    title: str
    description: Optional[str] = None
    instructor: Optional[str] = None
    duration: Optional[str] = None
    price: float = 0.0
    category: Optional[str] = None
    language: Optional[str] = None
    is_active: bool = True
    max_students: Optional[int] = None
    source: Optional[str] = None

class CourseCreate(CourseBase):
    pass

class CourseUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    instructor: Optional[str] = None
    duration: Optional[str] = None
    price: Optional[float] = None
    category: Optional[str] = None
    language: Optional[str] = None
    is_active: Optional[bool] = None
    max_students: Optional[int] = None
    source: Optional[str] = None

class CourseResponse(CourseBase):
    id: str
    created_at: datetime
    updated_at: datetime

class CourseEnrollment(BaseModel):
    contact_id: str
    course_id: str
    enrolled_at: datetime
    status: str = "active"  # active, completed, cancelled
    source: str = "manual"  # manual, order, tag

class CourseEnrollmentResponse(BaseModel):
    id: str
    contact_id: str
    course_id: str
    enrolled_at: datetime
    status: str
    source: str
    course: Optional[Dict] = None  # Course details

class RuleBase(BaseModel):
    name: str
    description: Optional[str] = None
    trigger_event: str  # 'create', 'update', 'email'
    conditions: Dict[str, Any]  # JSON conditions
    actions: Dict[str, Any]  # JSON actions (e.g., add tags)
    is_active: bool = True

class RuleCreate(RuleBase):
    pass

class RuleResponse(RuleBase):
    id: str
    created_at: datetime
    updated_at: datetime

# ===== IMPORT MODELS =====

class ImportMappingField(BaseModel):
    csv_column: str
    crm_field: str
    transform_rule: Optional[str] = None  # For data transformation rules

class ContactImportMapping(BaseModel):
    mappings: List[ImportMappingField]
    tag_ids: Optional[List[str]] = []
    skip_duplicates: bool = True
    update_duplicates: bool = False

class OrderImportMapping(BaseModel):
    mappings: List[ImportMappingField]
    default_status: str = "pending"
    default_payment_status: str = "pending"
    associate_with_contacts: bool = True  # Associate orders with contacts via email
    create_missing_contacts: bool = True

class GoogleSheetConfig(BaseModel):
    spreadsheet_id: str
    sheet_name: Optional[str] = None
    range_name: Optional[str] = "A:Z"  # Default range

class ImportResult(BaseModel):
    total_rows: int
    successful_imports: int
    failed_imports: int
    duplicates_skipped: int
    errors: List[str]
    created_items: List[str]  # IDs of created items

# ===== WOOCOMMERCE MODELS =====

class WooCommerceSyncLog(BaseModel):
    entity_type: str  # customers, products, orders
    sync_type: str    # full, incremental
    status: str       # started, completed, failed
    records_processed: int = 0
    error_message: Optional[str] = None
    started_at: datetime
    completed_at: Optional[datetime] = None

class WooCommerceSyncStatus(BaseModel):
    last_customer_sync: Optional[datetime] = None
    last_product_sync: Optional[datetime] = None
    last_order_sync: Optional[datetime] = None
    customer_count: int = 0
    product_count: int = 0
    order_count: int = 0
    last_full_sync: Optional[datetime] = None

class WooCommerceCustomer(BaseModel):
    woocommerce_id: int
    email: str
    first_name: str
    last_name: str
    username: Optional[str] = None
    billing_address: Optional[Dict] = None
    shipping_address: Optional[Dict] = None
    phone: Optional[str] = None
    total_spent: float = 0.0
    orders_count: int = 0
    date_created_wc: datetime
    date_modified_wc: datetime
    last_sync: datetime

class WooCommerceProduct(BaseModel):
    woocommerce_id: int
    name: str
    slug: str
    sku: Optional[str] = None
    price: float = 0.0
    regular_price: float = 0.0
    sale_price: float = 0.0
    description: Optional[str] = None
    short_description: Optional[str] = None
    categories: List[Dict] = []
    tags: List[Dict] = []
    stock_quantity: Optional[int] = None
    stock_status: str = "instock"
    date_created_wc: datetime
    date_modified_wc: datetime
    last_sync: datetime

class WooCommerceOrder(BaseModel):
    woocommerce_id: int
    order_number: str
    woocommerce_customer_id: Optional[int] = None
    crm_contact_id: Optional[str] = None  # Associated contact in CRM
    status: str
    currency: str = "EUR"
    total: float = 0.0
    total_tax: float = 0.0
    shipping_total: float = 0.0
    payment_method: Optional[str] = None
    payment_method_title: Optional[str] = None
    billing_address: Optional[Dict] = None
    shipping_address: Optional[Dict] = None
    line_items: List[Dict] = []
    date_created_wc: datetime
    date_modified_wc: datetime
    date_completed_wc: Optional[datetime] = None
    last_sync: datetime

class WooCommerceSyncSettings(BaseModel):
    auto_sync_enabled: bool = True
    sync_customers_enabled: bool = True
    sync_products_enabled: bool = True
    sync_orders_enabled: bool = True
    sync_interval_orders: int = 15  # minutes
    sync_interval_customers: int = 30  # minutes
    sync_interval_products: int = 60  # minutes
    full_sync_hour: int = 2  # 2 AM daily
    last_updated: datetime = Field(default_factory=datetime.utcnow)
    updated_by: Optional[str] = None

class WooCommerceSyncSettingsUpdate(BaseModel):
    auto_sync_enabled: Optional[bool] = None
    sync_customers_enabled: Optional[bool] = None
    sync_products_enabled: Optional[bool] = None
    sync_orders_enabled: Optional[bool] = None
    sync_interval_orders: Optional[int] = None
    sync_interval_customers: Optional[int] = None
    sync_interval_products: Optional[int] = None
    full_sync_hour: Optional[int] = None

# ===== EMAIL MODELS =====

class EmailSettings(BaseModel):
    smtp_server: Optional[str] = None
    smtp_port: Optional[int] = None
    username: Optional[str] = None
    password: Optional[str] = None
    from_email: Optional[str] = None
    from_name: Optional[str] = None
    use_tls: Optional[bool] = None

class EmailSettingsUpdate(BaseModel):
    smtp_server: Optional[str] = None
    smtp_port: Optional[int] = None
    username: Optional[str] = None
    password: Optional[str] = None
    from_email: Optional[str] = None
    from_name: Optional[str] = None
    use_tls: Optional[bool] = None

class MessageCreate(BaseModel):
    recipient_id: str  # Contact/Client ID
    recipient_email: str
    subject: str
    content: str
    message_type: str = "email"

class MessageResponse(BaseModel):
    id: str
    recipient_id: str
    recipient_email: str
    recipient_name: Optional[str] = None
    subject: str
    content: str
    message_type: str
    status: str  # sent, failed, pending
    sent_at: Optional[datetime] = None
    error_message: Optional[str] = None
    created_by: str
    created_at: datetime

# ===== INBOUND EMAIL MODELS =====

class InboundEmail(BaseModel):
    message_id: str
    from_email: str
    from_name: Optional[str] = None
    to_email: str
    subject: str
    text_body: Optional[str] = None
    html_body: Optional[str] = None
    received_date: datetime
    processed: bool = False
    client_id: Optional[str] = None
    postmark_id: Optional[str] = None

class InboundEmailResponse(BaseModel):
    id: str
    message_id: str
    from_email: str
    from_name: Optional[str] = None
    to_email: str
    subject: str
    text_body: Optional[str] = None
    html_body: Optional[str] = None
    received_date: datetime
    processed: bool
    client_id: Optional[str] = None
    client_name: Optional[str] = None
    attachments: Optional[List[Dict]] = []

class EmailAttachment(BaseModel):
    email_id: str
    filename: str
    content_type: str
    content_length: int
    content_data: str  # Base64 encoded content

class PostmarkWebhookPayload(BaseModel):
    MessageID: str
    From: str
    FromName: Optional[str] = None
    To: str
    Subject: str
    TextBody: Optional[str] = None
    HtmlBody: Optional[str] = None
    Date: str
    Attachments: Optional[List[Dict]] = []

# ===== UTILITY FUNCTIONS =====

def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

def verify_password(password: str, hashed: str) -> bool:
    return bcrypt.checkpw(password.encode('utf-8'), hashed.encode('utf-8'))

def create_jwt_token(user_id: str, email: str, role: str) -> str:
    payload = {
        "user_id": user_id,
        "email": email,
        "role": role,
        "exp": datetime.utcnow() + timedelta(hours=JWT_EXPIRATION_HOURS),
        "iat": datetime.utcnow()
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)

def decode_jwt_token(token: str) -> Dict:
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token has expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")

def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    token = credentials.credentials
    payload = decode_jwt_token(token)
    # Handle both 'sub' and 'user_id' for compatibility
    user_id = payload.get("sub") or payload.get("user_id")
    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid token: missing user ID")
    user = users_collection.find_one({"_id": ObjectId(user_id)})
    if not user:
        raise HTTPException(status_code=401, detail="User not found")
    return user

def generate_order_number() -> str:
    """Generate unique order number"""
    timestamp = datetime.now().strftime("%Y%m%d")
    random_suffix = secrets.token_hex(4).upper()
    return f"ORD-{timestamp}-{random_suffix}"

import math

def convert_objectid_to_str(obj):
    """Convert MongoDB ObjectId to string recursively, rename _id to id, and handle NaN values"""
    if isinstance(obj, ObjectId):
        return str(obj)
    elif isinstance(obj, dict):
        result = {}
        for key, value in obj.items():
            # Rename MongoDB _id field to id
            if key == "_id":
                result["id"] = convert_objectid_to_str(value)
            else:
                result[key] = convert_objectid_to_str(value)
        return result
    elif isinstance(obj, list):
        return [convert_objectid_to_str(item) for item in obj]
    elif isinstance(obj, float) and (math.isnan(obj) or math.isinf(obj)):
        return None
    return obj

# ===== IMPORT UTILITY FUNCTIONS =====

def parse_csv_file(file_content: bytes) -> pd.DataFrame:
    """Parse CSV file content and return DataFrame"""
    try:
        # Try different encodings
        for encoding in ['utf-8', 'latin-1', 'iso-8859-1', 'cp1252']:
            try:
                content = file_content.decode(encoding)
                df = pd.read_csv(io.StringIO(content))
                return df
            except UnicodeDecodeError:
                continue
        
        # If all encodings fail, use utf-8 with error handling
        content = file_content.decode('utf-8', errors='replace')
        df = pd.read_csv(io.StringIO(content))
        return df
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error parsing CSV file: {str(e)}")

def apply_field_mapping(row: dict, mappings: List[ImportMappingField]) -> dict:
    """Apply field mapping from CSV columns to CRM fields"""
    mapped_data = {}
    
    for mapping in mappings:
        csv_value = row.get(mapping.csv_column, "")
        
        # Apply transformation rules if specified
        if mapping.transform_rule:
            if mapping.transform_rule == "lowercase":
                csv_value = str(csv_value).lower() if csv_value else ""
            elif mapping.transform_rule == "uppercase":
                csv_value = str(csv_value).upper() if csv_value else ""
            elif mapping.transform_rule == "strip":
                csv_value = str(csv_value).strip() if csv_value else ""
        
        mapped_data[mapping.crm_field] = csv_value
    
    return mapped_data

def find_existing_contact_by_email(email: str) -> Optional[dict]:
    """Find existing contact by email address"""
    if not email:
        return None
    return contacts_collection.find_one({"email": email.lower()})

def create_contact_from_mapped_data(mapped_data: dict, tag_ids: List[str], user_id: str) -> str:
    """Create a new contact from mapped data and return contact ID"""
    contact_doc = {
        "first_name": mapped_data.get("first_name", ""),
        "last_name": mapped_data.get("last_name", ""),
        "email": mapped_data.get("email", "").lower() if mapped_data.get("email") else None,
        "phone": mapped_data.get("phone", ""),
        "address": mapped_data.get("address", ""),
        "city": mapped_data.get("city", ""),
        "postal_code": mapped_data.get("postal_code", ""),
        "country": mapped_data.get("country", ""),
        "notes": mapped_data.get("notes", ""),
        "source": mapped_data.get("source", "csv_import"),
        "status": mapped_data.get("status", "lead"),
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow(),
        "created_by": user_id
    }
    
    # Remove empty fields
    contact_doc = {k: v for k, v in contact_doc.items() if v}
    
    result = contacts_collection.insert_one(contact_doc)
    contact_id = str(result.inserted_id)
    
    # Associate tags if provided
    if tag_ids:
        tag_associations = [
            {"contact_id": contact_id, "tag_id": tag_id, "created_at": datetime.utcnow()}
            for tag_id in tag_ids
        ]
        contact_tags_collection.insert_many(tag_associations)
    
    return contact_id

def get_google_sheet_data(spreadsheet_id: str, range_name: str = "A:Z") -> pd.DataFrame:
    """Fetch data from Google Sheets and return as DataFrame"""
    try:
        # Load credentials
        credentials_path = os.getenv("GOOGLE_SERVICE_ACCOUNT_FILE", "/app/backend/google_credentials.json")
        
        # Set up the service
        scope = ['https://www.googleapis.com/auth/spreadsheets.readonly']
        from google.oauth2 import service_account
        from googleapiclient.discovery import build
        
        credentials = service_account.Credentials.from_service_account_file(
            credentials_path, scopes=scope)
        service = build('sheets', 'v4', credentials=credentials)
        
        # Call the Sheets API
        sheet = service.spreadsheets()
        result = sheet.values().get(spreadsheetId=spreadsheet_id,
                                    range=range_name).execute()
        values = result.get('values', [])
        
        if not values:
            return pd.DataFrame()
        
        # Convert to DataFrame
        df = pd.DataFrame(values[1:], columns=values[0]) if len(values) > 1 else pd.DataFrame()
        return df
        
    except Exception as e:
        logger.error(f"Error accessing Google Sheet: {str(e)}")
        raise HTTPException(status_code=400, detail=f"Error accessing Google Sheet: {str(e)}")

# ===== AUTHENTICATION ENDPOINTS =====

@app.post("/api/register")
async def register_user(user_data: UserRegister):
    """Register a new user and send verification email"""
    try:
        # Check if user already exists
        existing_user = users_collection.find_one({"email": user_data.email})
        if existing_user:
            raise HTTPException(status_code=400, detail="Email already registered")
        
        existing_username = users_collection.find_one({"username": user_data.username})
        if existing_username:
            raise HTTPException(status_code=400, detail="Username already taken")
        
        # Hash password
        hashed_password = hash_password(user_data.password)
        
        # Generate verification token
        verification_token = generate_verification_token()
        
        # Create user
        user_doc = {
            "username": user_data.username,
            "email": user_data.email,
            "password": hashed_password,
            "name": user_data.name,
            "role": "user",  # Default role for registration
            "is_verified": False,
            "created_at": datetime.utcnow(),
            "last_login": None
        }
        
        result = users_collection.insert_one(user_doc)
        user_id = str(result.inserted_id)
        
        # Store verification token
        token_doc = {
            "user_id": user_id,
            "token": verification_token,
            "type": "email_verification",
            "expires_at": datetime.utcnow() + timedelta(hours=24),
            "created_at": datetime.utcnow()
        }
        
        verification_tokens_collection.insert_one(token_doc)
        
        # Send verification email
        email_sent = await send_verification_email(
            user_data.email, 
            verification_token, 
            user_data.name or user_data.username
        )
        
        return {
            "message": "Registration successful. Please check your email to verify your account.",
            "user_id": user_id,
            "email_sent": email_sent
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Registration error: {str(e)}")
        raise HTTPException(status_code=500, detail="Registration failed")

@app.get("/api/debug/database-info")
async def debug_database_info():
    """Debug endpoint to check database configuration"""
    try:
        mongo_url = os.getenv("MONGO_URL", "not_found")
        
        # Test database connection and get info
        from pymongo import MongoClient
        client = MongoClient(mongo_url)
        
        # Get database name being used
        db_name = db.name
        
        # Count collections and documents
        collections = db.list_collection_names()
        
        collection_info = {}
        for collection_name in collections:
            try:
                count = db[collection_name].count_documents({})
                collection_info[collection_name] = count
            except:
                collection_info[collection_name] = "error"
        
        return {
            "mongo_url_prefix": mongo_url[:30] + "..." if len(mongo_url) > 30 else mongo_url,
            "database_name": db_name,
            "collections": collection_info,
            "users_collection_count": users_collection.count_documents({}),
            "server_time": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        return {
            "error": str(e),
            "mongo_url_available": bool(os.getenv("MONGO_URL")),
            "server_time": datetime.utcnow().isoformat()
        }

@app.post("/api/initialize-admin")
async def initialize_admin():
    """Initialize admin user if not exists - for production setup"""
    try:
        # Check if admin user already exists
        existing_admin = users_collection.find_one({
            "$or": [
                {"email": "admin@grabovoi.com"},
                {"is_admin": True}
            ]
        })
        
        if existing_admin:
            # Fix admin role if it's not set correctly
            if existing_admin.get("role") != "admin":
                users_collection.update_one(
                    {"_id": existing_admin["_id"]},
                    {"$set": {"role": "admin", "is_admin": True, "updated_at": datetime.utcnow()}}
                )
                return {
                    "message": "Admin user role updated to admin",
                    "email": existing_admin.get("email"),
                    "created": False,
                    "updated": True
                }
            
            return {
                "message": "Admin user already exists",
                "email": existing_admin.get("email"),
                "created": False
            }
        
        # Create admin user
        password_hash = hash_password("admin123")
        
        admin_user = {
            "username": "admin",
            "email": "admin@grabovoi.com",
            "password": password_hash,
            "name": "Amministratore",
            "role": "admin", 
            "is_admin": True,
            "is_verified": True,
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow(),
            "last_login": None
        }
        
        result = users_collection.insert_one(admin_user)
        
        return {
            "message": "Admin user created successfully",
            "email": "admin@grabovoi.com",
            "user_id": str(result.inserted_id),
            "created": True,
            "note": "Default password: admin123 - Please change it after first login"
        }
        
    except Exception as e:
        logger.error(f"Initialize admin error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to initialize admin: {str(e)}")

@app.post("/api/login")
async def login_user(credentials: UserLogin):
    """Login user with email verification check"""
    try:
        logger.info(f"Login attempt for: {credentials.email}")
        
        # Check environment variables
        mongo_url = os.getenv("MONGO_URL")
        jwt_secret = os.getenv("JWT_SECRET")
        logger.info(f"MONGO_URL loaded: {bool(mongo_url)}")
        logger.info(f"JWT_SECRET loaded: {bool(jwt_secret)}")
        
        # Find user by email
        user = users_collection.find_one({"email": credentials.email})
        logger.info(f"User found: {bool(user)}")
        
        if not user:
            raise HTTPException(status_code=401, detail="Invalid credentials")
        
        # Verify password
        password_valid = verify_password(credentials.password, user["password"])
        logger.info(f"Password valid: {password_valid}")
        
        if not password_valid:
            raise HTTPException(status_code=401, detail="Invalid credentials")
        
        # Check if email is verified
        is_verified = user.get("is_verified", False)
        logger.info(f"Email verified: {is_verified}")
        
        if not is_verified:
            raise HTTPException(status_code=401, detail="Please verify your email before logging in")
        
        # Update last login
        users_collection.update_one(
            {"_id": user["_id"]},
            {"$set": {"last_login": datetime.utcnow()}}
        )
        
        # Create JWT token
        token_data = {
            "sub": str(user["_id"]),
            "email": user["email"],
            "role": user.get("role", "user"),
            "exp": datetime.utcnow() + timedelta(days=7)
        }
        token = jwt.encode(token_data, jwt_secret, algorithm="HS256")
        logger.info("JWT token created successfully")
        
        # Return user data and token
        user_response = convert_objectid_to_str(user)
        user_response.pop("password", None)  # Remove password from response
        
        return {
            "access_token": token,
            "token_type": "bearer",
            "user": user_response
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Login error: {str(e)}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail="Login failed")

@app.post("/api/verify-email")
async def verify_email(verification: EmailVerification):
    """Verify user's email address"""
    try:
        # Find valid verification token
        token_doc = verification_tokens_collection.find_one({
            "token": verification.token,
            "type": "email_verification",
            "expires_at": {"$gt": datetime.utcnow()}
        })
        
        if not token_doc:
            raise HTTPException(status_code=400, detail="Invalid or expired verification token")
        
        # Update user as verified
        result = users_collection.update_one(
            {"_id": ObjectId(token_doc["user_id"])},
            {"$set": {"is_verified": True, "updated_at": datetime.utcnow()}}
        )
        
        if result.matched_count == 0:
            raise HTTPException(status_code=404, detail="User not found")
        
        # Delete used token
        verification_tokens_collection.delete_one({"_id": token_doc["_id"]})
        
        return {"message": "Email verified successfully. You can now log in."}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Email verification error: {str(e)}")
        raise HTTPException(status_code=500, detail="Email verification failed")

@app.post("/api/resend-verification")
async def resend_verification_email(email_data: dict):
    """Resend verification email"""
    try:
        email = email_data.get("email")
        if not email:
            raise HTTPException(status_code=400, detail="Email is required")
        
        # Find user
        user = users_collection.find_one({"email": email})
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        if user.get("is_verified", False):
            raise HTTPException(status_code=400, detail="Email already verified")
        
        # Delete existing verification tokens
        verification_tokens_collection.delete_many({
            "user_id": str(user["_id"]),
            "type": "email_verification"
        })
        
        # Generate new verification token
        verification_token = generate_verification_token()
        
        # Store new token
        token_doc = {
            "user_id": str(user["_id"]),
            "token": verification_token,
            "type": "email_verification",
            "expires_at": datetime.utcnow() + timedelta(hours=24),
            "created_at": datetime.utcnow()
        }
        
        verification_tokens_collection.insert_one(token_doc)
        
        # Send verification email
        email_sent = await send_verification_email(
            email,
            verification_token,
            user.get("name") or user.get("username")
        )
        
        return {
            "message": "Verification email sent successfully",
            "email_sent": email_sent
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Resend verification error: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to resend verification email")

@app.post("/api/forgot-password")
async def forgot_password(password_reset: PasswordReset):
    """Send password reset email"""
    try:
        # Find user
        user = users_collection.find_one({"email": password_reset.email})
        if not user:
            # Don't reveal if email exists or not
            return {"message": "If the email exists, a password reset link has been sent"}
        
        # Delete existing password reset tokens
        verification_tokens_collection.delete_many({
            "user_id": str(user["_id"]),
            "type": "password_reset"
        })
        
        # Generate password reset token
        reset_token = generate_verification_token()
        
        # Store reset token (expires in 1 hour)
        token_doc = {
            "user_id": str(user["_id"]),
            "token": reset_token,
            "type": "password_reset",
            "expires_at": datetime.utcnow() + timedelta(hours=1),
            "created_at": datetime.utcnow()
        }
        
        verification_tokens_collection.insert_one(token_doc)
        
        # Send reset email
        email_sent = await send_password_reset_email(
            password_reset.email,
            reset_token,
            user.get("name") or user.get("username")
        )
        
        return {"message": "If the email exists, a password reset link has been sent"}
        
    except Exception as e:
        logger.error(f"Forgot password error: {str(e)}")
        return {"message": "If the email exists, a password reset link has been sent"}

@app.post("/api/reset-password")
async def reset_password(reset_data: PasswordResetConfirm):
    """Reset user password with token"""
    try:
        # Find valid reset token
        token_doc = verification_tokens_collection.find_one({
            "token": reset_data.token,
            "type": "password_reset",
            "expires_at": {"$gt": datetime.utcnow()}
        })
        
        if not token_doc:
            raise HTTPException(status_code=400, detail="Invalid or expired reset token")
        
        # Hash new password
        hashed_password = hash_password(reset_data.new_password)
        
        # Update user password
        result = users_collection.update_one(
            {"_id": ObjectId(token_doc["user_id"])},
            {"$set": {"password": hashed_password, "updated_at": datetime.utcnow()}}
        )
        
        if result.matched_count == 0:
            raise HTTPException(status_code=404, detail="User not found")
        
        # Delete used token
        verification_tokens_collection.delete_one({"_id": token_doc["_id"]})
        
        return {"message": "Password reset successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Password reset error: {str(e)}")
        raise HTTPException(status_code=500, detail="Password reset failed")

@app.get("/api/auth/me")
async def get_current_user_info(current_user: dict = Depends(get_current_user)):
    """Get current user information"""
    # Remove sensitive information
    user_info = convert_objectid_to_str(current_user)
    user_info.pop("password", None)
    return user_info

# ===== CONTACTS ENDPOINTS =====

@app.get("/api/contacts")
async def get_contacts(
    current_user: dict = Depends(get_current_user),
    course_id: Optional[str] = None,
    tag_id: Optional[str] = None,
    has_orders: Optional[bool] = None,
    product_id: Optional[str] = None,
    status: Optional[str] = None,
    language: Optional[str] = None,
    page: int = 1,
    limit: int = 100,  # Changed default to 100 as requested
    search: Optional[str] = None
):
    """Get all contacts with optional filters and pagination - OPTIMIZED"""
    try:
        # Build optimized aggregation pipeline
        pipeline = []
        
        # Base match stage
        match_stage = {}
        
        # Apply direct filters
        if status:
            match_stage["status"] = status
        if language:
            match_stage["language"] = language
        
        # Apply search filter
        if search and search.strip():
            search_regex = {"$regex": search.strip(), "$options": "i"}
            match_stage["$or"] = [
                {"first_name": search_regex},
                {"last_name": search_regex},
                {"email": search_regex}
            ]
        
        if match_stage:
            pipeline.append({"$match": match_stage})
        
        # Add lookup stages for complex filters
        if course_id or tag_id or has_orders is not None or product_id:
            
            # Lookup tags if needed
            if tag_id:
                pipeline.extend([
                    {
                        "$lookup": {
                            "from": "contact_tags",
                            "localField": "_id",
                            "foreignField": "contact_id",
                            "as": "contact_tags"
                        }
                    },
                    {
                        "$match": {
                            "contact_tags.tag_id": tag_id
                        }
                    }
                ])
            
            # Lookup orders if needed
            if has_orders is not None or product_id:
                pipeline.append({
                    "$lookup": {
                        "from": "orders",
                        "let": {"contact_str_id": {"$toString": "$_id"}},
                        "pipeline": [
                            {"$match": {"$expr": {"$eq": ["$contact_id", "$$contact_str_id"]}}},
                            {
                                "$lookup": {
                                    "from": "order_items",
                                    "let": {"order_str_id": {"$toString": "$_id"}},
                                    "pipeline": [
                                        {"$match": {"$expr": {"$eq": ["$order_id", "$$order_str_id"]}}}
                                    ],
                                    "as": "items"
                                }
                            }
                        ],
                        "as": "orders"
                    }
                })
                
                # Filter by has_orders
                if has_orders is not None:
                    if has_orders:
                        pipeline.append({"$match": {"orders": {"$ne": []}}})
                    else:
                        pipeline.append({"$match": {"orders": []}})
                
                # Filter by product_id
                if product_id:
                    pipeline.append({
                        "$match": {
                            "orders.items.product_id": product_id
                        }
                    })
        
        # Add final tag lookup for display
        pipeline.extend([
            {
                "$lookup": {
                    "from": "contact_tags",
                    "let": {"contact_str_id": {"$toString": "$_id"}},
                    "pipeline": [
                        {"$match": {"$expr": {"$eq": ["$contact_id", "$$contact_str_id"]}}},
                        {
                            "$lookup": {
                                "from": "tags",
                                "localField": "tag_id",
                                "foreignField": "_id",
                                "as": "tag_info"
                            }
                        },
                        {"$unwind": "$tag_info"},
                        {"$replaceRoot": {"newRoot": "$tag_info"}}
                    ],
                    "as": "tags"
                }
            }
        ])
        
        # Execute optimized query (without expensive count)
        contacts = list(contacts_collection.aggregate(pipeline + [
            {"$skip": (page - 1) * limit},
            {"$limit": limit + 1}  # Get one extra to check if there are more
        ]))
        
        # Check if there are more results without expensive count
        has_more = len(contacts) > limit
        if has_more:
            contacts = contacts[:-1]  # Remove the extra item
            
        # Estimate total for pagination (much faster)
        estimated_total = ((page - 1) * limit) + len(contacts)
        if has_more:
            estimated_total += 1  # At least one more page
            
        return {
            "contacts": convert_objectid_to_str(contacts),
            "pagination": {
                "current_page": page,
                "per_page": limit,
                "total_count": estimated_total,
                "total_pages": page + (1 if has_more else 0),
                "has_more": has_more
            }
        }
        
    except Exception as e:
        logger.error(f"Error in optimized get_contacts: {e}")
        # Fallback to original logic if needed
        return {"contacts": [], "pagination": {"current_page": 1, "per_page": limit, "total_count": 0, "total_pages": 0}}

@app.get("/api/contacts/original")
async def get_contacts_original(
    current_user: dict = Depends(get_current_user),
    course_id: Optional[str] = None,
    tag_id: Optional[str] = None,
    has_orders: Optional[bool] = None,
    product_id: Optional[str] = None,
    status: Optional[str] = None,
    language: Optional[str] = None
):
    """Get all contacts with optional filters - ORIGINAL VERSION"""
    # Start with base query
    query = {}
    
    # Apply status filter if provided
    if status:
        query["status"] = status
    
    # Apply language filter if provided
    if language:
        query["language"] = language
    
    # Get initial contacts
    contacts = list(contacts_collection.find(query))
    
    # Apply additional filters
    filtered_contacts = []
    
    for contact in contacts:
        contact_id = str(contact["_id"])
        include_contact = True
        
        # Filter by course enrollment
        if course_id and include_contact:
            enrollment_exists = course_enrollments_collection.find_one({
                "contact_id": contact_id,
                "course_id": course_id,
                "status": "active"
            })
            if not enrollment_exists:
                include_contact = False
        
        # Filter by tag
        if tag_id and include_contact:
            tag_association = contact_tags_collection.find_one({
                "contact_id": contact_id,
                "tag_id": tag_id
            })
            if not tag_association:
                include_contact = False
        
        # Filter by orders
        if has_orders is not None and include_contact:
            order_count = orders_collection.count_documents({"contact_id": contact_id})
            if has_orders and order_count == 0:
                include_contact = False
            elif not has_orders and order_count > 0:
                include_contact = False
        
        # Filter by product purchased
        if product_id and include_contact:
            # Find orders with this product
            orders_with_product = list(orders_collection.find({"contact_id": contact_id}))
            has_product = False
            
            for order in orders_with_product:
                order_items = list(order_items_collection.find({
                    "order_id": str(order["_id"]),
                    "product_id": product_id
                }))
                if order_items:
                    has_product = True
                    break
            
            if not has_product:
                include_contact = False
        
        if include_contact:
            filtered_contacts.append(contact)
    
    # Get tags for each filtered contact
    for contact in filtered_contacts:
        contact_id = str(contact["_id"])
        contact_tag_docs = list(contact_tags_collection.find({"contact_id": contact_id}))
        tag_ids = [doc["tag_id"] for doc in contact_tag_docs]
        
        tags = []
        if tag_ids:
            tag_docs = list(tags_collection.find({"_id": {"$in": [ObjectId(tag_id) for tag_id in tag_ids]}}))
            tags = convert_objectid_to_str(tag_docs)
        
        contact["tags"] = tags
    
    return convert_objectid_to_str(filtered_contacts)

# ===== CONTACT ASSOCIATIONS ENDPOINTS =====

@app.post("/api/contacts/{contact_id}/associate-product")
async def associate_product_with_contact(
    contact_id: str,
    product_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Associate a product with a contact by creating an order"""
    # Verify contact exists
    contact = contacts_collection.find_one({"_id": ObjectId(contact_id)})
    if not contact:
        raise HTTPException(status_code=404, detail="Contact not found")
    
    # Verify product exists
    product = products_collection.find_one({"_id": ObjectId(product_id)})
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    
    # Create an order for this association
    order_doc = {
        "contact_id": contact_id,
        "order_number": f"ASSOC-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}",
        "total_amount": product.get("price", 0),
        "status": "completed",
        "payment_status": "paid",
        "payment_method": "association",
        "notes": f"Prodotto associato manualmente: {product.get('name', 'N/A')}",
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow()
    }
    
    order_result = orders_collection.insert_one(order_doc)
    order_id = str(order_result.inserted_id)
    
    # Create order item
    item_doc = {
        "order_id": order_id,
        "product_id": product_id,
        "product_name": product.get("name", "N/A"),
        "quantity": 1,
        "unit_price": product.get("price", 0),
        "total_price": product.get("price", 0)
    }
    
    order_items_collection.insert_one(item_doc)
    
    # Process course associations if this product is course-related
    process_order_course_associations(order_id, contact_id)
    
    return {
        "message": "Product associated successfully",
        "order_id": order_id,
        "product_name": product.get("name", "N/A")
    }

@app.post("/api/contacts/{contact_id}/associate-course")
async def associate_course_with_contact(
    contact_id: str,
    course_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Associate a course with a contact and transform to student"""
    # Verify contact exists
    contact = contacts_collection.find_one({"_id": ObjectId(contact_id)})
    if not contact:
        raise HTTPException(status_code=404, detail="Contact not found")
    
    # Verify course exists
    course = courses_collection.find_one({"_id": ObjectId(course_id)})
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")
    
    # Enroll contact in course (this will also transform to student)
    enrollment_id = enroll_contact_in_course(contact_id, course_id, "manual")
    
    # Get updated contact
    updated_contact = contacts_collection.find_one({"_id": ObjectId(contact_id)})
    
    return {
        "message": "Course associated successfully",
        "enrollment_id": enrollment_id,
        "course_title": course.get("title", "N/A"),
        "new_status": updated_contact.get("status"),
        "transformed_to_student": updated_contact.get("status") == "student"
    }

@app.get("/api/contacts/filter-options")
async def get_contact_filter_options(current_user: dict = Depends(get_current_user)):
    """Get available filter options for contacts page"""
    # Get all courses
    courses = list(courses_collection.find({}))
    
    # Get all tags  
    tags = list(tags_collection.find({}))
    
    # Get all products
    products = list(products_collection.find({}))
    
    # Get contact statuses
    statuses = list(contacts_collection.distinct("status"))
    
    return {
        "courses": convert_objectid_to_str(courses),
        "tags": convert_objectid_to_str(tags), 
        "products": convert_objectid_to_str(products),
        "statuses": statuses,
        "languages": list(contacts_collection.distinct("language"))
    }

@app.post("/api/contacts/{contact_id}/tags")
async def add_tag_to_contact(
    contact_id: str, 
    tag_data: dict,
    current_user: dict = Depends(get_current_user)
):
    """Add tag to contact"""
    try:
        tag_id = tag_data.get("tag_id")
        if not tag_id:
            raise HTTPException(status_code=400, detail="tag_id is required")
        
        # Verify contact exists
        contact = contacts_collection.find_one({"_id": ObjectId(contact_id)})
        if not contact:
            raise HTTPException(status_code=404, detail="Contact not found")
        
        # Verify tag exists
        tag = tags_collection.find_one({"_id": ObjectId(tag_id)})
        if not tag:
            raise HTTPException(status_code=404, detail="Tag not found")
        
        # Check if tag association already exists
        existing_association = contact_tags_collection.find_one({
            "contact_id": contact_id,
            "tag_id": tag_id
        })
        
        if not existing_association:
            # Create new tag association
            contact_tags_collection.insert_one({
                "contact_id": contact_id,
                "tag_id": tag_id,
                "created_at": datetime.utcnow()
            })
        
        return {"success": True, "message": "Tag added to contact"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error adding tag to contact: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")

@app.post("/api/contacts")
async def create_contact(contact_data: ContactCreate, current_user: dict = Depends(get_current_user)):
    contact_doc = contact_data.dict(exclude={"tag_ids"})
    contact_doc.update({
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow(),
        "created_by": str(current_user["_id"])
    })
    
    result = contacts_collection.insert_one(contact_doc)
    contact_id = str(result.inserted_id)
    
    # Associate tags
    if contact_data.tag_ids:
        tag_associations = [
            {"contact_id": contact_id, "tag_id": tag_id, "created_at": datetime.utcnow()}
            for tag_id in contact_data.tag_ids
        ]
        contact_tags_collection.insert_many(tag_associations)
    
    # Check for course associations based on tags
    check_tag_course_associations(contact_id)
    
    # Get created contact with tags
    created_contact = contacts_collection.find_one({"_id": result.inserted_id})
    contact_tag_docs = list(contact_tags_collection.find({"contact_id": contact_id}))
    tag_ids = [doc["tag_id"] for doc in contact_tag_docs]
    
    tags = []
    if tag_ids:
        tag_docs = list(tags_collection.find({"_id": {"$in": [ObjectId(tag_id) for tag_id in tag_ids]}}))
        tags = convert_objectid_to_str(tag_docs)
    
    created_contact["tags"] = tags
    
    return convert_objectid_to_str(created_contact)

@app.get("/api/contacts/{contact_id}")
async def get_contact(contact_id: str, current_user: dict = Depends(get_current_user)):
    contact = contacts_collection.find_one({"_id": ObjectId(contact_id)})
    if not contact:
        raise HTTPException(status_code=404, detail="Contact not found")
    
    # Get tags
    contact_tag_docs = list(contact_tags_collection.find({"contact_id": contact_id}))
    tag_ids = [doc["tag_id"] for doc in contact_tag_docs]
    
    tags = []
    if tag_ids:
        tag_docs = list(tags_collection.find({"_id": {"$in": [ObjectId(tag_id) for tag_id in tag_ids]}}))
        tags = convert_objectid_to_str(tag_docs)
    
    contact["tags"] = tags
    return convert_objectid_to_str(contact)

@app.put("/api/contacts/{contact_id}")
async def update_contact(contact_id: str, contact_data: ContactUpdate, current_user: dict = Depends(get_current_user)):
    # Only include fields that are not None (partial update support)
    update_doc = {k: v for k, v in contact_data.dict(exclude={"tag_ids"}).items() if v is not None}
    update_doc["updated_at"] = datetime.utcnow()
    
    result = contacts_collection.update_one(
        {"_id": ObjectId(contact_id)},
        {"$set": update_doc}
    )
    
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Contact not found")
    
    # Update tags
    if contact_data.tag_ids is not None:
        # Remove existing tags
        contact_tags_collection.delete_many({"contact_id": contact_id})
        
        # Add new tags
        if contact_data.tag_ids:
            tag_associations = [
                {"contact_id": contact_id, "tag_id": tag_id, "created_at": datetime.utcnow()}
                for tag_id in contact_data.tag_ids
            ]
            contact_tags_collection.insert_many(tag_associations)
        
        # Check for course associations based on new tags
        check_tag_course_associations(contact_id)
    
    return await get_contact(contact_id, current_user)

@app.delete("/api/contacts/{contact_id}")
async def delete_contact(contact_id: str, current_user: dict = Depends(get_current_user)):
    # Delete contact tags first
    contact_tags_collection.delete_many({"contact_id": contact_id})
    
    # Delete contact
    result = contacts_collection.delete_one({"_id": ObjectId(contact_id)})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Contact not found")
    
    return {"message": "Contact deleted successfully"}

# ===== DASHBOARD ENDPOINTS =====

@app.get("/api/dashboard/stats")
async def get_dashboard_stats(current_user: dict = Depends(get_current_user)):
    # Get counts
    total_contacts = contacts_collection.count_documents({})
    active_students = contacts_collection.count_documents({"status": "student"})
    total_orders = orders_collection.count_documents({})
    leads = contacts_collection.count_documents({"status": "lead"})
    
    return {
        "total_contacts": total_contacts,
        "active_students": active_students,
        "total_orders": total_orders,
        "leads": leads
    }

@app.get("/api/dashboard/initial-data")
async def get_initial_dashboard_data(current_user: dict = Depends(get_current_user)):
    """
    Get OPTIMIZED initial data for faster loading - only first page of contacts but ALL small datasets
    This provides instant loading with good UX while keeping manageable data sizes
    """
    try:
        # Get dashboard stats (ALWAYS TOTAL COUNTS for correct statistics)
        total_contacts = contacts_collection.count_documents({})
        active_students = contacts_collection.count_documents({"status": "student"})
        total_orders = orders_collection.count_documents({})
        total_products = products_collection.count_documents({})
        total_courses = courses_collection.count_documents({})
        leads = contacts_collection.count_documents({"status": "lead"})
        
        stats = {
            "total_contacts": total_contacts,
            "active_students": active_students,
            "total_orders": total_orders,
            "total_products": total_products,
            "total_courses": total_courses,
            "leads": leads
        }
        
        # Get FIRST PAGE of contacts only (100 items) for fast loading
        per_page = 100
        contacts_cursor = contacts_collection.find().sort("created_at", -1).limit(per_page)
        contacts_page = list(contacts_cursor)
        
        # Calculate pagination for contacts
        total_pages_contacts = math.ceil(total_contacts / per_page) if total_contacts > 0 else 1
        
        contacts_data = {
            "contacts": convert_objectid_to_str(contacts_page),
            "pagination": {
                "page": 1,
                "limit": per_page,
                "total": total_contacts,
                "pages": total_pages_contacts,
                "has_next": total_pages_contacts > 1,
                "has_prev": False
            }
        }
        
        # Get ALL products (usually small dataset) with course info
        products_pipeline = [
            {
                "$lookup": {
                    "from": "courses",
                    "let": {"course_id_str": "$course_id"},
                    "pipeline": [
                        {
                            "$match": {
                                "$expr": {
                                    "$and": [
                                        {"$ne": ["$$course_id_str", None]},
                                        {"$ne": ["$$course_id_str", ""]},
                                        {"$eq": ["$_id", {"$toObjectId": "$$course_id_str"}]}
                                    ]
                                }
                            }
                        }
                    ],
                    "as": "course_info"
                }
            },
            {
                "$addFields": {
                    "course": {
                        "$cond": {
                            "if": {"$gt": [{"$size": "$course_info"}, 0]},
                            "then": {"$arrayElemAt": ["$course_info", 0]},
                            "else": None
                        }
                    }
                }
            },
            {
                "$project": {
                    "course_info": 0
                }
            },
            {"$sort": {"created_at": -1}}
        ]
        
        all_products = list(products_collection.aggregate(products_pipeline))
        
        products_data = {
            "products": convert_objectid_to_str(all_products),
            "total": total_products
        }
        
        # Get ALL courses (usually small dataset)
        courses_cursor = courses_collection.find().sort("created_at", -1)
        all_courses = list(courses_cursor)
        
        courses_data = {
            "courses": convert_objectid_to_str(all_courses),
            "total": total_courses
        }
        
        return {
            "success": True,
            "dashboard_stats": stats,
            "contacts_data": contacts_data,
            "products_data": products_data,
            "courses_data": courses_data,
            "load_time": datetime.utcnow().isoformat(),
            "data_loaded": {
                "contacts": len(contacts_page),  # Only first page
                "products": len(all_products), 
                "courses": len(all_courses)
            },
            "optimization": "first_page_contacts_only"
        }
        
    except Exception as e:
        logger.error(f"Error in get_initial_dashboard_data: {str(e)}")
        raise HTTPException(status_code=500, detail="Error loading initial data")

# ===== PRODUCTS ENDPOINTS =====

@app.get("/api/products")
async def get_products(
    current_user: dict = Depends(get_current_user),
    page: int = 1,
    limit: int = 100,
    search: Optional[str] = None,
    category: Optional[str] = None,
    is_active: Optional[bool] = None
):
    # Build match stage for filters
    match_stage = {}
    
    if search and search.strip():
        search_regex = {"$regex": search.strip(), "$options": "i"}
        match_stage["$or"] = [
            {"name": search_regex},
            {"description": search_regex},
            {"sku": search_regex}
        ]
    
    if category:
        match_stage["category"] = category
        
    if is_active is not None:
        match_stage["is_active"] = is_active
    
    # Build aggregation pipeline
    pipeline = []
    
    # Add match stage if filters exist
    if match_stage:
        pipeline.append({"$match": match_stage})
    
    # Count total documents
    count_pipeline = pipeline.copy()
    count_pipeline.append({"$count": "total"})
    count_result = list(products_collection.aggregate(count_pipeline))
    total = count_result[0]["total"] if count_result else 0
    
    # Add course lookup
    pipeline.extend([
        {
            "$lookup": {
                "from": "courses",
                "let": {"course_id_str": "$course_id"},
                "pipeline": [
                    {
                        "$match": {
                            "$expr": {
                                "$and": [
                                    {"$ne": ["$$course_id_str", None]},
                                    {"$ne": ["$$course_id_str", ""]},
                                    {"$eq": ["$_id", {"$toObjectId": "$$course_id_str"}]}
                                ]
                            }
                        }
                    }
                ],
                "as": "course_info"
            }
        },
        {
            "$addFields": {
                "course": {
                    "$cond": {
                        "if": {"$gt": [{"$size": "$course_info"}, 0]},
                        "then": {"$arrayElemAt": ["$course_info", 0]},
                        "else": None
                    }
                }
            }
        },
        {
            "$project": {
                "course_info": 0  # Remove the temporary course_info array
            }
        },
        {"$skip": (page - 1) * limit},  # Pagination
        {"$limit": limit}
    ])
    
    products = list(products_collection.aggregate(pipeline))
    
    # Calculate pagination info
    total_pages = math.ceil(total / limit) if total > 0 else 1
    has_next = page < total_pages
    has_prev = page > 1
    
    return {
        "data": convert_objectid_to_str(products),
        "pagination": {
            "page": page,
            "limit": limit,
            "total": total,
            "pages": total_pages,
            "has_next": has_next,
            "has_prev": has_prev
        }
    }

@app.post("/api/products")
async def create_product(product_data: ProductCreate, current_user: dict = Depends(get_current_user)):
    # Validation
    if not product_data.name.strip():
        raise HTTPException(status_code=400, detail="Product name cannot be empty")
    
    if product_data.price < 0:
        raise HTTPException(status_code=400, detail="Product price cannot be negative")
    
    # Validate course_id exists if provided
    if product_data.course_id and product_data.course_id.strip():
        try:
            # Validate ObjectId format
            course_object_id = ObjectId(product_data.course_id)
            course = courses_collection.find_one({"_id": course_object_id})
            if not course:
                raise HTTPException(status_code=400, detail="Associated course not found")
        except Exception as e:
            if "invalid ObjectId" in str(e).lower() or "invalid" in str(e).lower():
                raise HTTPException(status_code=400, detail="Invalid course ID format")
            raise HTTPException(status_code=400, detail="Associated course not found")
    
    product_doc = product_data.dict()
    product_doc.update({
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow(),
        "created_by": str(current_user["_id"])
    })
    
    result = products_collection.insert_one(product_doc)
    created_product = products_collection.find_one({"_id": result.inserted_id})
    return convert_objectid_to_str(created_product)

@app.get("/api/products/{product_id}")
async def get_product(product_id: str, current_user: dict = Depends(get_current_user)):
    # Aggregate to include course information
    pipeline = [
        {"$match": {"_id": ObjectId(product_id)}},
        {
            "$lookup": {
                "from": "courses",
                "let": {"course_id_str": "$course_id"},
                "pipeline": [
                    {
                        "$match": {
                            "$expr": {
                                "$and": [
                                    {"$ne": ["$$course_id_str", None]},
                                    {"$ne": ["$$course_id_str", ""]},
                                    {"$eq": ["$_id", {"$toObjectId": "$$course_id_str"}]}
                                ]
                            }
                        }
                    }
                ],
                "as": "course_info"
            }
        },
        {
            "$addFields": {
                "course": {
                    "$cond": {
                        "if": {"$gt": [{"$size": "$course_info"}, 0]},
                        "then": {"$arrayElemAt": ["$course_info", 0]},
                        "else": None
                    }
                }
            }
        },
        {
            "$project": {
                "course_info": 0  # Remove the temporary course_info array
            }
        }
    ]
    
    products = list(products_collection.aggregate(pipeline))
    if not products:
        raise HTTPException(status_code=404, detail="Product not found")
    
    return convert_objectid_to_str(products[0])

@app.put("/api/products/{product_id}")
async def update_product(product_id: str, product_data: ProductUpdate, current_user: dict = Depends(get_current_user)):
    # Validation
    if product_data.name is not None and not product_data.name.strip():
        raise HTTPException(status_code=400, detail="Product name cannot be empty")
    
    if product_data.price is not None and product_data.price < 0:
        raise HTTPException(status_code=400, detail="Product price cannot be negative")
    
    # Validate course_id exists if provided and not empty/null
    if product_data.course_id is not None and product_data.course_id.strip():
        try:
            # Validate ObjectId format
            course_object_id = ObjectId(product_data.course_id)
            course = courses_collection.find_one({"_id": course_object_id})
            if not course:
                raise HTTPException(status_code=400, detail="Associated course not found")
        except Exception as e:
            if "invalid ObjectId" in str(e).lower() or "invalid" in str(e).lower():
                raise HTTPException(status_code=400, detail="Invalid course ID format")
            raise HTTPException(status_code=400, detail="Associated course not found")
    
    # Build update document - handle None values explicitly for course_id
    update_doc = {}
    for k, v in product_data.dict().items():
        if k == "course_id":
            # Handle course_id specially to allow None/empty values
            if v is None or v == "":
                update_doc[k] = None
            else:
                update_doc[k] = v
        elif v is not None:
            update_doc[k] = v
    
    update_doc["updated_at"] = datetime.utcnow()
    
    result = products_collection.update_one(
        {"_id": ObjectId(product_id)},
        {"$set": update_doc}
    )
    
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Product not found")
    
    updated_product = products_collection.find_one({"_id": ObjectId(product_id)})
    return convert_objectid_to_str(updated_product)

@app.delete("/api/products/{product_id}")
async def delete_product(product_id: str, current_user: dict = Depends(get_current_user)):
    result = products_collection.delete_one({"_id": ObjectId(product_id)})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Product not found")
    return {"message": "Product deleted successfully"}

# ===== CRM PRODUCTS ENDPOINTS =====

@app.get("/api/crm-products")
async def get_crm_products(
    current_user: dict = Depends(get_current_user),
    page: int = 1,
    limit: int = 100,
    search: Optional[str] = None
):
    """Get CRM products with pagination"""
    try:
        # Build match query
        match_query = {}
        
        # Apply search filter
        if search and search.strip():
            search_regex = {"$regex": search.strip(), "$options": "i"}
            match_query["$or"] = [
                {"name": search_regex},
                {"description": search_regex},
                {"category": search_regex}
            ]
        
        # FAST VERSION: Simple query without expensive operations
        crm_products = list(crm_products_collection.find(match_query)
                           .sort("created_at", -1)
                           .skip((page - 1) * limit)
                           .limit(limit))
        
        # Add payment links count with simple query (optional, only if needed)
        for product in crm_products:
            product["payment_links_count"] = 0  # Default to 0 for speed
        
        return {
            "data": convert_objectid_to_str(crm_products),
            "pagination": {
                "current_page": page,
                "per_page": limit,
                "total_count": len(crm_products),  # Approximate count
                "total_pages": 1,
                "has_more": len(crm_products) == limit
            }
        }
        
    except Exception as e:
        logger.error(f"Error getting CRM products: {e}")
        return {
            "data": [],
            "pagination": {"current_page": 1, "per_page": limit, "total_count": 0, "total_pages": 0}
        }

@app.get("/api/crm-products/{product_id}")
async def get_crm_product(product_id: str, current_user: dict = Depends(get_current_user)):
    """Get single CRM product by ID"""
    try:
        crm_product = crm_products_collection.find_one({"_id": ObjectId(product_id)})
        if not crm_product:
            raise HTTPException(status_code=404, detail="CRM Product not found")
        return convert_objectid_to_str(crm_product)
    except Exception as e:
        logger.error(f"Error getting CRM product: {e}")
        raise HTTPException(status_code=404, detail="CRM Product not found")

@app.post("/api/crm-products")
async def create_crm_product(product: CrmProductCreate, current_user: dict = Depends(get_current_user)):
    """Create new CRM product"""
    try:
        crm_product_dict = product.dict()
        product_id = ObjectId()
        
        # Use _id from current_user since it's the raw MongoDB document
        user_id = str(current_user["_id"])
        
        crm_product_dict.update({
            "_id": product_id,
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow(),
            "created_by": user_id,
            "payment_links_count": 0
        })
        
        crm_products_collection.insert_one(crm_product_dict)
        
        # Return the created product
        created_product = crm_products_collection.find_one({"_id": product_id})
        return convert_objectid_to_str(created_product)
        
    except Exception as e:
        logger.error(f"Error creating CRM product: {e}")
        raise HTTPException(status_code=400, detail="Error creating CRM product")

@app.put("/api/crm-products/{product_id}")
async def update_crm_product(
    product_id: str, 
    product: CrmProductUpdate, 
    current_user: dict = Depends(get_current_user)
):
    """Update CRM product"""
    try:
        update_data = {k: v for k, v in product.dict().items() if v is not None}
        update_data["updated_at"] = datetime.utcnow()
        
        result = crm_products_collection.update_one(
            {"_id": ObjectId(product_id)},
            {"$set": update_data}
        )
        
        if result.matched_count == 0:
            raise HTTPException(status_code=404, detail="CRM Product not found")
            
        # Return updated product
        updated_product = crm_products_collection.find_one({"_id": ObjectId(product_id)})
        return convert_objectid_to_str(updated_product)
        
    except Exception as e:
        logger.error(f"Error updating CRM product: {e}")
        raise HTTPException(status_code=400, detail="Error updating CRM product")

@app.delete("/api/crm-products/{product_id}")
async def delete_crm_product(product_id: str, current_user: dict = Depends(get_current_user)):
    """Delete CRM product"""
    try:
        # Check if there are associated payment links
        associated_links = products_collection.count_documents({"crm_product_id": product_id})
        if associated_links > 0:
            # Optionally, you can remove the associations or prevent deletion
            # For now, we'll just remove the associations
            products_collection.update_many(
                {"crm_product_id": product_id},
                {"$unset": {"crm_product_id": ""}}
            )
        
        result = crm_products_collection.delete_one({"_id": ObjectId(product_id)})
        if result.deleted_count == 0:
            raise HTTPException(status_code=404, detail="CRM Product not found")
            
        return {"message": "CRM Product deleted successfully"}
        
    except Exception as e:
        logger.error(f"Error deleting CRM product: {e}")
        raise HTTPException(status_code=400, detail="Error deleting CRM product")

@app.get("/api/crm-products/{product_id}/payment-links")
async def get_payment_links_by_crm_product(
    product_id: str, 
    current_user: dict = Depends(get_current_user)
):
    """Get payment links associated with a CRM product"""
    try:
        # Verify CRM product exists
        crm_product = crm_products_collection.find_one({"_id": ObjectId(product_id)})
        if not crm_product:
            raise HTTPException(status_code=404, detail="CRM Product not found")
        
        # Get associated payment links
        payment_links = list(products_collection.find({"crm_product_id": product_id}))
        
        return {
            "data": convert_objectid_to_str(payment_links),
            "pagination": {
                "current_page": 1,
                "per_page": len(payment_links),
                "total_count": len(payment_links),
                "total_pages": 1
            }
        }
        
    except Exception as e:
        logger.error(f"Error getting payment links for CRM product: {e}")
        raise HTTPException(status_code=400, detail="Error getting payment links")

# ===== ORDERS ENDPOINTS =====

@app.get("/api/orders")
async def get_orders(
    current_user: dict = Depends(get_current_user),
    language: Optional[str] = None,
    page: int = 1,
    limit: int = 100,  # Changed default to 100
    search: Optional[str] = None
):
    """Get orders with pagination and filters - OPTIMIZED"""
    try:
        # Build aggregation pipeline
        pipeline = []
        
        # Base match stage
        match_stage = {}
        if language:
            match_stage["language"] = language
        
        # Apply search filter
        if search and search.strip():
            search_regex = {"$regex": search.strip(), "$options": "i"}
            match_stage["$or"] = [
                {"order_number": search_regex},
                {"notes": search_regex}
            ]
        
        if match_stage:
            pipeline.append({"$match": match_stage})
        
        # Lookup contact and items
        pipeline.extend([
            {
                "$lookup": {
                    "from": "contacts",
                    "let": {"contact_id_str": "$contact_id"},
                    "pipeline": [
                        {"$match": {"$expr": {"$eq": [{"$toString": "$_id"}, "$$contact_id_str"]}}}
                    ],
                    "as": "contact"
                }
            },
            {
                "$lookup": {
                    "from": "order_items",
                    "let": {"order_id_str": {"$toString": "$_id"}},
                    "pipeline": [
                        {"$match": {"$expr": {"$eq": ["$order_id", "$$order_id_str"]}}}
                    ],
                    "as": "items"
                }
            },
            {
                "$addFields": {
                    "contact": {"$arrayElemAt": ["$contact", 0]}
                }
            }
        ])
        
        # Get total count for pagination
        count_pipeline = pipeline + [{"$count": "total"}]
        count_result = list(orders_collection.aggregate(count_pipeline))
        total_count = count_result[0]["total"] if count_result else 0
        
        # Add sorting and pagination
        pipeline.extend([
            {"$sort": {"created_at": -1}},
            {"$skip": (page - 1) * limit},
            {"$limit": limit}
        ])
        
        # Execute query
        orders = list(orders_collection.aggregate(pipeline))
        
        return {
            "orders": convert_objectid_to_str(orders),
            "pagination": {
                "current_page": page,
                "per_page": limit,
                "total_count": total_count,
                "total_pages": (total_count + limit - 1) // limit
            }
        }
        
    except Exception as e:
        logger.error(f"Error in optimized get_orders: {e}")
        return {"orders": [], "pagination": {"current_page": 1, "per_page": limit, "total_count": 0, "total_pages": 0}}

@app.get("/api/orders/original")  
async def get_orders_original(
    current_user: dict = Depends(get_current_user),
    language: Optional[str] = None
):
    """Get orders - ORIGINAL VERSION"""
    # Build query with optional language filter
    query = {}
    if language:
        query["language"] = language
        
    orders = list(orders_collection.find(query))
    
    # Get contact and items for each order
    for order in orders:
        order_id = str(order["_id"])
        
        # Get contact info
        if order.get("contact_id"):
            contact = contacts_collection.find_one({"_id": ObjectId(order["contact_id"])})
            order["contact"] = convert_objectid_to_str(contact) if contact else None
        
        # Get order items
        items = list(order_items_collection.find({"order_id": order_id}))
        order["items"] = convert_objectid_to_str(items)
    
    return convert_objectid_to_str(orders)
    
    # Get contact and items for each order
    for order in orders:
        order_id = str(order["_id"])
        
        # Get contact info
        if order.get("contact_id"):
            contact = contacts_collection.find_one({"_id": ObjectId(order["contact_id"])})
            order["contact"] = convert_objectid_to_str(contact) if contact else None
        
        # Get order items
        items = list(order_items_collection.find({"order_id": order_id}))
        order["items"] = convert_objectid_to_str(items)
    
    return convert_objectid_to_str(orders)

@app.post("/api/orders")
async def create_order(order_data: OrderCreate, current_user: dict = Depends(get_current_user)):
    # Create order
    order_doc = order_data.dict(exclude={"items"})
    order_doc.update({
        "order_number": generate_order_number(),
        "total_amount": sum(item.total_price for item in order_data.items),
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow(),
        "created_by": str(current_user["_id"])
    })
    
    result = orders_collection.insert_one(order_doc)
    order_id = str(result.inserted_id)
    
    # Create order items
    if order_data.items:
        items_docs = []
        for item in order_data.items:
            item_doc = item.dict()
            item_doc.update({
                "order_id": order_id,
                "created_at": datetime.utcnow()
            })
            items_docs.append(item_doc)
        
        order_items_collection.insert_many(items_docs)
    
    # Process course associations for this order
    if order_data.contact_id:
        process_order_course_associations(order_id, order_data.contact_id)
    
    return await get_order(order_id, current_user)

@app.get("/api/orders/{order_id}")
async def get_order(order_id: str, current_user: dict = Depends(get_current_user)):
    order = orders_collection.find_one({"_id": ObjectId(order_id)})
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    
    # Get contact info
    if order.get("contact_id"):
        contact = contacts_collection.find_one({"_id": ObjectId(order["contact_id"])})
        order["contact"] = convert_objectid_to_str(contact) if contact else None
    
    # Get order items
    items = list(order_items_collection.find({"order_id": order_id}))
    order["items"] = convert_objectid_to_str(items)
    
    return convert_objectid_to_str(order)

@app.put("/api/orders/{order_id}")
async def update_order(order_id: str, order_data: OrderUpdate, current_user: dict = Depends(get_current_user)):
    update_doc = order_data.dict()
    update_doc["updated_at"] = datetime.utcnow()
    
    result = orders_collection.update_one(
        {"_id": ObjectId(order_id)},
        {"$set": update_doc}
    )
    
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Order not found")
    
    return await get_order(order_id, current_user)

@app.delete("/api/orders/{order_id}")
async def delete_order(order_id: str, current_user: dict = Depends(get_current_user)):
    # Delete order items first
    order_items_collection.delete_many({"order_id": order_id})
    
    # Delete order
    result = orders_collection.delete_one({"_id": ObjectId(order_id)})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Order not found")
    
    return {"message": "Order deleted successfully"}

# ===== TAGS ENDPOINTS =====

@app.get("/api/tags")
async def get_tags(current_user: dict = Depends(get_current_user)):
    tags = list(tags_collection.find())
    return convert_objectid_to_str(tags)

@app.post("/api/tags")
async def create_tag(tag_data: TagCreate, current_user: dict = Depends(get_current_user)):
    tag_doc = tag_data.dict()
    tag_doc.update({
        "created_at": datetime.utcnow(),
        "created_by": str(current_user["_id"])
    })
    
    result = tags_collection.insert_one(tag_doc)
    created_tag = tags_collection.find_one({"_id": result.inserted_id})
    return convert_objectid_to_str(created_tag)

@app.delete("/api/tags/{tag_id}")
async def delete_tag(tag_id: str, current_user: dict = Depends(get_current_user)):
    # Delete tag associations first
    contact_tags_collection.delete_many({"tag_id": tag_id})
    
    # Delete tag
    result = tags_collection.delete_one({"_id": ObjectId(tag_id)})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Tag not found")
    
    return {"message": "Tag deleted successfully"}

# ===== COURSES ENDPOINTS =====

@app.get("/api/courses")
async def get_courses(
    language: Optional[str] = None,
    category: Optional[str] = None,
    is_active: Optional[bool] = None,
    instructor: Optional[str] = None,
    min_price: Optional[float] = None,
    max_price: Optional[float] = None,
    page: int = 1,
    limit: int = 100,
    search: Optional[str] = None,
    current_user: dict = Depends(get_current_user)
):
    # Build query with optional filters
    query = {}
    
    if language:
        query["language"] = language
    
    if category:
        query["category"] = category
    
    if is_active is not None:
        query["is_active"] = is_active
    
    if instructor:
        # Case-insensitive partial match for instructor
        query["instructor"] = {"$regex": instructor, "$options": "i"}
    
    # Search filter
    if search and search.strip():
        search_regex = {"$regex": search.strip(), "$options": "i"}
        query["$or"] = [
            {"title": search_regex},
            {"description": search_regex},
            {"instructor": search_regex}
        ]
    
    # Price range filter
    if min_price is not None or max_price is not None:
        price_query = {}
        if min_price is not None:
            price_query["$gte"] = min_price
        if max_price is not None:
            price_query["$lte"] = max_price
        query["price"] = price_query
    
    # FAST VERSION: Get courses without expensive count
    courses = list(courses_collection.find(query)
                  .sort("created_at", -1)
                  .skip((page - 1) * limit)
                  .limit(limit + 1))  # Get one extra to check if there are more
    
    # Check if there are more results
    has_more = len(courses) > limit
    if has_more:
        courses = courses[:-1]  # Remove extra item
    
    return {
        "data": convert_objectid_to_str(courses),
        "pagination": {
            "page": page,
            "limit": limit,
            "total": len(courses),  # Approximate count
            "pages": page + (1 if has_more else 0),
            "has_next": has_more,
            "has_prev": page > 1
        }
    }

@app.get("/api/courses/languages")
async def get_course_languages(current_user: dict = Depends(get_current_user)):
    """Get all available course languages"""
    languages = courses_collection.distinct("language")
    # Filter out None/null values and empty strings
    languages = [lang for lang in languages if lang and lang.strip()]
    return sorted(languages)

@app.get("/api/courses/categories")
async def get_course_categories(current_user: dict = Depends(get_current_user)):
    """Get all available course categories"""
    categories = courses_collection.distinct("category")
    # Filter out None/null values and empty strings
    categories = [cat for cat in categories if cat and cat.strip()]
    return sorted(categories)

@app.get("/api/courses/instructors")
async def get_course_instructors(current_user: dict = Depends(get_current_user)):
    """Get all available course instructors"""
    instructors = courses_collection.distinct("instructor")
    # Filter out None/null values and empty strings
    instructors = [inst for inst in instructors if inst and inst.strip()]
    return sorted(instructors)

@app.post("/api/courses")
async def create_course(course: CourseCreate, current_user: dict = Depends(get_current_user), request: Request = None):
    language = detect_language_from_request(request)
    
    # Validation
    if not course.title or course.title.strip() == "":
        raise HTTPException(
            status_code=400, 
            detail=get_translation('name_empty', language)
        )
    
    if course.price is not None and course.price < 0:
        raise HTTPException(
            status_code=400, 
            detail=get_translation('price_negative', language)
        )
    
    if course.max_students is not None and course.max_students < 0:
        raise HTTPException(
            status_code=400, 
            detail="Il numero massimo di studenti non può essere negativo"
        )
    
    course_doc = {
        "title": course.title,
        "description": course.description or "",
        "instructor": course.instructor or "Grigori Grabovoi",
        "duration": course.duration or "",
        "price": course.price or 0,
        "category": course.category or "",
        "language": course.language or "it",
        "max_students": course.max_students or 0,
        "is_active": course.is_active if course.is_active is not None else True,
        "source": course.source or "manual",
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow(),
        "created_by": str(current_user["_id"])
    }
    
    result = courses_collection.insert_one(course_doc)
    course_doc["_id"] = result.inserted_id
    
    # Convert ObjectId to string and add message
    response_data = convert_objectid_to_str(course_doc)
    response_data["message"] = get_entity_message('course', 'created_successfully', language)
    
    return response_data

@app.get("/api/courses/{course_id}")
async def get_course(course_id: str, current_user: dict = Depends(get_current_user)):
    course = courses_collection.find_one({"_id": ObjectId(course_id)})
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")
    return convert_objectid_to_str(course)

@app.put("/api/courses/{course_id}")
async def update_course(course_id: str, course_data: CourseUpdate, current_user: dict = Depends(get_current_user), request: Request = None):
    language = detect_language_from_request(request)
    
    # Check if course exists
    course = courses_collection.find_one({"_id": ObjectId(course_id)})
    if not course:
        raise HTTPException(
            status_code=404, 
            detail=get_error_message('not_found', language, 'course')
        )
    
    # Validation for updates
    update_data = {}
    for field, value in course_data.dict(exclude_unset=True).items():
        if field == 'title' and (not value or value.strip() == ""):
            raise HTTPException(
                status_code=400, 
                detail=get_translation('name_empty', language)
            )
        elif field == 'price' and value is not None and value < 0:
            raise HTTPException(
                status_code=400, 
                detail=get_translation('price_negative', language)
            )
        update_data[field] = value
    
    if update_data:
        update_data["updated_at"] = datetime.utcnow()
        update_data["updated_by"] = str(current_user["_id"])
        
        result = courses_collection.update_one(
            {"_id": ObjectId(course_id)}, 
            {"$set": update_data}
        )
        
        if result.matched_count == 0:
            raise HTTPException(
                status_code=404, 
                detail=get_error_message('not_found', language, 'course')
            )
    
    # Get updated course
    updated_course = courses_collection.find_one({"_id": ObjectId(course_id)})
    return {
        **convert_objectid_to_str(updated_course),
        "message": get_entity_message('course', 'updated_successfully', language)
    }

@app.delete("/api/courses/{course_id}")
async def delete_course(course_id: str, current_user: dict = Depends(get_current_user), request: Request = None):
    language = detect_language_from_request(request)
    
    # First get the course to track it as manually deleted
    course = courses_collection.find_one({"_id": ObjectId(course_id)})
    if not course:
        raise HTTPException(
            status_code=404, 
            detail=get_error_message('not_found', language, 'course')
        )
    
    # Track this course as manually deleted to prevent auto-recreation
    deleted_course_doc = {
        "course_id": course_id,
        "course_title": course.get("title", ""),
        "associated_product_id": course.get("associated_product_id"),
        "deleted_at": datetime.utcnow(),
        "deleted_by": str(current_user["_id"])
    }
    deleted_courses_collection.insert_one(deleted_course_doc)
    
    # Delete the course
    result = courses_collection.delete_one({"_id": ObjectId(course_id)})
    if result.deleted_count == 0:
        raise HTTPException(
            status_code=404, 
            detail=get_error_message('not_found', language, 'course')
        )
    
    return {"message": get_entity_message('course', 'deleted_successfully', language)}

@app.post("/api/courses/{course_id}/restore-auto-creation")
async def restore_auto_creation(course_id: str, current_user: dict = Depends(get_current_user), request: Request = None):
    """Remove a course from the manually deleted list to allow auto-recreation"""
    language = detect_language_from_request(request)
    
    result = deleted_courses_collection.delete_one({"course_id": course_id})
    if result.deleted_count == 0:
        raise HTTPException(
            status_code=404, 
            detail=get_error_message('not_found', language, 'course')
        )
    
    return {"message": get_translation('course_auto_creation_restored', language)}

# ===== COURSE ENROLLMENTS ENDPOINTS =====

@app.post("/api/courses/{course_id}/enroll/{contact_id}")
async def enroll_contact_in_course_endpoint(
    course_id: str, 
    contact_id: str, 
    current_user: dict = Depends(get_current_user)
):
    """Manually enroll a contact in a course"""
    # Verify course exists
    course = courses_collection.find_one({"_id": ObjectId(course_id)})
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")
    
    # Verify contact exists
    contact = contacts_collection.find_one({"_id": ObjectId(contact_id)})
    if not contact:
        raise HTTPException(status_code=404, detail="Contact not found")
    
    # Enroll contact
    enrollment_id = enroll_contact_in_course(contact_id, course_id, "manual")
    
    # Get enrollment details
    enrollment = course_enrollments_collection.find_one({"_id": ObjectId(enrollment_id)})
    enrollment_dict = convert_objectid_to_str(enrollment)
    enrollment_dict["course"] = convert_objectid_to_str(course)
    
    return enrollment_dict

@app.get("/api/contacts/{contact_id}/courses")
async def get_contact_courses(contact_id: str, current_user: dict = Depends(get_current_user)):
    """Get all courses for a contact"""
    enrollments = list(course_enrollments_collection.find({"contact_id": contact_id}))
    
    courses_with_enrollment = []
    for enrollment in enrollments:
        course = courses_collection.find_one({"_id": ObjectId(enrollment["course_id"])})
        if course:
            course_dict = convert_objectid_to_str(course)
            course_dict["enrollment"] = convert_objectid_to_str(enrollment)
            courses_with_enrollment.append(course_dict)
    
    return courses_with_enrollment

@app.delete("/api/enrollments/{enrollment_id}")
async def cancel_course_enrollment(enrollment_id: str, current_user: dict = Depends(get_current_user)):
    """Cancel a course enrollment"""
    result = course_enrollments_collection.update_one(
        {"_id": ObjectId(enrollment_id)},
        {"$set": {"status": "cancelled", "cancelled_at": datetime.utcnow()}}
    )
    
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Enrollment not found")
    
    return {"message": "Enrollment cancelled successfully"}

@app.get("/api/courses/{course_id}/students")
async def get_course_students(course_id: str, current_user: dict = Depends(get_current_user)):
    """Get all students/contacts enrolled in a course"""
    # Verify course exists
    course = courses_collection.find_one({"_id": ObjectId(course_id)})
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")
    
    # Get all enrollments for this course
    enrollments = list(course_enrollments_collection.find({"course_id": course_id}))
    
    students_with_enrollment = []
    for enrollment in enrollments:
        contact = contacts_collection.find_one({"_id": ObjectId(enrollment["contact_id"])})
        if contact:
            contact_dict = convert_objectid_to_str(contact)
            contact_dict["enrollment"] = convert_objectid_to_str(enrollment)
            students_with_enrollment.append(contact_dict)
    
    return {
        "course": convert_objectid_to_str(course),
        "students": students_with_enrollment,
        "total_enrolled": len(students_with_enrollment)
    }

@app.get("/api/enrollments")
async def get_all_enrollments(
    current_user: dict = Depends(get_current_user),
    course_id: Optional[str] = None,
    contact_id: Optional[str] = None,
    status: Optional[str] = None
):
    """Get all enrollments with optional filters"""
    # Build filter query
    filter_query = {}
    if course_id:
        filter_query["course_id"] = course_id
    if contact_id:
        filter_query["contact_id"] = contact_id
    if status:
        filter_query["status"] = status
    
    # Get enrollments with course and contact details
    pipeline = [
        {"$match": filter_query},
        {
            "$lookup": {
                "from": "courses",
                "localField": "course_id",
                "foreignField": "_id",
                "as": "course",
                "pipeline": [{"$project": {"title": 1, "price": 1, "instructor": 1}}]
            }
        },
        {
            "$lookup": {
                "from": "contacts", 
                "localField": "contact_id",
                "foreignField": "_id",
                "as": "contact",
                "pipeline": [{"$project": {"name": 1, "email": 1, "phone": 1}}]
            }
        },
        {
            "$addFields": {
                "course": {"$arrayElemAt": ["$course", 0]},
                "contact": {"$arrayElemAt": ["$contact", 0]}
            }
        },
        {"$sort": {"enrolled_at": -1}}
    ]
    
    enrollments = list(course_enrollments_collection.aggregate(pipeline))
    
    return {
        "enrollments": convert_objectid_to_str(enrollments),
        "total": len(enrollments)
    }

# ===== STUDENTS ENDPOINTS =====

@app.get("/api/students")
async def get_students(current_user: dict = Depends(get_current_user)):
    """Get all contacts with status 'student'"""
    students = list(contacts_collection.find({"status": "student"}))
    
    # Get tags and course info for each student
    for student in students:
        student_id = str(student["_id"])
        
        # Get tags
        contact_tag_docs = list(contact_tags_collection.find({"contact_id": student_id}))
        tag_ids = [doc["tag_id"] for doc in contact_tag_docs]
        
        tags = []
        if tag_ids:
            tag_docs = list(tags_collection.find({"_id": {"$in": [ObjectId(tag_id) for tag_id in tag_ids]}}))
            tags = convert_objectid_to_str(tag_docs)
        
        student["tags"] = tags
        
        # Get active course enrollments count
        active_courses = course_enrollments_collection.count_documents({
            "contact_id": student_id,
            "status": "active"
        })
        student["active_courses_count"] = active_courses
    
    return convert_objectid_to_str(students)

@app.get("/api/students/stats")
async def get_student_stats(current_user: dict = Depends(get_current_user)):
    total_students = contacts_collection.count_documents({"status": "student"})
    
    # Active students (with active course enrollments)
    active_students_pipeline = [
        {"$match": {"status": "active"}},
        {"$group": {"_id": "$contact_id"}},
        {"$count": "count"}
    ]
    active_result = list(course_enrollments_collection.aggregate(active_students_pipeline))
    active_students = active_result[0]["count"] if active_result else 0
    
    # New students this month
    start_of_month = datetime.utcnow().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    new_students_this_month = contacts_collection.count_documents({
        "status": "student",
        "created_at": {"$gte": start_of_month}
    })
    
    return {
        "total_students": total_students,
        "active_students": active_students,
        "new_students_this_month": new_students_this_month
    }

@app.get("/api/students/{student_id}")
async def get_student_detail(student_id: str, current_user: dict = Depends(get_current_user)):
    """Get detailed student information including courses, orders, and progress"""
    # Get student (contact with status 'student')
    student = contacts_collection.find_one({"_id": ObjectId(student_id)})
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")
    
    # Check if it's actually a student
    if student.get("status") != "student":
        raise HTTPException(status_code=400, detail="Contact is not a student")
    
    # Get tags
    contact_tag_docs = list(contact_tags_collection.find({"contact_id": student_id}))
    tag_ids = [doc["tag_id"] for doc in contact_tag_docs]
    
    tags = []
    if tag_ids:
        tag_docs = list(tags_collection.find({"_id": {"$in": [ObjectId(tag_id) for tag_id in tag_ids]}}))
        tags = convert_objectid_to_str(tag_docs)
    
    student["tags"] = tags
    
    # Get course enrollments with course details
    enrollments = list(course_enrollments_collection.find({"contact_id": student_id}).sort("enrolled_at", -1))
    
    courses_list = []
    for enrollment in enrollments:
        course = courses_collection.find_one({"_id": ObjectId(enrollment["course_id"])})
        if course:
            course_dict = convert_objectid_to_str(course)
            course_dict["enrolled_at"] = enrollment["enrolled_at"]
            course_dict["enrollment_status"] = enrollment["status"]
            course_dict["enrollment_source"] = enrollment["source"]
            course_dict["enrollment_id"] = str(enrollment["_id"])
            courses_list.append(course_dict)
    
    # Get student's orders
    orders = list(orders_collection.find({"contact_id": student_id}).sort("created_at", -1))
    
    # Get order items and products for each order
    all_products = []
    for order in orders:
        order_id = str(order["_id"])
        items = list(order_items_collection.find({"order_id": order_id}))
        order["items"] = convert_objectid_to_str(items)
        
        # Collect products
        for item in items:
            if item.get("product_id"):
                product = products_collection.find_one({"_id": ObjectId(item["product_id"])})
                if product:
                    product_dict = convert_objectid_to_str(product)
                    product_dict["purchased_at"] = order["created_at"]
                    product_dict["order_id"] = order_id
                    product_dict["quantity"] = item["quantity"]
                    product_dict["paid_price"] = item["unit_price"]
                    all_products.append(product_dict)
    
    # Remove duplicate products
    unique_products = {}
    for product in all_products:
        product_id = product["id"]
        if product_id not in unique_products or product["purchased_at"] > unique_products[product_id]["purchased_at"]:
            unique_products[product_id] = product
    
    products_list = list(unique_products.values())
    
    # Get recent messages
    messages = list(
        messages_collection
        .find({"recipient_id": student_id})
        .sort("created_at", -1)
        .limit(10)
    )
    
    return {
        "student": convert_objectid_to_str(student),
        "courses": courses_list,
        "orders": convert_objectid_to_str(orders),
        "products": products_list,
        "messages": convert_objectid_to_str(messages),
        "stats": {
            "total_courses": len(courses_list),
            "active_courses": len([c for c in courses_list if c["enrollment_status"] == "active"]),
            "completed_courses": len([c for c in courses_list if c["enrollment_status"] == "completed"]),
            "total_orders": len(orders),
            "total_spent": sum(order.get("total_amount", 0) for order in orders),
            "total_products": len(products_list)
        }
    }

# ===== CLIENTS ENDPOINTS =====

@app.get("/api/clients")
async def get_clients(current_user: dict = Depends(get_current_user)):
    """Get all contacts with status 'client'"""
    clients = list(contacts_collection.find({"status": "client"}))
    
    # Get tags for each client
    for client in clients:
        client_id = str(client["_id"])
        contact_tag_docs = list(contact_tags_collection.find({"contact_id": client_id}))
        tag_ids = [doc["tag_id"] for doc in contact_tag_docs]
        
        tags = []
        if tag_ids:
            tag_docs = list(tags_collection.find({"_id": {"$in": [ObjectId(tag_id) for tag_id in tag_ids]}}))
            tags = convert_objectid_to_str(tag_docs)
        
        client["tags"] = tags
    
    return convert_objectid_to_str(clients)

@app.get("/api/clients/stats")
async def get_client_stats(current_user: dict = Depends(get_current_user)):
    total_clients = contacts_collection.count_documents({"status": "client"})
    active_clients = contacts_collection.count_documents({"status": "client", "is_active": True})
    
    # New clients this month
    start_of_month = datetime.utcnow().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    new_clients_this_month = contacts_collection.count_documents({
        "status": "client",
        "created_at": {"$gte": start_of_month}
    })
    
    return {
        "total_clients": total_clients,
        "active_clients": active_clients,
        "new_clients_this_month": new_clients_this_month
    }

# ===== RULES ENDPOINTS =====

@app.get("/api/rules")
async def get_rules(current_user: dict = Depends(get_current_user)):
    rules = list(rules_collection.find())
    return convert_objectid_to_str(rules)

@app.post("/api/rules")
async def create_rule(rule_data: RuleCreate, current_user: dict = Depends(get_current_user)):
    rule_doc = rule_data.dict()
    rule_doc.update({
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow(),
        "created_by": str(current_user["_id"])
    })
    
    result = rules_collection.insert_one(rule_doc)
    created_rule = rules_collection.find_one({"_id": result.inserted_id})
    return convert_objectid_to_str(created_rule)

@app.delete("/api/rules/{rule_id}")
async def delete_rule(rule_id: str, current_user: dict = Depends(get_current_user)):
    result = rules_collection.delete_one({"_id": ObjectId(rule_id)})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Rule not found")
    return {"message": "Rule deleted successfully"}

# ===== CSV IMPORT ENDPOINTS =====

@app.post("/api/import/csv/preview")
async def preview_csv_import(file: UploadFile = File(...), current_user: dict = Depends(get_current_user)):
    """Preview CSV file content and return column headers and sample data"""
    try:
        content = await file.read()
        df = parse_csv_file(content)
        
        # Get column headers
        columns = list(df.columns)
        
        # Get first 5 rows as preview
        preview_data = df.head(5).to_dict('records')
        
        # Convert NaN to empty strings for JSON serialization
        preview_data = [{k: ("" if pd.isna(v) else v) for k, v in row.items()} for row in preview_data]
        
        return {
            "columns": columns,
            "preview_data": preview_data,
            "total_rows": len(df),
            "filename": file.filename
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error previewing CSV: {str(e)}")

@app.post("/api/import/csv/contacts")
async def import_contacts_from_csv(
    file: UploadFile = File(...),
    current_user: dict = Depends(get_current_user)
):
    """Import contacts from CSV file with mapping"""
    try:
        content = await file.read()
        df = parse_csv_file(content)
        
        # For now, use simple default mapping - will be enhanced with frontend mapping interface
        default_mappings = [
            ImportMappingField(csv_column="first_name", crm_field="first_name"),
            ImportMappingField(csv_column="last_name", crm_field="last_name"),
            ImportMappingField(csv_column="email", crm_field="email", transform_rule="lowercase"),
            ImportMappingField(csv_column="phone", crm_field="phone"),
            ImportMappingField(csv_column="city", crm_field="city"),
            ImportMappingField(csv_column="notes", crm_field="notes"),
        ]
        
        mapping_config = ContactImportMapping(mappings=default_mappings)
        
        return await process_contact_import(df, mapping_config, str(current_user["_id"]))
        
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error importing contacts: {str(e)}")

@app.post("/api/import/csv/contacts/mapped")
async def import_contacts_with_mapping(
    request: Request,
    file: UploadFile = File(...),
    current_user: dict = Depends(get_current_user)
):
    """Import contacts from CSV with custom mapping configuration sent as form data"""
    try:
        # Get form data
        form_data = await request.form()
        mappings = json.loads(form_data.get('mappings', '{}')) if form_data.get('mappings') else {}
        tag_ids = json.loads(form_data.get('tag_ids', '[]')) if form_data.get('tag_ids') else []
        
        content = await file.read()
        df = parse_csv_file(content)
        
        # Create mapping configuration
        mapping_list = [
            ImportMappingField(csv_column=sheet_column, crm_field=crm_field)
            for crm_field, sheet_column in mappings.items()
            if sheet_column  # Only include mapped fields
        ]
        
        mapping_config = ContactImportMapping(mappings=mapping_list, tag_ids=tag_ids)
        
        return await process_contact_import(df, mapping_config, str(current_user["_id"]))
        
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error importing contacts: {str(e)}")

@app.post("/api/import/csv/orders/mapped")
async def import_orders_with_mapping(
    request: Request,
    file: UploadFile = File(...),
    current_user: dict = Depends(get_current_user)
):
    """Import orders from CSV with custom mapping configuration sent as form data"""
    try:
        # Get form data
        form_data = await request.form()
        mappings = json.loads(form_data.get('mappings', '{}')) if form_data.get('mappings') else {}
        
        content = await file.read()
        df = parse_csv_file(content)
        
        # Create mapping configuration
        mapping_list = [
            ImportMappingField(csv_column=sheet_column, crm_field=crm_field)
            for crm_field, sheet_column in mappings.items()
            if sheet_column  # Only include mapped fields
        ]
        
        mapping_config = OrderImportMapping(mappings=mapping_list)
        
        return await process_order_import(df, mapping_config, str(current_user["_id"]))
        
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error importing orders: {str(e)}")

@app.post("/api/import/csv/orders")
async def import_orders_from_csv(
    file: UploadFile = File(...),
    current_user: dict = Depends(get_current_user)
):
    """Import orders from CSV file and associate with contacts via email"""
    try:
        content = await file.read()
        df = parse_csv_file(content)
        
        # Default mapping for orders
        default_mappings = [
            ImportMappingField(csv_column="email", crm_field="contact_email", transform_rule="lowercase"),
            ImportMappingField(csv_column="product_name", crm_field="product_name"),
            ImportMappingField(csv_column="quantity", crm_field="quantity"),
            ImportMappingField(csv_column="price", crm_field="unit_price"),
            ImportMappingField(csv_column="status", crm_field="status"),
            ImportMappingField(csv_column="payment_method", crm_field="payment_method"),
        ]
        
        mapping_config = OrderImportMapping(mappings=default_mappings)
        
        return await process_order_import(df, mapping_config, str(current_user["_id"]))
        
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error importing orders: {str(e)}")

async def process_contact_import(df: pd.DataFrame, mapping_config: ContactImportMapping, user_id: str) -> ImportResult:
    """Process contact import with mapping configuration"""
    results = ImportResult(
        total_rows=len(df),
        successful_imports=0,
        failed_imports=0,
        duplicates_skipped=0,
        errors=[],
        created_items=[]
    )
    
    for index, row in df.iterrows():
        try:
            # Convert row to dict and apply mapping
            row_dict = row.to_dict()
            mapped_data = apply_field_mapping(row_dict, mapping_config.mappings)
            
            # Check for duplicates by email
            email = mapped_data.get("email")
            if email and mapping_config.skip_duplicates:
                existing_contact = find_existing_contact_by_email(email)
                if existing_contact:
                    results.duplicates_skipped += 1
                    continue
            
            # Create contact
            contact_id = create_contact_from_mapped_data(mapped_data, mapping_config.tag_ids, user_id)
            results.created_items.append(contact_id)
            results.successful_imports += 1
            
        except Exception as e:
            results.failed_imports += 1
            results.errors.append(f"Row {index + 1}: {str(e)}")
    
    return results

async def process_order_import(df: pd.DataFrame, mapping_config: OrderImportMapping, user_id: str) -> ImportResult:
    """Process order import with contact association via email"""
    results = ImportResult(
        total_rows=len(df),
        successful_imports=0,
        failed_imports=0,
        duplicates_skipped=0,
        errors=[],
        created_items=[]
    )
    
    for index, row in df.iterrows():
        try:
            row_dict = row.to_dict()
            mapped_data = apply_field_mapping(row_dict, mapping_config.mappings)
            
            # Find contact by email
            contact_email = mapped_data.get("contact_email")
            contact_id = None
            
            if contact_email and mapping_config.associate_with_contacts:
                existing_contact = find_existing_contact_by_email(contact_email)
                
                if existing_contact:
                    contact_id = str(existing_contact["_id"])
                elif mapping_config.create_missing_contacts:
                    # Create minimal contact from email
                    new_contact_data = {
                        "first_name": "",
                        "last_name": "",
                        "email": contact_email,
                        "status": "lead",
                        "source": "order_import"
                    }
                    contact_id = create_contact_from_mapped_data(new_contact_data, [], user_id)
            
            # Create order
            order_doc = {
                "contact_id": contact_id,
                "order_number": generate_order_number(),
                "status": mapped_data.get("status", mapping_config.default_status),
                "payment_status": mapped_data.get("payment_status", mapping_config.default_payment_status),
                "payment_method": mapped_data.get("payment_method"),
                "notes": mapped_data.get("notes", ""),
                "total_amount": 0,  # Will be calculated from items
                "created_at": datetime.utcnow(),
                "updated_at": datetime.utcnow(),
                "created_by": user_id
            }
            
            # Insert order
            order_result = orders_collection.insert_one(order_doc)
            order_id = str(order_result.inserted_id)
            
            # Create order item
            unit_price = float(mapped_data.get("unit_price", 0))
            quantity = int(mapped_data.get("quantity", 1))
            total_price = unit_price * quantity
            
            item_doc = {
                "order_id": order_id,
                "product_name": mapped_data.get("product_name", "Imported Product"),
                "quantity": quantity,
                "unit_price": unit_price,
                "total_price": total_price,
                "created_at": datetime.utcnow()
            }
            
            order_items_collection.insert_one(item_doc)
            
            # Update order total
            orders_collection.update_one(
                {"_id": order_result.inserted_id},
                {"$set": {"total_amount": total_price}}
            )
            
            results.created_items.append(order_id)
            results.successful_imports += 1
            
        except Exception as e:
            results.failed_imports += 1
            results.errors.append(f"Row {index + 1}: {str(e)}")
    
    return results

# ===== GOOGLE SHEETS IMPORT ENDPOINTS =====

@app.post("/api/import/google-sheets/preview")
async def preview_google_sheets_import(request: dict, current_user: dict = Depends(get_current_user)):
    """Preview Google Sheets content and return column headers and sample data"""
    try:
        spreadsheet_id = request.get("spreadsheet_id")
        sheet_name = request.get("sheet_name", "")
        range_name = f"{sheet_name}!A:Z" if sheet_name else "A:Z"
        
        if not spreadsheet_id:
            raise HTTPException(status_code=400, detail="spreadsheet_id is required")
        
        df = get_google_sheet_data(spreadsheet_id, range_name)
        
        if df.empty:
            return {
                "columns": [],
                "preview_data": [],
                "total_rows": 0,
                "spreadsheet_id": spreadsheet_id
            }
        
        # Get column headers
        columns = list(df.columns)
        
        # Get first 5 rows as preview
        preview_data = df.head(5).fillna('').to_dict('records')
        
        return {
            "columns": columns,
            "preview_data": preview_data,
            "total_rows": len(df),
            "spreadsheet_id": spreadsheet_id
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error previewing Google Sheets: {str(e)}")

@app.post("/api/import/google-sheets/contacts")
async def import_contacts_from_google_sheets(request: dict, current_user: dict = Depends(get_current_user)):
    """Import contacts from Google Sheets with mapping"""
    try:
        spreadsheet_id = request.get("spreadsheet_id")
        sheet_name = request.get("sheet_name", "")
        mappings = request.get("mappings", {})
        tag_ids = request.get("tag_ids", [])
        
        if not spreadsheet_id:
            raise HTTPException(status_code=400, detail="spreadsheet_id is required")
        
        range_name = f"{sheet_name}!A:Z" if sheet_name else "A:Z"
        df = get_google_sheet_data(spreadsheet_id, range_name)
        
        if df.empty:
            return ImportResult(
                total_rows=0,
                successful_imports=0,
                failed_imports=0,
                duplicates_skipped=0,
                errors=[],
                created_items=[]
            )
        
        # Create mappings if not provided
        if not mappings:
            mappings = create_default_mappings(df.columns.tolist(), "contact")
        
        # Process contacts
        results = ImportResult(
            total_rows=len(df),
            successful_imports=0,
            failed_imports=0,
            duplicates_skipped=0,
            errors=[],
            created_items=[]
        )
        
        for index, row in df.iterrows():
            try:
                # Apply mappings
                contact_data = {}
                for crm_field, sheet_column in mappings.items():
                    if sheet_column in df.columns:
                        value = str(row[sheet_column]).strip() if pd.notna(row[sheet_column]) else ""
                        if value:
                            contact_data[crm_field] = value
                
                # Check for duplicates by email
                email = contact_data.get("email", "").lower()
                if email:
                    existing_contact = find_existing_contact_by_email(email)
                    if existing_contact:
                        results.duplicates_skipped += 1
                        continue
                
                # Create contact
                contact_id = create_contact_from_mapped_data(contact_data, tag_ids, str(current_user["_id"]))
                results.created_items.append(contact_id)
                results.successful_imports += 1
                
            except Exception as e:
                results.failed_imports += 1
                results.errors.append(f"Row {index + 1}: {str(e)}")
        
        return results
        
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error importing contacts from Google Sheets: {str(e)}")

@app.post("/api/import/google-sheets/orders")
async def import_orders_from_google_sheets(request: dict, current_user: dict = Depends(get_current_user)):
    """Import orders from Google Sheets and associate with contacts via email"""
    try:
        spreadsheet_id = request.get("spreadsheet_id")
        sheet_name = request.get("sheet_name", "")
        mappings = request.get("mappings", {})
        
        if not spreadsheet_id:
            raise HTTPException(status_code=400, detail="spreadsheet_id is required")
        
        range_name = f"{sheet_name}!A:Z" if sheet_name else "A:Z"
        df = get_google_sheet_data(spreadsheet_id, range_name)
        
        if df.empty:
            return ImportResult(
                total_rows=0,
                successful_imports=0,
                failed_imports=0,
                duplicates_skipped=0,
                errors=[],
                created_items=[]
            )
        
        # Create mappings if not provided
        if not mappings:
            mappings = create_default_mappings(df.columns.tolist(), "order")
        
        # Process orders
        results = ImportResult(
            total_rows=len(df),
            successful_imports=0,
            failed_imports=0,
            duplicates_skipped=0,
            errors=[],
            created_items=[]
        )
        
        for index, row in df.iterrows():
            try:
                # Apply mappings
                order_data = {}
                for crm_field, sheet_column in mappings.items():
                    if sheet_column in df.columns:
                        value = str(row[sheet_column]).strip() if pd.notna(row[sheet_column]) else ""
                        if value:
                            order_data[crm_field] = value
                
                # Find or create contact by email
                contact_email = order_data.get("contact_email", "").lower()
                contact_id = None
                
                if contact_email:
                    existing_contact = find_existing_contact_by_email(contact_email)
                    
                    if existing_contact:
                        contact_id = str(existing_contact["_id"])
                    else:
                        # Create minimal contact from email
                        new_contact_data = {
                            "first_name": "",
                            "last_name": "",
                            "email": contact_email,
                            "status": "lead",
                            "source": "google_sheets_import"
                        }
                        contact_id = create_contact_from_mapped_data(new_contact_data, [], str(current_user["_id"]))
                
                # Create order
                order_doc = {
                    "contact_id": contact_id,
                    "order_number": generate_order_number(),
                    "status": order_data.get("status", "pending"),
                    "payment_status": order_data.get("payment_status", "pending"),
                    "payment_method": order_data.get("payment_method"),
                    "notes": order_data.get("notes", "Imported from Google Sheets"),
                    "total_amount": 0,  # Will be calculated from items
                    "created_at": datetime.utcnow(),
                    "updated_at": datetime.utcnow(),
                    "created_by": str(current_user["_id"])
                }
                
                # Insert order
                order_result = orders_collection.insert_one(order_doc)
                order_id = str(order_result.inserted_id)
                
                # Create order item
                unit_price = float(order_data.get("unit_price", 0)) if order_data.get("unit_price") else 0
                quantity = int(float(order_data.get("quantity", 1))) if order_data.get("quantity") else 1
                total_price = unit_price * quantity
                
                item_doc = {
                    "order_id": order_id,
                    "product_name": order_data.get("product_name", "Imported Product"),
                    "quantity": quantity,
                    "unit_price": unit_price,
                    "total_price": total_price,
                    "created_at": datetime.utcnow()
                }
                
                order_items_collection.insert_one(item_doc)
                
                # Update order total
                orders_collection.update_one(
                    {"_id": order_result.inserted_id},
                    {"$set": {"total_amount": total_price}}
                )
                
                results.created_items.append(order_id)
                results.successful_imports += 1
                
            except Exception as e:
                results.failed_imports += 1
                results.errors.append(f"Row {index + 1}: {str(e)}")
        
        return results
        
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error importing orders from Google Sheets: {str(e)}")

def create_default_mappings(columns: List[str], import_type: str) -> Dict[str, str]:
    """Create default mapping based on common column names"""
    mappings = {}
    
    # Convert columns to lowercase for matching
    columns_lower = {col.lower(): col for col in columns}
    
    if import_type == "contact":
        field_variations = {
            'first_name': ['first name', 'firstname', 'first', 'nome', 'first_name'],
            'last_name': ['last name', 'lastname', 'last', 'cognome', 'surname', 'last_name'],
            'email': ['email', 'email address', 'e-mail', 'mail', 'posta'],
            'phone': ['phone', 'phone number', 'mobile', 'tel', 'telephone', 'telefono', 'cellulare'],
            'address': ['address', 'indirizzo', 'via'],
            'city': ['city', 'città', 'comune'],
            'postal_code': ['postal code', 'zip', 'cap', 'codice postale'],
            'country': ['country', 'paese', 'nazione'],
            'notes': ['notes', 'note', 'commenti', 'comments']
        }
    else:  # order
        field_variations = {
            'contact_email': ['email', 'customer email', 'client email', 'mail cliente'],
            'product_name': ['product', 'product name', 'prodotto', 'nome prodotto'],
            'quantity': ['quantity', 'qty', 'quantità', 'qta'],
            'unit_price': ['price', 'unit price', 'prezzo', 'prezzo unitario'],
            'status': ['status', 'stato', 'order status'],
            'payment_method': ['payment', 'payment method', 'pagamento', 'metodo pagamento'],
            'notes': ['notes', 'note', 'commenti', 'comments']
        }
    
    # Match columns to fields
    for crm_field, variations in field_variations.items():
        for variation in variations:
            if variation in columns_lower:
                mappings[crm_field] = columns_lower[variation]
                break
    
    return mappings

# ===== EMAIL UTILITY FUNCTIONS =====

async def get_email_settings(user_id: str) -> EmailSettings:
    """Get email settings for user, return default from environment if not found"""
    settings_doc = email_settings_collection.find_one({"user_id": user_id})
    if settings_doc:
        # Remove MongoDB specific fields
        settings_dict = {k: v for k, v in settings_doc.items() if k not in ['_id', 'user_id', 'created_at', 'updated_at']}
        return EmailSettings(**settings_dict)
    else:
        # Return settings from environment variables
        return EmailSettings(
            smtp_server=os.getenv("SMTP_SERVER", "smtp240.ext.armada.it"),
            smtp_port=int(os.getenv("SMTP_PORT", "587")),
            username=os.getenv("SMTP_USERNAME", "SMTP-PRO-15223"),
            password=os.getenv("SMTP_PASSWORD", "EiM5Tn5FKdTe"),
            from_email=os.getenv("SMTP_FROM_EMAIL", "grabovoi@wp-mail.org"),
            from_name=os.getenv("SMTP_FROM_NAME", "Grabovoi Foundation"),
            use_tls=os.getenv("SMTP_USE_TLS", "true").lower() == "true"
        )

async def send_email_smtp(to_email: str, subject: str, content: str, email_settings: EmailSettings) -> bool:
    """Send email via SMTP"""
    try:
        # Create message
        message = MIMEMultipart()
        message["From"] = f"{email_settings.from_name} <{email_settings.from_email}>"
        message["To"] = to_email
        message["Subject"] = subject
        
        # Add body
        message.attach(MIMEText(content, "html" if "<html>" in content.lower() else "plain", "utf-8"))
        
        # Send email
        await aiosmtplib.send(
            message,
            hostname=email_settings.smtp_server,
            port=email_settings.smtp_port,
            start_tls=email_settings.use_tls,
            username=email_settings.username,
            password=email_settings.password,
        )
        
        logger.info(f"Email sent successfully to {to_email}")
        return True
        
    except Exception as e:
        logger.error(f"Failed to send email to {to_email}: {str(e)}")
        return False

async def save_message(message_data: MessageCreate, user_id: str, status: str = "pending", error_message: str = None) -> str:
    """Save message to database"""
    # Get recipient name
    recipient_name = None
    if message_data.recipient_id:
        contact = contacts_collection.find_one({"_id": ObjectId(message_data.recipient_id)})
        if contact:
            recipient_name = f"{contact.get('first_name', '')} {contact.get('last_name', '')}".strip()
    
    message_doc = {
        "recipient_id": message_data.recipient_id,
        "recipient_email": message_data.recipient_email,
        "recipient_name": recipient_name,
        "subject": message_data.subject,
        "content": message_data.content,
        "message_type": message_data.message_type,
        "status": status,
        "sent_at": datetime.utcnow() if status == "sent" else None,
        "error_message": error_message,
        "created_by": user_id,
        "created_at": datetime.utcnow()
    }
    
    result = messages_collection.insert_one(message_doc)
    return str(result.inserted_id)

# ===== COURSE ENROLLMENT UTILITY FUNCTIONS =====

def enroll_contact_in_course(contact_id: str, course_id: str, source: str = "manual") -> str:
    """Enroll a contact in a course and update their status to student if needed"""
    # Check if already enrolled
    existing = course_enrollments_collection.find_one({
        "contact_id": contact_id,
        "course_id": course_id,
        "status": "active"
    })
    
    if existing:
        return str(existing["_id"])
    
    # Create enrollment
    enrollment_doc = {
        "contact_id": contact_id,
        "course_id": course_id,
        "enrolled_at": datetime.utcnow(),
        "status": "active",
        "source": source
    }
    
    result = course_enrollments_collection.insert_one(enrollment_doc)
    
    # Update contact status to student
    contacts_collection.update_one(
        {"_id": ObjectId(contact_id)},
        {"$set": {"status": "student", "updated_at": datetime.utcnow()}}
    )
    
    return str(result.inserted_id)

# ===== USER MANAGEMENT UTILITY FUNCTIONS =====

def generate_verification_token() -> str:
    """Generate a secure verification token"""
    import secrets
    return secrets.token_urlsafe(32)

def hash_password(password: str) -> str:
    """Hash password using bcrypt"""
    import bcrypt
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(password.encode('utf-8'), salt)
    return hashed.decode('utf-8')

def verify_password(password: str, hashed_password: str) -> bool:
    """Verify password against hash"""
    import bcrypt
    return bcrypt.checkpw(password.encode('utf-8'), hashed_password.encode('utf-8'))

async def send_verification_email(email: str, token: str, user_name: str = None):
    """Send email verification email"""
    try:
        # Get email settings
        settings_doc = email_settings_collection.find_one({})
        if not settings_doc:
            # Use settings from environment variables
            settings = EmailSettings(
                smtp_server=os.getenv("SMTP_SERVER", "smtp240.ext.armada.it"),
                smtp_port=int(os.getenv("SMTP_PORT", "587")),
                username=os.getenv("SMTP_USERNAME", "SMTP-PRO-15223"),
                password=os.getenv("SMTP_PASSWORD", "EiM5Tn5FKdTe"),
                from_email=os.getenv("SMTP_FROM_EMAIL", "grabovoi@wp-mail.org"),
                from_name=os.getenv("SMTP_FROM_NAME", "Grabovoi Foundation"),
                use_tls=os.getenv("SMTP_USE_TLS", "true").lower() == "true"
            )
        else:
            settings_dict = {k: v for k, v in settings_doc.items() if k not in ['_id', 'user_id', 'created_at', 'updated_at']}
            settings = EmailSettings(**settings_dict)
        
        # Create verification link - use environment variable for production URL
        base_url = os.getenv("FRONTEND_URL", "https://grabovoi.crm.co.it")
        verification_link = f"{base_url}/verify-email?token={token}"
        
        subject = "Verifica la tua email - CRM Grabovoi Foundation"
        
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>Verifica Email</title>
        </head>
        <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333; max-width: 600px; margin: 0 auto; padding: 20px;">
            <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); padding: 30px; text-align: center; border-radius: 10px 10px 0 0;">
                <h1 style="color: white; margin: 0; font-size: 28px;">🎯 CRM Grabovoi Foundation</h1>
            </div>
            
            <div style="background: #f8f9fa; padding: 30px; border-radius: 0 0 10px 10px; border: 1px solid #e9ecef;">
                <h2 style="color: #495057; margin-top: 0;">Ciao {user_name or 'Utente'}! 👋</h2>
                
                <p style="font-size: 16px; margin-bottom: 25px;">
                    Benvenuto nel <strong>CRM Grabovoi Foundation</strong>! Per completare la registrazione, 
                    devi verificare il tuo indirizzo email.
                </p>
                
                <div style="text-align: center; margin: 30px 0;">
                    <a href="{verification_link}" 
                       style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); 
                              color: white; 
                              padding: 15px 30px; 
                              text-decoration: none; 
                              border-radius: 50px; 
                              font-weight: bold; 
                              font-size: 16px; 
                              display: inline-block;
                              box-shadow: 0 4px 15px rgba(102, 126, 234, 0.4);">
                        ✅ Verifica Email
                    </a>
                </div>
                
                <p style="font-size: 14px; color: #6c757d; margin-top: 25px;">
                    Se non hai creato questo account, puoi ignorare questa email.<br>
                    Il link di verifica scadrà tra 24 ore.
                </p>
                
                <hr style="border: none; height: 1px; background: #dee2e6; margin: 25px 0;">
                
                <p style="font-size: 12px; color: #868e96; text-align: center;">
                    © 2025 CRM Grabovoi Foundation. Tutti i diritti riservati.
                </p>
            </div>
        </body>
        </html>
        """
        
        text_content = f"""
        Ciao {user_name or 'Utente'}!
        
        Benvenuto nel CRM Grabovoi Foundation! 
        Per completare la registrazione, devi verificare il tuo indirizzo email.
        
        Clicca sul seguente link per verificare:
        {verification_link}
        
        Se non hai creato questo account, puoi ignorare questa email.
        Il link di verifica scadrà tra 24 ore.
        
        © 2025 CRM Grabovoi Foundation
        """
        
        # Send email
        success = await send_email_smtp(email, subject, html_content, settings)
        
        if success:
            logger.info(f"Verification email sent successfully to {email}")
        else:
            logger.error(f"Failed to send verification email to {email}")
            
        return success
        
    except Exception as e:
        logger.error(f"Error sending verification email: {str(e)}")
        return False

async def send_password_reset_email(email: str, token: str, user_name: str = None):
    """Send password reset email"""
    try:
        # Get email settings
        settings_doc = email_settings_collection.find_one({})
        if not settings_doc:
            # Use settings from environment variables
            settings = EmailSettings(
                smtp_server=os.getenv("SMTP_SERVER", "smtp240.ext.armada.it"),
                smtp_port=int(os.getenv("SMTP_PORT", "587")),
                username=os.getenv("SMTP_USERNAME", "SMTP-PRO-15223"),
                password=os.getenv("SMTP_PASSWORD", "EiM5Tn5FKdTe"),
                from_email=os.getenv("SMTP_FROM_EMAIL", "grabovoi@wp-mail.org"),
                from_name=os.getenv("SMTP_FROM_NAME", "Grabovoi Foundation"),
                use_tls=os.getenv("SMTP_USE_TLS", "true").lower() == "true"
            )
        else:
            settings_dict = {k: v for k, v in settings_doc.items() if k not in ['_id', 'user_id', 'created_at', 'updated_at']}
            settings = EmailSettings(**settings_dict)
        
        base_url = os.getenv("FRONTEND_URL", "https://grabovoi.crm.co.it")
        reset_link = f"{base_url}/reset-password?token={token}"
        
        subject = "Reset Password - CRM Grabovoi Foundation"
        
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <title>Reset Password</title>
        </head>
        <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333; max-width: 600px; margin: 0 auto; padding: 20px;">
            <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); padding: 30px; text-align: center; border-radius: 10px 10px 0 0;">
                <h1 style="color: white; margin: 0; font-size: 28px;">🔐 Reset Password</h1>
            </div>
            
            <div style="background: #f8f9fa; padding: 30px; border-radius: 0 0 10px 10px; border: 1px solid #e9ecef;">
                <h2 style="color: #495057; margin-top: 0;">Ciao {user_name or 'Utente'}!</h2>
                
                <p>Hai richiesto di reimpostare la tua password. Clicca sul pulsante qui sotto per continuare:</p>
                
                <div style="text-align: center; margin: 30px 0;">
                    <a href="{reset_link}" 
                       style="background: linear-gradient(135deg, #dc3545 0%, #c82333 100%); 
                              color: white; 
                              padding: 15px 30px; 
                              text-decoration: none; 
                              border-radius: 50px; 
                              font-weight: bold; 
                              display: inline-block;">
                        🔐 Reimposta Password
                    </a>
                </div>
                
                <p style="font-size: 14px; color: #6c757d;">
                    Se non hai richiesto questa reimpostazione, puoi ignorare questa email.<br>
                    Il link scadrà tra 1 ora.
                </p>
            </div>
        </body>
        </html>
        """
        
        success = await send_email_smtp(email, subject, html_content, settings)
        return success
        
    except Exception as e:
        logger.error(f"Error sending password reset email: {str(e)}")
        return False

def process_order_course_associations(order_id: str, contact_id: str):
    """Process course associations for an order based on products and tags"""
    # Get order items
    items = list(order_items_collection.find({"order_id": order_id}))
    
    for item in items:
        # Check if product is associated with a course (by name matching or product category)
        product_name = item.get("product_name", "").lower()
        
        # Direct course association (if product name contains course keywords)
        if "corso" in product_name or "course" in product_name:
            # Try to find matching course
            course = courses_collection.find_one({
                "$or": [
                    {"title": {"$regex": product_name.replace("corso ", ""), "$options": "i"}},
                    {"category": {"$regex": "corso", "$options": "i"}}
                ]
            })
            
            if course:
                enroll_contact_in_course(contact_id, str(course["_id"]), "order")
        
        # Check product-related tags for course associations
        if item.get("product_id"):
            product = products_collection.find_one({"_id": ObjectId(item["product_id"])})
            if product and product.get("category") == "corso":
                # Find course with same category or name
                course = courses_collection.find_one({
                    "$or": [
                        {"title": {"$regex": product.get("name", ""), "$options": "i"}},
                        {"category": product.get("category")}
                    ]
                })
                
                if course:
                    enroll_contact_in_course(contact_id, str(course["_id"]), "order")

def check_tag_course_associations(contact_id: str):
    """Check if contact tags are associated with courses and enroll accordingly"""
    # Get contact tags
    contact_tags = list(contact_tags_collection.find({"contact_id": contact_id}))
    tag_ids = [ct["tag_id"] for ct in contact_tags]
    
    if not tag_ids:
        return
    
    # Get tags details
    tags = list(tags_collection.find({"_id": {"$in": [ObjectId(tid) for tid in tag_ids]}}))
    
    for tag in tags:
        # Check if tag is associated with courses
        tag_name = tag.get("name", "").lower()
        tag_category = tag.get("category", "").lower()
        
        # Look for courses with matching category or title
        if "corso" in tag_name or "course" in tag_name or tag_category == "corso":
            # Find matching courses
            courses = list(courses_collection.find({
                "$or": [
                    {"title": {"$regex": tag_name.replace("corso ", ""), "$options": "i"}},
                    {"category": {"$regex": tag_category, "$options": "i"}},
                    {"category": "corso"}
                ]
            }))
            
            for course in courses:
                enroll_contact_in_course(contact_id, str(course["_id"]), "tag")

# ===== WOOCOMMERCE SYNC SERVICES =====

class WooCommerceSyncService:
    """Service for synchronizing data from WooCommerce to CRM"""
    
    def __init__(self):
        self.wc_client = woocommerce_client
        
    async def sync_customers_from_woocommerce(self, incremental: bool = True) -> dict:
        """Sync customers from WooCommerce to contacts collection"""
        if not self.wc_client:
            raise Exception("WooCommerce client not available")
        
        logger.info("Starting WooCommerce customer sync")
        
        # Log sync start
        sync_log_doc = {
            "entity_type": "customers",
            "sync_type": "incremental" if incremental else "full", 
            "status": "started",
            "records_processed": 0,
            "started_at": datetime.utcnow()
        }
        sync_log_result = wc_sync_logs_collection.insert_one(sync_log_doc)
        sync_log_id = sync_log_result.inserted_id
        
        try:
            # Determine last sync time for incremental updates
            last_sync_time = None
            if incremental:
                last_customer = wc_customers_collection.find_one(
                    sort=[("last_sync", -1)]
                )
                if last_customer:
                    last_sync_time = last_customer["last_sync"] - timedelta(minutes=5)
            
            page = 1
            total_synced = 0
            
            while True:
                logger.info(f"Fetching WooCommerce customers page {page}")
                
                # Build API parameters
                params = {
                    "per_page": 100,
                    "page": page,
                    "orderby": "registered_date",
                    "order": "desc"
                }
                
                if last_sync_time:
                    params["modified_after"] = last_sync_time.isoformat()
                
                # Get customers from WooCommerce
                logger.info(f"Making WooCommerce API call with params: {params}")
                response = self.wc_client.get("customers", params=params)
                logger.info(f"WooCommerce API response status: {response.status_code}")
                
                if response.status_code != 200:
                    logger.error(f"WooCommerce API error - Status: {response.status_code}, Response: {response.text}")
                    raise Exception(f"WooCommerce API error: {response.status_code} - {response.text}")
                
                customers_data = response.json()
                logger.info(f"Retrieved {len(customers_data)} customers from WooCommerce")
                
                if not customers_data:
                    break
                
                for customer_data in customers_data:
                    try:
                        logger.debug(f"Processing customer ID: {customer_data.get('id')}")
                        # Transform WooCommerce customer to CRM contact
                        contact_doc = self._transform_wc_customer_to_contact(customer_data)
                        logger.debug(f"Transformed customer data: {contact_doc.get('email')}")
                        
                        # Check if contact already exists by email or WooCommerce ID
                        logger.debug(f"Checking for existing contact: {contact_doc['email']}")
                        existing_contact = contacts_collection.find_one({
                            "$or": [
                                {"email": contact_doc["email"]},
                                {"woocommerce_id": customer_data["id"]}
                            ]
                        })
                        
                        if existing_contact:
                            # Update existing contact
                            contact_doc["updated_at"] = datetime.utcnow()
                            contacts_collection.update_one(
                                {"_id": existing_contact["_id"]},
                                {"$set": contact_doc}
                            )
                            logger.info(f"Updated contact: {contact_doc['email']}")
                        else:
                            # Create new contact
                            contact_doc["created_at"] = datetime.utcnow()
                            contact_doc["updated_at"] = datetime.utcnow()
                            result = contacts_collection.insert_one(contact_doc)
                            logger.info(f"Created new contact: {contact_doc['email']}")
                        
                        # Store WooCommerce customer data
                        wc_customer_doc = {
                            "woocommerce_id": customer_data["id"],
                            "email": customer_data.get("email", ""),
                            "first_name": customer_data.get("first_name", ""),
                            "last_name": customer_data.get("last_name", ""),
                            "username": customer_data.get("username", ""),
                            "billing_address": customer_data.get("billing", {}),
                            "shipping_address": customer_data.get("shipping", {}),
                            "phone": customer_data.get("billing", {}).get("phone", ""),
                            "total_spent": float(customer_data.get("total_spent", 0)),
                            "orders_count": customer_data.get("orders_count", 0),
                            "date_created_wc": date_parser.parse(customer_data["date_created"]),
                            "date_modified_wc": date_parser.parse(customer_data["date_modified"]),
                            "last_sync": datetime.utcnow()
                        }
                        
                        wc_customers_collection.update_one(
                            {"woocommerce_id": customer_data["id"]},
                            {"$set": wc_customer_doc},
                            upsert=True
                        )
                        
                        total_synced += 1
                        
                    except Exception as e:
                        logger.error(f"Error processing customer {customer_data.get('id')}: {e}")
                        continue
                
                if len(customers_data) < 100:
                    break
                page += 1
            
            # Mark sync as completed
            wc_sync_logs_collection.update_one(
                {"_id": sync_log_id},
                {
                    "$set": {
                        "status": "completed",
                        "records_processed": total_synced,
                        "completed_at": datetime.utcnow()
                    }
                }
            )
            
            logger.info(f"WooCommerce customer sync completed. Processed {total_synced} customers")
            return {"success": True, "records_processed": total_synced}
            
        except Exception as e:
            # Mark sync as failed with detailed error information
            import traceback
            error_details = f"Exception type: {type(e).__name__}, Message: {str(e)}, Traceback: {traceback.format_exc()}"
            
            wc_sync_logs_collection.update_one(
                {"_id": sync_log_id},
                {
                    "$set": {
                        "status": "failed",
                        "error_message": error_details,
                        "completed_at": datetime.utcnow()
                    }
                }
            )
            logger.error(f"WooCommerce customer sync failed - {type(e).__name__}: {str(e) or 'No error message'}")
            logger.error(f"Full traceback: {traceback.format_exc()}")
            raise

    def _transform_wc_customer_to_contact(self, wc_customer: dict) -> dict:
        """Transform WooCommerce customer to CRM contact format"""
        billing = wc_customer.get("billing", {})
        shipping = wc_customer.get("shipping", {})
        
        # Detect language from country
        country = billing.get("country", "").upper()
        language = self._detect_language_from_country(country)
        
        return {
            "woocommerce_id": wc_customer["id"],
            "first_name": wc_customer.get("first_name", billing.get("first_name", "")),
            "last_name": wc_customer.get("last_name", billing.get("last_name", "")),
            "email": wc_customer.get("email", billing.get("email", "")),
            "phone": billing.get("phone", ""),
            "address": billing.get("address_1", ""),
            "city": billing.get("city", ""),
            "postal_code": billing.get("postcode", ""),
            "country": country,
            "language": language,
            "status": "client",  # WooCommerce customers are clients
            "source": "woocommerce",
            "notes": f"Importato da WooCommerce. Ordini totali: {wc_customer.get('orders_count', 0)}, Spesa totale: €{wc_customer.get('total_spent', 0)}",
            "wc_total_spent": float(wc_customer.get("total_spent", 0)),
            "wc_orders_count": wc_customer.get("orders_count", 0)
        }

    def _detect_language_from_country(self, country_code: str) -> str:
        """Detect language from country code"""
        country_language_map = {
            "IT": "it", "SM": "it", "VA": "it",  # Italian
            "FR": "fr", "BE": "fr", "CH": "fr", "MC": "fr",  # French
            "DE": "de", "AT": "de", "LI": "de",  # German
            "ES": "es", "AD": "es", "AR": "es", "MX": "es", "CO": "es",  # Spanish
            "GB": "en", "US": "en", "AU": "en", "CA": "en",  # English
            "PT": "pt", "BR": "pt",  # Portuguese
            "NL": "nl", "BE": "nl",  # Dutch
            "PL": "pl",  # Polish
            "RU": "ru",  # Russian
        }
        
        return country_language_map.get(country_code.upper(), "it")  # Default to Italian
    
    async def sync_products_from_woocommerce(self, incremental: bool = True) -> dict:
        """Sync products from WooCommerce to products collection"""
        if not self.wc_client:
            raise Exception("WooCommerce client not available")
        
        logger.info("Starting WooCommerce product sync")
        
        sync_log_doc = {
            "entity_type": "products",
            "sync_type": "incremental" if incremental else "full",
            "status": "started", 
            "records_processed": 0,
            "started_at": datetime.utcnow()
        }
        sync_log_result = wc_sync_logs_collection.insert_one(sync_log_doc)
        sync_log_id = sync_log_result.inserted_id
        
        try:
            last_sync_time = None
            if incremental:
                last_product = wc_products_collection.find_one(
                    sort=[("last_sync", -1)]
                )
                if last_product:
                    last_sync_time = last_product["last_sync"] - timedelta(minutes=5)
            
            page = 1
            total_synced = 0
            
            while True:
                logger.info(f"Fetching WooCommerce products page {page}")
                
                params = {
                    "per_page": 100,
                    "page": page,
                    "orderby": "modified",
                    "order": "desc"
                }
                
                if last_sync_time:
                    params["modified_after"] = last_sync_time.isoformat()
                
                response = self.wc_client.get("products", params=params)
                
                if response.status_code != 200:
                    logger.error(f"WooCommerce API error - Status: {response.status_code}, Response: {response.text}")
                    raise Exception(f"WooCommerce API error: {response.status_code} - {response.text}")
                
                products_data = response.json()
                
                if not products_data:
                    break
                
                for product_data in products_data:
                    try:
                        # Transform and store in CRM products
                        product_doc = self._transform_wc_product_to_crm(product_data)
                        
                        existing_product = products_collection.find_one({
                            "$or": [
                                {"sku": product_doc.get("sku")},
                                {"woocommerce_id": product_data["id"]}
                            ]
                        })
                        
                        if existing_product:
                            product_doc["updated_at"] = datetime.utcnow()
                            products_collection.update_one(
                                {"_id": existing_product["_id"]},
                                {"$set": product_doc}
                            )
                            product_id = str(existing_product["_id"])
                            logger.info(f"Updated product: {product_doc['name']}")
                        else:
                            product_doc["created_at"] = datetime.utcnow()
                            product_doc["updated_at"] = datetime.utcnow()
                            result = products_collection.insert_one(product_doc)
                            product_id = str(result.inserted_id)
                            logger.info(f"Created new product: {product_doc['name']}")
                        
                        # Create corresponding course if product contains course keywords
                        await self._create_course_from_product_if_needed(product_doc, product_id)
                        
                        # Store WooCommerce product data
                        wc_product_doc = {
                            "woocommerce_id": product_data["id"],
                            "name": product_data.get("name", ""),
                            "slug": product_data.get("slug", ""),
                            "sku": product_data.get("sku", ""),
                            "price": float(product_data.get("price", 0)),
                            "regular_price": float(product_data.get("regular_price", 0)),
                            "sale_price": float(product_data.get("sale_price", 0) or 0),
                            "description": product_data.get("description", ""),
                            "short_description": product_data.get("short_description", ""),
                            "categories": product_data.get("categories", []),
                            "tags": product_data.get("tags", []),
                            "stock_quantity": product_data.get("stock_quantity"),
                            "stock_status": product_data.get("stock_status", ""),
                            "date_created_wc": date_parser.parse(product_data["date_created"]),
                            "date_modified_wc": date_parser.parse(product_data["date_modified"]),
                            "last_sync": datetime.utcnow()
                        }
                        
                        wc_products_collection.update_one(
                            {"woocommerce_id": product_data["id"]},
                            {"$set": wc_product_doc},
                            upsert=True
                        )
                        
                        total_synced += 1
                        
                    except Exception as e:
                        logger.error(f"Error processing product {product_data.get('id')}: {e}")
                        continue
                
                if len(products_data) < 100:
                    break
                page += 1
            
            wc_sync_logs_collection.update_one(
                {"_id": sync_log_id},
                {
                    "$set": {
                        "status": "completed",
                        "records_processed": total_synced,
                        "completed_at": datetime.utcnow()
                    }
                }
            )
            
            logger.info(f"WooCommerce product sync completed. Processed {total_synced} products")
            return {"success": True, "records_processed": total_synced}
            
        except Exception as e:
            # Mark sync as failed with detailed error information
            import traceback
            error_details = f"Exception type: {type(e).__name__}, Message: {str(e)}, Traceback: {traceback.format_exc()}"
            
            wc_sync_logs_collection.update_one(
                {"_id": sync_log_id},
                {
                    "$set": {
                        "status": "failed", 
                        "error_message": error_details,
                        "completed_at": datetime.utcnow()
                    }
                }
            )
            logger.error(f"WooCommerce product sync failed - {type(e).__name__}: {str(e) or 'No error message'}")
            logger.error(f"Full traceback: {traceback.format_exc()}")
            raise

    def _transform_wc_product_to_crm(self, wc_product: dict) -> dict:
        """Transform WooCommerce product to CRM product format"""
        product_name = wc_product.get("name", "")
        language = self._detect_language_from_text(product_name)
        
        return {
            "woocommerce_id": wc_product["id"],
            "name": product_name,
            "description": wc_product.get("description", ""),
            "price": float(wc_product.get("price", 0)),
            "sku": wc_product.get("sku", ""),
            "category": self._categorize_product(product_name),
            "language": language,
            "is_active": wc_product.get("status") == "publish",
            "stock_quantity": wc_product.get("stock_quantity", 0),
            "stock_status": wc_product.get("stock_status", ""),
            "source": "woocommerce"
        }
    
    async def sync_orders_from_woocommerce(self, incremental: bool = True) -> dict:
        """Sync orders from WooCommerce to orders collection with contact association"""
        if not self.wc_client:
            raise Exception("WooCommerce client not available")
        
        logger.info("Starting WooCommerce order sync")
        
        sync_log_doc = {
            "entity_type": "orders",
            "sync_type": "incremental" if incremental else "full",
            "status": "started",
            "records_processed": 0, 
            "started_at": datetime.utcnow()
        }
        sync_log_result = wc_sync_logs_collection.insert_one(sync_log_doc)
        sync_log_id = sync_log_result.inserted_id
        
        try:
            last_sync_time = None
            if incremental:
                last_order = wc_orders_collection.find_one(
                    sort=[("last_sync", -1)]
                )
                if last_order:
                    last_sync_time = last_order["last_sync"] - timedelta(minutes=5)
            
            page = 1
            total_synced = 0
            
            while True:
                logger.info(f"Fetching WooCommerce orders page {page}")
                
                params = {
                    "per_page": 100,
                    "page": page,
                    "orderby": "modified",
                    "order": "desc"
                }
                
                if last_sync_time:
                    params["modified_after"] = last_sync_time.isoformat()
                
                response = self.wc_client.get("orders", params=params)
                
                if response.status_code != 200:
                    logger.error(f"WooCommerce API error - Status: {response.status_code}, Response: {response.text}")
                    raise Exception(f"WooCommerce API error: {response.status_code} - {response.text}")
                
                orders_data = response.json()
                
                if not orders_data:
                    break
                
                for order_data in orders_data:
                    try:
                        # Transform and associate with CRM contact
                        contact_id = await self._find_or_create_contact_for_order(order_data)
                        
                        order_doc = self._transform_wc_order_to_crm(order_data, contact_id)
                        
                        existing_order = orders_collection.find_one({
                            "woocommerce_id": order_data["id"]
                        })
                        
                        if existing_order:
                            order_doc["updated_at"] = datetime.utcnow()
                            orders_collection.update_one(
                                {"_id": existing_order["_id"]},
                                {"$set": order_doc}
                            )
                            order_id = str(existing_order["_id"])
                            logger.info(f"Updated order: {order_doc['order_number']}")
                        else:
                            order_doc["created_at"] = datetime.utcnow()
                            order_doc["updated_at"] = datetime.utcnow()
                            result = orders_collection.insert_one(order_doc)
                            order_id = str(result.inserted_id)
                            logger.info(f"Created new order: {order_doc['order_number']}")
                        
                        # Store order items
                        await self._sync_order_items(order_id, order_data.get("line_items", []))
                        
                        # Store WooCommerce order data
                        wc_order_doc = {
                            "woocommerce_id": order_data["id"],
                            "order_number": order_data.get("number", ""),
                            "woocommerce_customer_id": order_data.get("customer_id", 0),
                            "crm_contact_id": contact_id,
                            "status": order_data.get("status", ""),
                            "currency": order_data.get("currency", "EUR"),
                            "total": float(order_data.get("total", 0)),
                            "total_tax": float(order_data.get("total_tax", 0)),
                            "shipping_total": float(order_data.get("shipping_total", 0)),
                            "payment_method": order_data.get("payment_method", ""),
                            "payment_method_title": order_data.get("payment_method_title", ""),
                            "billing_address": order_data.get("billing", {}),
                            "shipping_address": order_data.get("shipping", {}),
                            "line_items": order_data.get("line_items", []),
                            "date_created_wc": date_parser.parse(order_data["date_created"]),
                            "date_modified_wc": date_parser.parse(order_data["date_modified"]),
                            "date_completed_wc": date_parser.parse(order_data["date_completed"]) if order_data.get("date_completed") else None,
                            "last_sync": datetime.utcnow()
                        }
                        
                        wc_orders_collection.update_one(
                            {"woocommerce_id": order_data["id"]},
                            {"$set": wc_order_doc},
                            upsert=True
                        )
                        
                        total_synced += 1
                        
                    except Exception as e:
                        logger.error(f"Error processing order {order_data.get('id')}: {e}")
                        continue
                
                if len(orders_data) < 100:
                    break
                page += 1
            
            wc_sync_logs_collection.update_one(
                {"_id": sync_log_id},
                {
                    "$set": {
                        "status": "completed",
                        "records_processed": total_synced,
                        "completed_at": datetime.utcnow()
                    }
                }
            )
            
            logger.info(f"WooCommerce order sync completed. Processed {total_synced} orders")
            return {"success": True, "records_processed": total_synced}
            
        except Exception as e:
            # Mark sync as failed with detailed error information
            import traceback
            error_details = f"Exception type: {type(e).__name__}, Message: {str(e)}, Traceback: {traceback.format_exc()}"
            
            wc_sync_logs_collection.update_one(
                {"_id": sync_log_id},
                {
                    "$set": {
                        "status": "failed",
                        "error_message": error_details,
                        "completed_at": datetime.utcnow()
                    }
                }
            )
            logger.error(f"WooCommerce order sync failed - {type(e).__name__}: {str(e) or 'No error message'}")
            logger.error(f"Full traceback: {traceback.format_exc()}")
            raise

    async def _find_or_create_contact_for_order(self, order_data: dict) -> Optional[str]:
        """Find existing contact by email or create new contact for WooCommerce order"""
        billing = order_data.get("billing", {})
        email = billing.get("email", "").strip().lower()
        
        if not email:
            return None
        
        # Try to find existing contact
        existing_contact = contacts_collection.find_one({"email": email})
        
        if existing_contact:
            return str(existing_contact["_id"])
        
        # Create new contact from order billing data
        language = self._detect_language_from_country(billing.get("country", ""))
        
        contact_doc = {
            "first_name": billing.get("first_name", ""),
            "last_name": billing.get("last_name", ""), 
            "email": email,
            "phone": billing.get("phone", ""),
            "address": billing.get("address_1", ""),
            "city": billing.get("city", ""),
            "postal_code": billing.get("postcode", ""),
            "country": billing.get("country", "").upper(),
            "language": language,
            "status": "client",
            "source": "woocommerce_order",
            "notes": f"Contatto creato da ordine WooCommerce #{order_data.get('number', '')}",
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        }
        
        result = contacts_collection.insert_one(contact_doc)
        logger.info(f"Created new contact from WooCommerce order: {email}")
        return str(result.inserted_id)

    def _transform_wc_order_to_crm(self, wc_order: dict, contact_id: Optional[str]) -> dict:
        """Transform WooCommerce order to CRM order format"""
        billing = wc_order.get("billing", {})
        
        # Detect language from country or order content
        country = billing.get("country", "").upper()
        language = self._detect_language_from_country(country)
        
        # Also try to detect from line items
        if not language or language == "it":
            line_items = wc_order.get("line_items", [])
            if line_items:
                first_item_name = line_items[0].get("name", "")
                detected_lang = self._detect_language_from_text(first_item_name)
                if detected_lang != "it":
                    language = detected_lang
        
        return {
            "woocommerce_id": wc_order["id"],
            "contact_id": contact_id,
            "order_number": f"WC-{wc_order.get('number', wc_order['id'])}",
            "total_amount": float(wc_order.get("total", 0)),
            "status": "completed" if wc_order.get("status") in ["completed", "processing"] else "pending",
            "payment_status": "paid" if wc_order.get("status") == "completed" else "pending",
            "payment_method": wc_order.get("payment_method_title", wc_order.get("payment_method", "")),
            "notes": f"Ordine WooCommerce #{wc_order.get('number', '')}. Stato: {wc_order.get('status', '')}",
            "source": "woocommerce",
            "language": language,
            "wc_currency": wc_order.get("currency", "EUR"),
            "wc_total_tax": float(wc_order.get("total_tax", 0)),
            "wc_shipping_total": float(wc_order.get("shipping_total", 0))
        }
    
    async def _sync_order_items(self, order_id: str, line_items: List[dict]):
        """Sync order line items to order_items collection and create missing products/courses"""
        # Remove existing items for this order
        order_items_collection.delete_many({"order_id": order_id})
        
        for item_data in line_items:
            # Try to find matching product by SKU or name
            product = None
            sku = item_data.get("sku", "")
            product_name = item_data.get("name", "")
            
            if sku:
                product = products_collection.find_one({"sku": sku})
            
            # If not found by SKU, try by name similarity (for products like "corso ringiovanimento in 3 rate")
            if not product and product_name:
                # Extract base product name (remove rate specifications)
                base_name = self._extract_base_product_name(product_name)
                product = products_collection.find_one({
                    "name": {"$regex": base_name, "$options": "i"}
                })
            
            # If product doesn't exist, create it automatically
            if not product:
                product_id = await self._create_product_from_order_item(item_data)
                logger.info(f"Created new product from order item: {product_name}")
            else:
                product_id = str(product["_id"])
            
            # Store rate information if present
            rate_info = self._extract_rate_info(product_name)
            
            item_doc = {
                "order_id": order_id,
                "product_id": product_id,
                "product_name": product_name,
                "sku": sku,
                "quantity": item_data.get("quantity", 1),
                "unit_price": float(item_data.get("price", 0)),
                "total_price": float(item_data.get("total", 0)),
                "woocommerce_item_id": item_data.get("id"),
                "rate_info": rate_info,  # Store rate information (es. "3 rate")
                "created_at": datetime.utcnow()
            }
            
            order_items_collection.insert_one(item_doc)

    def _extract_base_product_name(self, product_name: str) -> str:
        """Extract base product name removing rate specifications"""
        # Convert to lower for comparison
        name_lower = product_name.lower()
        
        # Remove common rate patterns
        rate_patterns = [
            r'\s*in\s*\d+\s*rate?\s*', 
            r'\s*-\s*\d+\s*rate?\s*',
            r'\s*\(\d+\s*rate?\)\s*',
            r'\s*€\s*\d+[,.]?\d*\s*x\s*\d+\s*mois?\s*',
            r'\s*-\s*€\s*[\d,]+\.?\d*\s*',
            r'\s*€\s*[\d,]+\.?\d*\s*'
        ]
        
        import re
        base_name = product_name
        for pattern in rate_patterns:
            base_name = re.sub(pattern, '', base_name, flags=re.IGNORECASE)
        
        # Clean up extra spaces
        base_name = ' '.join(base_name.split())
        
        return base_name.strip()

    def _extract_rate_info(self, product_name: str) -> Optional[dict]:
        """Extract rate information from product name"""
        import re
        
        # Look for rate patterns
        rate_match = re.search(r'(\d+)\s*rate?', product_name, re.IGNORECASE)
        if rate_match:
            return {
                "num_rates": int(rate_match.group(1)),
                "type": "rate"
            }
        
        # Look for monthly payments (mois)
        monthly_match = re.search(r'€\s*([\d,]+\.?\d*)\s*x\s*(\d+)\s*mois?', product_name, re.IGNORECASE)
        if monthly_match:
            return {
                "monthly_amount": float(monthly_match.group(1).replace(',', '.')),
                "num_months": int(monthly_match.group(2)),
                "type": "monthly"
            }
        
        return None

    async def _create_product_from_order_item(self, item_data: dict) -> str:
        """Create product automatically from order item data"""
        product_name = item_data.get("name", "")
        base_name = self._extract_base_product_name(product_name)
        
        # Detect language from product name
        language = self._detect_language_from_text(product_name)
        
        product_doc = {
            "name": base_name,
            "description": f"Prodotto creato automaticamente da ordine WooCommerce",
            "price": float(item_data.get("price", 0)),
            "sku": item_data.get("sku", f"WC-AUTO-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}"),
            "category": self._categorize_product(base_name),
            "is_active": True,
            "source": "woocommerce_auto",
            "language": language,
            "wc_original_name": product_name,  # Keep original for reference
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        }
        
        result = products_collection.insert_one(product_doc)
        product_id = str(result.inserted_id)
        
        # If product contains "corso" or "formazione", create corresponding course
        await self._create_course_from_product_if_needed(product_doc, product_id)
        
        return product_id

    def _detect_language_from_text(self, text: str) -> str:
        """Detect language from product text"""
        text_lower = text.lower()
        
        # Italian indicators
        italian_words = ['corso', 'formazione', 'rate', 'ringiovanimento', 'euro', 'mese', 'mesi']
        # French indicators  
        french_words = ['formation', 'cours', 'mois', 'officielle', 'rejuvenation']
        # German indicators
        german_words = ['kurs', 'verjüngungskurs', 'ausbildung']
        # Spanish indicators
        spanish_words = ['formación', 'curso', 'tarifa', 'rejuvenecimiento']
        
        italian_count = sum(1 for word in italian_words if word in text_lower)
        french_count = sum(1 for word in french_words if word in text_lower)
        german_count = sum(1 for word in german_words if word in text_lower)
        spanish_count = sum(1 for word in spanish_words if word in text_lower)
        
        if german_count > 0:
            return "de"
        elif french_count > 0:
            return "fr"
        elif spanish_count > 0:
            return "es"
        elif italian_count > 0:
            return "it"
        else:
            return "it"  # Default to Italian

    def _categorize_product(self, product_name: str) -> str:
        """Categorize product based on name"""
        name_lower = product_name.lower()
        
        if any(word in name_lower for word in ['corso', 'formation', 'formación', 'kurs']):
            return "corso"
        elif any(word in name_lower for word in ['formazione', 'training', 'ausbildung']):
            return "formazione"  
        elif any(word in name_lower for word in ['consulenza', 'consultation', 'beratung']):
            return "consulenza"
        else:
            return "generale"

    async def _create_course_from_product_if_needed(self, product_doc: dict, product_id: str):
        """Create course automatically if product contains course keywords"""
        product_name = product_doc["name"].lower()
        
        # Check if course creation is needed
        if not any(keyword in product_name for keyword in ['corso', 'formazione', 'formation', 'kurs', 'formación']):
            return
        
        # Check if this course was manually deleted (prevent auto-recreation)
        manually_deleted = deleted_courses_collection.find_one({
            "$or": [
                {"associated_product_id": product_id},
                {"course_title": {"$regex": product_doc["name"], "$options": "i"}}
            ]
        })
        
        if manually_deleted:
            logger.info(f"Skipping course recreation - was manually deleted: {product_doc['name']}")
            return
        
        # Check if course already exists
        existing_course = courses_collection.find_one({
            "title": {"$regex": product_doc["name"], "$options": "i"}
        })
        
        if existing_course:
            logger.info(f"Course already exists for product: {product_doc['name']}")
            return
        
        # Create course
        course_doc = {
            "title": product_doc["name"],
            "description": f"Corso creato automaticamente dal prodotto: {product_doc['name']}",
            "category": product_doc.get("category", "corso"),
            "language": product_doc.get("language", "it"),
            "price": product_doc.get("price", 0),
            "duration": self._estimate_course_duration(product_doc["name"]),
            "instructor": "Grigori Grabovoi",
            "source": "woocommerce_auto",
            "associated_product_id": product_id,
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        }
        
        result = courses_collection.insert_one(course_doc)
        logger.info(f"Created new course from product: {product_doc['name']}")
        return str(result.inserted_id)

    def _estimate_course_duration(self, course_name: str) -> str:
        """Estimate course duration from name"""
        name_lower = course_name.lower()
        
        # Look for duration indicators
        if any(word in name_lower for word in ['base', 'basic', 'primo']):
            return "4 settimane"
        elif any(word in name_lower for word in ['avanzato', 'advanced', 'secondo']):
            return "8 settimane"
        elif any(word in name_lower for word in ['completo', 'complete', 'full']):
            return "12 settimane"
        elif any(word in name_lower for word in ['intensivo', 'intensive']):
            return "6 settimane"
        else:
            return "8 settimane"  # Default duration

# Initialize WooCommerce sync service
wc_sync_service = WooCommerceSyncService() if woocommerce_client else None

# ===== WOOCOMMERCE SETTINGS MANAGEMENT =====

def get_woocommerce_sync_settings() -> dict:
    """Get current WooCommerce sync settings"""
    settings_doc = wc_sync_settings_collection.find_one({})
    if not settings_doc:
        # Return default settings
        default_settings = {
            "auto_sync_enabled": True,
            "sync_customers_enabled": True,
            "sync_products_enabled": True,
            "sync_orders_enabled": True,
            "sync_interval_orders": 15,
            "sync_interval_customers": 30,
            "sync_interval_products": 60,
            "full_sync_hour": 2,
            "last_updated": datetime.utcnow(),
            "updated_by": None
        }
        # Save default settings
        wc_sync_settings_collection.insert_one(default_settings)
        return default_settings
    
    # Convert ObjectId to string for API response
    settings_doc["_id"] = str(settings_doc["_id"])
    return settings_doc

def update_woocommerce_sync_settings(settings_update: dict, user_id: str) -> dict:
    """Update WooCommerce sync settings and restart scheduler if needed"""
    current_settings = get_woocommerce_sync_settings()
    
    # Update settings
    updated_settings = {**current_settings, **settings_update}
    updated_settings["last_updated"] = datetime.utcnow()
    updated_settings["updated_by"] = user_id
    
    # Save to database
    if "_id" in current_settings:
        # Remove _id from update data to avoid MongoDB error
        update_data = {k: v for k, v in updated_settings.items() if k != "_id"}
        wc_sync_settings_collection.update_one(
            {"_id": ObjectId(current_settings["_id"])},
            {"$set": update_data}
        )
    else:
        result = wc_sync_settings_collection.insert_one(updated_settings)
        updated_settings["_id"] = str(result.inserted_id)
    
    # Restart scheduler with new settings
    restart_woocommerce_scheduler(updated_settings)
    
    return updated_settings

def restart_woocommerce_scheduler(settings: dict):
    """Restart WooCommerce scheduler with new settings"""
    try:
        # Remove existing jobs
        if scheduler.running:
            job_ids = ['wc_order_sync', 'wc_customer_sync', 'wc_product_sync', 'wc_full_sync']
            for job_id in job_ids:
                try:
                    scheduler.remove_job(job_id)
                except:
                    pass
        
        # Add jobs only if auto sync is enabled
        if settings.get("auto_sync_enabled", True):
            # Schedule order sync (if enabled)
            if settings.get("sync_orders_enabled", True):
                scheduler.add_job(
                    func=scheduled_wc_order_sync,
                    trigger=IntervalTrigger(minutes=settings.get("sync_interval_orders", 15)),
                    id="wc_order_sync",
                    name="WooCommerce Order Sync",
                    misfire_grace_time=300,
                    coalesce=True,
                    max_instances=1,
                    replace_existing=True
                )
                logger.info(f"Order sync scheduled: every {settings.get('sync_interval_orders', 15)} minutes")
            
            # Schedule customer sync (if enabled)
            if settings.get("sync_customers_enabled", True):
                scheduler.add_job(
                    func=scheduled_wc_customer_sync,
                    trigger=IntervalTrigger(minutes=settings.get("sync_interval_customers", 30)),
                    id="wc_customer_sync", 
                    name="WooCommerce Customer Sync",
                    misfire_grace_time=300,
                    coalesce=True,
                    max_instances=1,
                    replace_existing=True
                )
                logger.info(f"Customer sync scheduled: every {settings.get('sync_interval_customers', 30)} minutes")
            
            # Schedule product sync (if enabled)
            if settings.get("sync_products_enabled", True):
                scheduler.add_job(
                    func=scheduled_wc_product_sync,
                    trigger=IntervalTrigger(minutes=settings.get("sync_interval_products", 60)),
                    id="wc_product_sync",
                    name="WooCommerce Product Sync",
                    misfire_grace_time=600,
                    coalesce=True,
                    max_instances=1,
                    replace_existing=True
                )
                logger.info(f"Product sync scheduled: every {settings.get('sync_interval_products', 60)} minutes")
            
            # Schedule full sync daily (if any sync is enabled)
            if any([
                settings.get("sync_customers_enabled", True),
                settings.get("sync_products_enabled", True),
                settings.get("sync_orders_enabled", True)
            ]):
                from apscheduler.triggers.cron import CronTrigger
                scheduler.add_job(
                    func=scheduled_wc_full_sync,
                    trigger=CronTrigger(hour=settings.get("full_sync_hour", 2), minute=0),
                    id="wc_full_sync",
                    name="WooCommerce Full Daily Sync",
                    misfire_grace_time=3600,
                    coalesce=True,
                    max_instances=1,
                    replace_existing=True
                )
                logger.info(f"Full sync scheduled: daily at {settings.get('full_sync_hour', 2)}:00")
            
            logger.info("WooCommerce automatic synchronization restarted with new settings")
        else:
            logger.info("WooCommerce automatic synchronization disabled")
            
    except Exception as e:
        logger.error(f"Error restarting WooCommerce scheduler: {e}")

def is_woocommerce_auto_sync_enabled() -> bool:
    """Check if WooCommerce auto sync is enabled"""
    settings = get_woocommerce_sync_settings()
    return settings.get("auto_sync_enabled", True)

# ===== EMAIL SETTINGS ENDPOINTS =====

@app.get("/api/email-settings")
async def get_user_email_settings(current_user: dict = Depends(get_current_user)):
    """Get current user's email settings"""
    settings = await get_email_settings(str(current_user["_id"]))
    return settings

@app.put("/api/email-settings")
async def update_email_settings(
    settings_data: EmailSettingsUpdate, 
    current_user: dict = Depends(get_current_user)
):
    """Update user's email settings"""
    user_id = str(current_user["_id"])
    
    # Get current settings or create new
    current_settings_doc = email_settings_collection.find_one({"user_id": user_id})
    
    if current_settings_doc:
        # Update existing settings
        update_data = settings_data.dict(exclude_unset=True)
        update_data["updated_at"] = datetime.utcnow()
        
        email_settings_collection.update_one(
            {"user_id": user_id},
            {"$set": update_data}
        )
    else:
        # Create new settings
        settings_doc = settings_data.dict(exclude_unset=True)
        settings_doc.update({
            "user_id": user_id,
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        })
        
        # Fill in defaults for missing values from environment
        env_defaults = {
            "smtp_server": os.getenv("SMTP_SERVER", "smtp240.ext.armada.it"),
            "smtp_port": int(os.getenv("SMTP_PORT", "587")),
            "username": os.getenv("SMTP_USERNAME", "SMTP-PRO-15223"),
            "password": os.getenv("SMTP_PASSWORD", "EiM5Tn5FKdTe"),
            "from_email": os.getenv("SMTP_FROM_EMAIL", "grabovoi@wp-mail.org"),
            "from_name": os.getenv("SMTP_FROM_NAME", "Grabovoi Foundation"),
            "use_tls": os.getenv("SMTP_USE_TLS", "true").lower() == "true"
        }
        
        for key, default_value in env_defaults.items():
            if key not in settings_doc:
                settings_doc[key] = default_value
        
        email_settings_collection.insert_one(settings_doc)
    
    # Return updated settings
    return await get_user_email_settings(current_user)

# ===== USER MANAGEMENT ENDPOINTS (ADMIN) =====

@app.get("/api/admin/users")
async def get_all_users(current_user: dict = Depends(get_current_user)):
    """Get all users (admin only)"""
    if current_user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    
    users = list(users_collection.find({}))
    
    # Remove passwords from response
    for user in users:
        user.pop("password", None)
    
    return convert_objectid_to_str(users)

@app.post("/api/admin/users")
async def create_user_admin(user_data: UserCreate, current_user: dict = Depends(get_current_user)):
    """Create a user with specific role (admin only)"""
    if current_user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    
    try:
        # Check if user already exists
        existing_user = users_collection.find_one({"email": user_data.email})
        if existing_user:
            raise HTTPException(status_code=400, detail="Email already registered")
        
        existing_username = users_collection.find_one({"username": user_data.username})
        if existing_username:
            raise HTTPException(status_code=400, detail="Username already taken")
        
        # Hash password
        hashed_password = hash_password(user_data.password)
        
        # Create user (admin created users are verified by default)
        user_doc = {
            "username": user_data.username,
            "email": user_data.email,
            "password": hashed_password,
            "name": user_data.name,
            "role": user_data.role,
            "is_verified": True,  # Admin created users are pre-verified
            "created_at": datetime.utcnow(),
            "created_by": str(current_user["_id"]),
            "last_login": None
        }
        
        result = users_collection.insert_one(user_doc)
        user_id = str(result.inserted_id)
        
        # Get created user without password
        created_user = users_collection.find_one({"_id": result.inserted_id})
        created_user.pop("password", None)
        
        return {
            "message": "User created successfully",
            "user": convert_objectid_to_str(created_user)
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Admin user creation error: {str(e)}")
        raise HTTPException(status_code=500, detail="User creation failed")

@app.put("/api/admin/users/{user_id}")
async def update_user_admin(user_id: str, user_data: UserUpdate, current_user: dict = Depends(get_current_user)):
    """Update user (admin only)"""
    if current_user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    
    try:
        # Check if user exists
        existing_user = users_collection.find_one({"_id": ObjectId(user_id)})
        if not existing_user:
            raise HTTPException(status_code=404, detail="User not found")
        
        # Prepare update data
        update_data = user_data.dict(exclude_unset=True)
        if update_data:
            update_data["updated_at"] = datetime.utcnow()
            update_data["updated_by"] = str(current_user["_id"])
            
            # Check for email/username conflicts if updating
            if "email" in update_data and update_data["email"] != existing_user["email"]:
                email_conflict = users_collection.find_one({
                    "email": update_data["email"],
                    "_id": {"$ne": ObjectId(user_id)}
                })
                if email_conflict:
                    raise HTTPException(status_code=400, detail="Email already in use")
            
            if "username" in update_data and update_data["username"] != existing_user["username"]:
                username_conflict = users_collection.find_one({
                    "username": update_data["username"],
                    "_id": {"$ne": ObjectId(user_id)}
                })
                if username_conflict:
                    raise HTTPException(status_code=400, detail="Username already in use")
            
            # Update user
            users_collection.update_one(
                {"_id": ObjectId(user_id)},
                {"$set": update_data}
            )
        
        # Get updated user
        updated_user = users_collection.find_one({"_id": ObjectId(user_id)})
        updated_user.pop("password", None)
        
        return {
            "message": "User updated successfully",
            "user": convert_objectid_to_str(updated_user)
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Admin user update error: {str(e)}")
        raise HTTPException(status_code=500, detail="User update failed")

@app.delete("/api/admin/users/{user_id}")
async def delete_user_admin(user_id: str, current_user: dict = Depends(get_current_user)):
    """Delete user (admin only)"""
    if current_user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    
    try:
        # Don't allow deleting yourself
        if user_id == str(current_user["_id"]):
            raise HTTPException(status_code=400, detail="Cannot delete your own account")
        
        # Check if user exists
        user = users_collection.find_one({"_id": ObjectId(user_id)})
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        # Delete user
        users_collection.delete_one({"_id": ObjectId(user_id)})
        
        # Clean up verification tokens
        verification_tokens_collection.delete_many({"user_id": user_id})
        
        return {"message": "User deleted successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Admin user deletion error: {str(e)}")
        raise HTTPException(status_code=500, detail="User deletion failed")

@app.get("/api/admin/users/stats")
async def get_user_stats(current_user: dict = Depends(get_current_user)):
    """Get user statistics (admin only)"""
    if current_user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    
    try:
        total_users = users_collection.count_documents({})
        verified_users = users_collection.count_documents({"is_verified": True})
        unverified_users = users_collection.count_documents({"is_verified": False})
        
        # Users by role
        admins = users_collection.count_documents({"role": "admin"})
        managers = users_collection.count_documents({"role": "manager"})
        regular_users = users_collection.count_documents({"role": "user"})
        
        # Recent registrations (last 30 days)
        thirty_days_ago = datetime.utcnow() - timedelta(days=30)
        recent_registrations = users_collection.count_documents({
            "created_at": {"$gte": thirty_days_ago}
        })
        
        return {
            "total_users": total_users,
            "verified_users": verified_users,
            "unverified_users": unverified_users,
            "users_by_role": {
                "admin": admins,
                "manager": managers,
                "user": regular_users
            },
            "recent_registrations": recent_registrations
        }
        
    except Exception as e:
        logger.error(f"User stats error: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to get user statistics")

# ===== MESSAGES ENDPOINTS =====

@app.post("/api/messages/send-email")
async def send_email_message(
    message_data: MessageCreate,
    current_user: dict = Depends(get_current_user)
):
    """Send email message to client"""
    try:
        user_id = str(current_user["_id"])
        
        # Get email settings
        email_settings = await get_email_settings(user_id)
        
        # Save message as pending
        message_id = await save_message(message_data, user_id, "pending")
        
        # Send email
        success = await send_email_smtp(
            message_data.recipient_email,
            message_data.subject,
            message_data.content,
            email_settings
        )
        
        # Update message status
        if success:
            messages_collection.update_one(
                {"_id": ObjectId(message_id)},
                {"$set": {"status": "sent", "sent_at": datetime.utcnow()}}
            )
            status = "sent"
            error_msg = None
        else:
            messages_collection.update_one(
                {"_id": ObjectId(message_id)},
                {"$set": {"status": "failed", "error_message": "SMTP sending failed"}}
            )
            status = "failed"
            error_msg = "SMTP sending failed"
        
        # Get updated message
        message_doc = messages_collection.find_one({"_id": ObjectId(message_id)})
        message_response = convert_objectid_to_str(message_doc)
        
        return {
            "success": success,
            "message_id": message_id,
            "status": status,
            "error": error_msg,
            "message": message_response
        }
        
    except Exception as e:
        logger.error(f"Error sending email: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error sending email: {str(e)}")

@app.get("/api/messages")
async def get_messages(
    current_user: dict = Depends(get_current_user),
    recipient_id: Optional[str] = None,
    limit: int = 50,
    skip: int = 0
):
    """Get messages, optionally filtered by recipient"""
    query = {"created_by": str(current_user["_id"])}
    if recipient_id:
        query["recipient_id"] = recipient_id
    
    messages = list(
        messages_collection
        .find(query)
        .sort("created_at", -1)
        .skip(skip)
        .limit(limit)
    )
    
    return convert_objectid_to_str(messages)

@app.get("/api/messages/client/{client_id}")
async def get_client_messages(
    client_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Get all messages for a specific client"""
    messages = list(
        messages_collection
        .find({
            "recipient_id": client_id,
            "created_by": str(current_user["_id"])
        })
        .sort("created_at", -1)
    )
    
    return convert_objectid_to_str(messages)

# ===== CLIENT DETAIL ENDPOINTS =====

@app.get("/api/clients/{client_id}")
async def get_client_detail(client_id: str, current_user: dict = Depends(get_current_user)):
    """Get detailed client information including messages and orders"""
    # Get client (contact with status 'client')
    client = contacts_collection.find_one({"_id": ObjectId(client_id)})
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")
    
    # Check if it's actually a client
    if client.get("status") != "client":
        raise HTTPException(status_code=400, detail="Contact is not a client")
    
    # Get tags
    contact_tag_docs = list(contact_tags_collection.find({"contact_id": client_id}))
    tag_ids = [doc["tag_id"] for doc in contact_tag_docs]
    
    tags = []
    if tag_ids:
        tag_docs = list(tags_collection.find({"_id": {"$in": [ObjectId(tag_id) for tag_id in tag_ids]}}))
        tags = convert_objectid_to_str(tag_docs)
    
    client["tags"] = tags
    
    # Get client's orders
    orders = list(orders_collection.find({"contact_id": client_id}).sort("created_at", -1))
    
    # Get order items and products for each order
    all_products = []
    for order in orders:
        order_id = str(order["_id"])
        items = list(order_items_collection.find({"order_id": order_id}))
        order["items"] = convert_objectid_to_str(items)
        
        # Collect unique products
        for item in items:
            if item.get("product_id"):
                product = products_collection.find_one({"_id": ObjectId(item["product_id"])})
                if product:
                    product_dict = convert_objectid_to_str(product)
                    # Add purchase info
                    product_dict["purchased_at"] = order["created_at"]
                    product_dict["order_id"] = order_id
                    product_dict["quantity"] = item["quantity"]
                    product_dict["paid_price"] = item["unit_price"]
                    all_products.append(product_dict)
    
    # Remove duplicate products (keep most recent purchase)
    unique_products = {}
    for product in all_products:
        product_id = product["id"]
        if product_id not in unique_products or product["purchased_at"] > unique_products[product_id]["purchased_at"]:
            unique_products[product_id] = product
    
    products_list = list(unique_products.values())
    
    # Get client's course enrollments
    enrollments = list(course_enrollments_collection.find({"contact_id": client_id}).sort("enrolled_at", -1))
    
    # Get course details for enrollments
    courses_list = []
    for enrollment in enrollments:
        course = courses_collection.find_one({"_id": ObjectId(enrollment["course_id"])})
        if course:
            course_dict = convert_objectid_to_str(course)
            # Add enrollment info
            course_dict["enrolled_at"] = enrollment["enrolled_at"]
            course_dict["enrollment_status"] = enrollment["status"]
            course_dict["enrollment_source"] = enrollment["source"]
            course_dict["enrollment_id"] = str(enrollment["_id"])
            courses_list.append(course_dict)
    
    # Get recent messages (last 10)
    messages = list(
        messages_collection
        .find({"recipient_id": client_id})
        .sort("created_at", -1)
        .limit(10)
    )
    
    return {
        "client": convert_objectid_to_str(client),
        "orders": convert_objectid_to_str(orders),
        "products": products_list,
        "courses": courses_list,
        "messages": convert_objectid_to_str(messages),
        "stats": {
            "total_orders": len(orders),
            "total_spent": sum(order.get("total_amount", 0) for order in orders),
            "active_courses": len([c for c in courses_list if c["enrollment_status"] == "active"]),
            "total_products": len(products_list)
        }
    }

# ===== INBOUND EMAIL UTILITY FUNCTIONS =====

import hmac
import hashlib
import requests
from bs4 import BeautifulSoup
from dateutil import parser

def verify_postmark_webhook_signature(request_body: bytes, signature: str) -> bool:
    """Verify Postmark webhook signature"""
    webhook_secret = os.getenv("POSTMARK_WEBHOOK_SECRET", "")
    if not webhook_secret or not signature:
        return False
    
    expected_signature = hmac.new(
        webhook_secret.encode(),
        request_body,
        hashlib.sha256
    ).hexdigest()
    
    return hmac.compare_digest(signature, expected_signature)

def extract_postmark_email_data(payload: dict) -> dict:
    """Extract email data from Postmark webhook payload"""
    try:
        return {
            "message_id": payload.get("MessageID", ""),
            "from_email": payload.get("From", "").lower(),
            "from_name": payload.get("FromName", ""),
            "to_email": payload.get("To", "").lower(),
            "subject": payload.get("Subject", ""),
            "text_body": payload.get("TextBody", ""),
            "html_body": payload.get("HtmlBody", ""),
            "date": payload.get("Date", ""),
            "attachments": payload.get("Attachments", [])
        }
    except Exception as e:
        logger.error(f"Error extracting Postmark data: {str(e)}")
        return {}

def find_client_by_email(email: str) -> Optional[dict]:
    """Find client by email address"""
    if not email:
        return None
    
    # First try exact match
    client = contacts_collection.find_one({"email": email.lower()})
    if client:
        return client
    
    # Try domain matching
    domain = email.split("@")[1] if "@" in email else ""
    if domain:
        # Look for other clients with same domain
        domain_clients = list(contacts_collection.find({
            "email": {"$regex": f"@{domain}$", "$options": "i"}
        }).limit(1))
        if domain_clients:
            return domain_clients[0]
    
    return None

def extract_text_from_html(html_content: str) -> str:
    """Extract plain text from HTML content"""
    if not html_content:
        return ""
    
    try:
        soup = BeautifulSoup(html_content, 'html.parser')
        return soup.get_text(separator=' ', strip=True)
    except Exception:
        return html_content

async def process_inbound_email(email_data: dict) -> Optional[str]:
    """Process inbound email and save to database"""
    try:
        # Check for duplicate emails
        existing_email = inbound_emails_collection.find_one({
            "message_id": email_data["message_id"]
        })
        
        if existing_email:
            logger.info(f"Duplicate email ignored: {email_data['message_id']}")
            return str(existing_email["_id"])
        
        # Parse date
        received_date = datetime.utcnow()
        if email_data.get("date"):
            try:
                received_date = parser.parse(email_data["date"])
            except Exception:
                pass
        
        # Create email document
        email_doc = {
            "message_id": email_data["message_id"],
            "from_email": email_data["from_email"],
            "from_name": email_data["from_name"],
            "to_email": email_data["to_email"],
            "subject": email_data["subject"],
            "text_body": email_data["text_body"],
            "html_body": email_data["html_body"],
            "received_date": received_date,
            "processed": False,
            "client_id": None,
            "created_at": datetime.utcnow()
        }
        
        # Try to find matching client
        client = find_client_by_email(email_data["from_email"])
        if client:
            email_doc["client_id"] = str(client["_id"])
            logger.info(f"Email associated with client: {client.get('first_name', '')} {client.get('last_name', '')}")
        
        # Save email
        result = inbound_emails_collection.insert_one(email_doc)
        email_id = str(result.inserted_id)
        
        # Process attachments if present
        if email_data.get("attachments"):
            await process_email_attachments(email_id, email_data["attachments"])
        
        # Mark as processed
        inbound_emails_collection.update_one(
            {"_id": result.inserted_id},
            {"$set": {"processed": True}}
        )
        
        logger.info(f"Inbound email processed successfully: {email_id}")
        return email_id
        
    except Exception as e:
        logger.error(f"Error processing inbound email: {str(e)}")
        return None

async def process_email_attachments(email_id: str, attachments: list):
    """Process email attachments"""
    try:
        for attachment_data in attachments:
            attachment_doc = {
                "email_id": email_id,
                "filename": attachment_data.get("Name", ""),
                "content_type": attachment_data.get("ContentType", ""),
                "content_length": attachment_data.get("ContentLength", 0),
                "content_data": attachment_data.get("Content", ""),
                "created_at": datetime.utcnow()
            }
            
            # Validate attachment size (limit to 25MB)
            if attachment_doc["content_length"] > 25 * 1024 * 1024:
                logger.warning(f"Attachment too large, skipping: {attachment_doc['filename']}")
                continue
            
            email_attachments_collection.insert_one(attachment_doc)
            
    except Exception as e:
        logger.error(f"Error processing attachments: {str(e)}")

# ===== INBOUND EMAIL ENDPOINTS =====

@app.post("/api/webhooks/postmark/inbound")
async def postmark_inbound_webhook(request: Request):
    """Handle Postmark inbound email webhook"""
    try:
        # Get request body and signature
        body = await request.body()
        signature = request.headers.get("X-Postmark-Signature", "")
        
        # Verify webhook signature
        if not verify_postmark_webhook_signature(body, signature):
            logger.warning("Invalid Postmark webhook signature")
            raise HTTPException(status_code=401, detail="Invalid webhook signature")
        
        # Parse JSON payload
        payload = await request.json()
        
        # Extract email data
        email_data = extract_postmark_email_data(payload)
        if not email_data:
            raise HTTPException(status_code=400, detail="Invalid email data")
        
        # Process email
        email_id = await process_inbound_email(email_data)
        
        if email_id:
            return {
                "status": "success",
                "message": "Email processed successfully",
                "email_id": email_id
            }
        else:
            return {
                "status": "error",
                "message": "Failed to process email"
            }
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Webhook processing error: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")

@app.get("/api/inbound-emails")
async def get_inbound_emails(
    current_user: dict = Depends(get_current_user),
    client_id: Optional[str] = None,
    limit: int = 50,
    skip: int = 0
):
    """Get inbound emails, optionally filtered by client"""
    query = {}
    if client_id:
        query["client_id"] = client_id
    
    emails = list(
        inbound_emails_collection
        .find(query)
        .sort("received_date", -1)
        .skip(skip)
        .limit(limit)
    )
    
    # Get client names and attachments for each email
    for email in emails:
        email_id = str(email["_id"])
        
        # Get client info if associated
        if email.get("client_id"):
            client = contacts_collection.find_one({"_id": ObjectId(email["client_id"])})
            if client:
                email["client_name"] = f"{client.get('first_name', '')} {client.get('last_name', '')}".strip()
        
        # Get attachments
        attachments = list(email_attachments_collection.find({"email_id": email_id}))
        email["attachments"] = convert_objectid_to_str(attachments)
    
    return convert_objectid_to_str(emails)

@app.get("/api/inbound-emails/{email_id}")
async def get_inbound_email(email_id: str, current_user: dict = Depends(get_current_user)):
    """Get single inbound email with details"""
    email = inbound_emails_collection.find_one({"_id": ObjectId(email_id)})
    if not email:
        raise HTTPException(status_code=404, detail="Email not found")
    
    # Get client info if associated
    if email.get("client_id"):
        client = contacts_collection.find_one({"_id": ObjectId(email["client_id"])})
        if client:
            email["client"] = convert_objectid_to_str(client)
    
    # Get attachments
    attachments = list(email_attachments_collection.find({"email_id": email_id}))
    email["attachments"] = convert_objectid_to_str(attachments)
    
    return convert_objectid_to_str(email)

@app.get("/api/clients/{client_id}/inbound-emails")
async def get_client_inbound_emails(
    client_id: str, 
    current_user: dict = Depends(get_current_user)
):
    """Get all inbound emails for a specific client"""
    # Verify client exists
    client = contacts_collection.find_one({"_id": ObjectId(client_id)})
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")
    
    emails = list(
        inbound_emails_collection
        .find({"client_id": client_id})
        .sort("received_date", -1)
    )
    
    # Get attachments for each email
    for email in emails:
        email_id = str(email["_id"])
        attachments = list(email_attachments_collection.find({"email_id": email_id}))
        email["attachments"] = convert_objectid_to_str(attachments)
    
    return convert_objectid_to_str(emails)

# ===== WOOCOMMERCE SYNC ENDPOINTS =====

@app.get("/api/woocommerce/sync/status")
async def get_woocommerce_sync_status(current_user: dict = Depends(get_current_user)):
    """Get WooCommerce synchronization status"""
    try:
        # Get last sync times
        last_customer_sync = wc_customers_collection.find_one(
            sort=[("last_sync", -1)]
        )
        last_product_sync = wc_products_collection.find_one(
            sort=[("last_sync", -1)]
        )
        last_order_sync = wc_orders_collection.find_one(
            sort=[("last_sync", -1)]
        )
        
        # Get counts
        customer_count = wc_customers_collection.count_documents({})
        product_count = wc_products_collection.count_documents({})
        order_count = wc_orders_collection.count_documents({})
        
        # Get recent sync logs
        recent_logs = list(
            wc_sync_logs_collection
            .find({})
            .sort("started_at", -1)
            .limit(10)
        )
        
        return {
            "woocommerce_connection": woocommerce_client is not None,
            "last_customer_sync": last_customer_sync["last_sync"] if last_customer_sync else None,
            "last_product_sync": last_product_sync["last_sync"] if last_product_sync else None, 
            "last_order_sync": last_order_sync["last_sync"] if last_order_sync else None,
            "customer_count": customer_count,
            "product_count": product_count,
            "order_count": order_count,
            "recent_sync_logs": convert_objectid_to_str(recent_logs)
        }
        
    except Exception as e:
        logger.error(f"Error getting WooCommerce sync status: {e}")
        raise HTTPException(status_code=500, detail="Error retrieving sync status")

@app.post("/api/woocommerce/sync/customers")
async def trigger_woocommerce_customer_sync(
    background_tasks: BackgroundTasks,
    full_sync: bool = False,
    current_user: dict = Depends(get_current_user)
):
    """Trigger WooCommerce customer synchronization"""
    if not wc_sync_service:
        raise HTTPException(status_code=503, detail="WooCommerce sync service not available")
    
    try:
        async def sync_task():
            await wc_sync_service.sync_customers_from_woocommerce(incremental=not full_sync)
        
        background_tasks.add_task(sync_task)
        
        return {
            "message": "WooCommerce customer sync initiated",
            "full_sync": full_sync,
            "initiated_by": current_user.get("email")
        }
        
    except Exception as e:
        logger.error(f"Error triggering customer sync: {e}")
        raise HTTPException(status_code=500, detail="Error initiating customer sync")

@app.post("/api/woocommerce/sync/products")
async def trigger_woocommerce_product_sync(
    background_tasks: BackgroundTasks,
    full_sync: bool = False,
    current_user: dict = Depends(get_current_user)
):
    """Trigger WooCommerce product synchronization"""
    if not wc_sync_service:
        raise HTTPException(status_code=503, detail="WooCommerce sync service not available")
    
    try:
        async def sync_task():
            await wc_sync_service.sync_products_from_woocommerce(incremental=not full_sync)
        
        background_tasks.add_task(sync_task)
        
        return {
            "message": "WooCommerce product sync initiated",
            "full_sync": full_sync,
            "initiated_by": current_user.get("email")
        }
        
    except Exception as e:
        logger.error(f"Error triggering product sync: {e}")
        raise HTTPException(status_code=500, detail="Error initiating product sync")

@app.post("/api/woocommerce/sync/orders")
async def trigger_woocommerce_order_sync(
    background_tasks: BackgroundTasks,
    full_sync: bool = False,
    current_user: dict = Depends(get_current_user)
):
    """Trigger WooCommerce order synchronization"""
    if not wc_sync_service:
        raise HTTPException(status_code=503, detail="WooCommerce sync service not available")
    
    try:
        async def sync_task():
            await wc_sync_service.sync_orders_from_woocommerce(incremental=not full_sync)
        
        background_tasks.add_task(sync_task)
        
        return {
            "message": "WooCommerce order sync initiated", 
            "full_sync": full_sync,
            "initiated_by": current_user.get("email")
        }
        
    except Exception as e:
        logger.error(f"Error triggering order sync: {e}")
        raise HTTPException(status_code=500, detail="Error initiating order sync")

@app.post("/api/woocommerce/sync/all")
async def trigger_woocommerce_full_sync(
    background_tasks: BackgroundTasks,
    current_user: dict = Depends(get_current_user)
):
    """Trigger complete WooCommerce synchronization"""
    if not wc_sync_service:
        raise HTTPException(status_code=503, detail="WooCommerce sync service not available")
    
    try:
        async def full_sync_task():
            # Sync in order: customers first, then products, then orders
            await wc_sync_service.sync_customers_from_woocommerce(incremental=False)
            await wc_sync_service.sync_products_from_woocommerce(incremental=False)
            await wc_sync_service.sync_orders_from_woocommerce(incremental=False)
        
        background_tasks.add_task(full_sync_task)
        
        return {
            "message": "Full WooCommerce synchronization initiated",
            "initiated_by": current_user.get("email")
        }
        
    except Exception as e:
        logger.error(f"Error triggering full sync: {e}")
        raise HTTPException(status_code=500, detail="Error initiating full sync")

@app.get("/api/woocommerce/test-connection")
async def test_woocommerce_connection(current_user: dict = Depends(get_current_user)):
    """Test WooCommerce API connection"""
    if not woocommerce_client:
        raise HTTPException(status_code=503, detail="WooCommerce client not initialized")
    
    try:
        # Test connection with a simple API call
        response = woocommerce_client.get("")
        
        if response.status_code == 200:
            api_info = response.json()
            return {
                "connection": "successful",
                "store_info": {
                    "name": api_info.get("store", {}).get("name", ""),
                    "description": api_info.get("store", {}).get("description", ""),
                    "url": api_info.get("store", {}).get("URL", ""),
                    "wc_version": api_info.get("store", {}).get("wc_version", "")
                }
            }
        else:
            return {
                "connection": "failed",
                "status_code": response.status_code,
                "error": "API returned non-200 status"
            }
            
    except Exception as e:
        logger.error(f"WooCommerce connection test failed: {e}")
        return {
            "connection": "failed",
            "error": str(e)
        }

@app.get("/api/woocommerce/sync/settings")
async def get_woocommerce_sync_settings_endpoint(current_user: dict = Depends(get_current_user)):
    """Get WooCommerce sync settings"""
    if current_user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    
    try:
        settings = get_woocommerce_sync_settings()
        return settings
    except Exception as e:
        logger.error(f"Error getting WooCommerce sync settings: {e}")
        raise HTTPException(status_code=500, detail="Error retrieving sync settings")

@app.put("/api/woocommerce/sync/settings")
async def update_woocommerce_sync_settings_endpoint(
    settings_update: WooCommerceSyncSettingsUpdate,
    current_user: dict = Depends(get_current_user)
):
    """Update WooCommerce sync settings"""
    if current_user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    
    try:
        user_id = str(current_user["_id"])
        updated_settings = update_woocommerce_sync_settings(
            settings_update.dict(exclude_unset=True), 
            user_id
        )
        
        return {
            "message": "Settings updated successfully",
            "settings": updated_settings
        }
        
    except Exception as e:
        logger.error(f"Error updating WooCommerce sync settings: {e}")
        raise HTTPException(status_code=500, detail="Error updating sync settings")

# ===== WOOCOMMERCE AUTOMATIC SCHEDULING =====

# Initialize scheduler for automatic synchronization
scheduler = AsyncIOScheduler()

async def scheduled_wc_customer_sync():
    """Scheduled job for customer synchronization"""
    if wc_sync_service:
        try:
            logger.info("Starting scheduled WooCommerce customer sync")
            result = await wc_sync_service.sync_customers_from_woocommerce(incremental=True)
            logger.info(f"Scheduled customer sync completed: {result}")
        except Exception as e:
            import traceback
            logger.error(f"Scheduled customer sync failed - {type(e).__name__}: {str(e) or 'No error message'}")
            logger.error(f"Full traceback: {traceback.format_exc()}")

async def scheduled_wc_product_sync():
    """Scheduled job for product synchronization"""
    if wc_sync_service:
        try:
            logger.info("Starting scheduled WooCommerce product sync")
            result = await wc_sync_service.sync_products_from_woocommerce(incremental=True)
            logger.info(f"Scheduled product sync completed: {result}")
        except Exception as e:
            import traceback
            logger.error(f"Scheduled product sync failed - {type(e).__name__}: {str(e) or 'No error message'}")
            logger.error(f"Full traceback: {traceback.format_exc()}")

async def scheduled_wc_order_sync():
    """Scheduled job for order synchronization"""
    if wc_sync_service:
        try:
            logger.info("Starting scheduled WooCommerce order sync") 
            result = await wc_sync_service.sync_orders_from_woocommerce(incremental=True)
            logger.info(f"Scheduled order sync completed: {result}")
        except Exception as e:
            import traceback
            logger.error(f"Scheduled order sync failed - {type(e).__name__}: {str(e) or 'No error message'}")
            logger.error(f"Full traceback: {traceback.format_exc()}")

async def scheduled_wc_full_sync():
    """Scheduled job for full synchronization (daily)"""
    if wc_sync_service:
        try:
            logger.info("Starting scheduled full WooCommerce sync")
            await wc_sync_service.sync_customers_from_woocommerce(incremental=False)
            await wc_sync_service.sync_products_from_woocommerce(incremental=False)  
            await wc_sync_service.sync_orders_from_woocommerce(incremental=False)
            logger.info("Scheduled full sync completed")
        except Exception as e:
            logger.error(f"Scheduled full sync failed: {e}")

@app.on_event("startup")
async def startup_event():
    """Start scheduled WooCommerce synchronization when FastAPI starts"""
    if woocommerce_client and wc_sync_service:
        try:
            # Get sync settings
            settings = get_woocommerce_sync_settings()
            
            # Only start automatic sync if enabled
            if settings.get("auto_sync_enabled", True):
                # Schedule order sync (if enabled)
                if settings.get("sync_orders_enabled", True):
                    scheduler.add_job(
                        func=scheduled_wc_order_sync,
                        trigger=IntervalTrigger(minutes=settings.get("sync_interval_orders", 15)),
                        id="wc_order_sync",
                        name="WooCommerce Order Sync",
                        misfire_grace_time=300,
                        coalesce=True,
                        max_instances=1
                    )
                
                # Schedule customer sync (if enabled)
                if settings.get("sync_customers_enabled", True):
                    scheduler.add_job(
                        func=scheduled_wc_customer_sync,
                        trigger=IntervalTrigger(minutes=settings.get("sync_interval_customers", 30)),
                        id="wc_customer_sync",
                        name="WooCommerce Customer Sync",
                        misfire_grace_time=300,
                        coalesce=True,
                        max_instances=1
                    )
                
                # Schedule product sync (if enabled)
                if settings.get("sync_products_enabled", True):
                    scheduler.add_job(
                        func=scheduled_wc_product_sync,
                        trigger=IntervalTrigger(minutes=settings.get("sync_interval_products", 60)),
                        id="wc_product_sync",
                        name="WooCommerce Product Sync",
                        misfire_grace_time=600,
                        coalesce=True,
                        max_instances=1
                    )
                
                # Schedule full sync daily (if any sync is enabled)
                if any([
                    settings.get("sync_customers_enabled", True),
                    settings.get("sync_products_enabled", True),
                    settings.get("sync_orders_enabled", True)
                ]):
                    from apscheduler.triggers.cron import CronTrigger
                    scheduler.add_job(
                        func=scheduled_wc_full_sync,
                        trigger=CronTrigger(hour=settings.get("full_sync_hour", 2), minute=0),
                        id="wc_full_sync",
                        name="WooCommerce Full Daily Sync",
                        misfire_grace_time=3600,
                        coalesce=True,
                        max_instances=1
                    )
                
                scheduler.start()
                logger.info("WooCommerce automatic synchronization started:")
                logger.info(f"- Orders: ogni {settings.get('sync_interval_orders', 15)} minuti ({'ENABLED' if settings.get('sync_orders_enabled', True) else 'DISABLED'})")
                logger.info(f"- Customers: ogni {settings.get('sync_interval_customers', 30)} minuti ({'ENABLED' if settings.get('sync_customers_enabled', True) else 'DISABLED'})")
                logger.info(f"- Products: ogni {settings.get('sync_interval_products', 60)} minuti ({'ENABLED' if settings.get('sync_products_enabled', True) else 'DISABLED'})")
                logger.info(f"- Full sync: daily at {settings.get('full_sync_hour', 2)}:00")
            else:
                scheduler.start()  # Start scheduler but no jobs
                logger.info("WooCommerce automatic synchronization DISABLED - manual mode active")
                
        except Exception as e:
            logger.error(f"Error starting WooCommerce scheduler: {e}")
    else:
        logger.warning("WooCommerce client not available - scheduling disabled")

@app.on_event("shutdown")
async def shutdown_event():
    """Stop scheduled synchronization when FastAPI shuts down"""
    try:
        scheduler.shutdown(wait=True)
        logger.info("WooCommerce scheduler stopped")
    except Exception as e:
        logger.error(f"Error stopping scheduler: {e}")

# Health check
@app.get("/api/health")
async def health_check():
    return {"status": "healthy", "timestamp": datetime.utcnow()}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)