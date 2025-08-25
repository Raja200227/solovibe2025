#!/usr/bin/env python3
"""
Admin User Creation Script
This script creates admin users directly in the database.
Useful for initial setup or when you need to create admin users programmatically.
"""

import sys
import os
from pymongo import MongoClient
import bcrypt
from datetime import datetime

def create_admin_user(email, password, mongodb_uri="mongodb://localhost:27017/ecommerce"):
    """Create an admin user in the database"""
    try:
        # Connect to MongoDB
        client = MongoClient(mongodb_uri)
        db = client.ecommerce
        
        # Check if user already exists
        existing_user = db.users.find_one({'email': email})
        if existing_user:
            print(f"❌ User with email {email} already exists!")
            if existing_user.get('role') == 'admin':
                print(f"   This user is already an admin.")
            else:
                print(f"   This user has role: {existing_user.get('role')}")
            return False
        
        # Hash password
        password_hash = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())
        
        # Create admin user
        user_data = {
            'email': email,
            'password_hash': password_hash,
            'role': 'admin',
            'created_at': datetime.utcnow()
        }
        
        result = db.users.insert_one(user_data)
        
        if result.inserted_id:
            print(f"✅ Admin user created successfully!")
            print(f"   Email: {email}")
            print(f"   Role: admin")
            print(f"   User ID: {result.inserted_id}")
            return True
        else:
            print("❌ Failed to create admin user")
            return False
            
    except Exception as e:
        print(f"❌ Error creating admin user: {e}")
        return False
    finally:
        client.close()

def main():
    print("🔐 Admin User Creation Script")
    print("=" * 40)
    
    # Get email and password from command line arguments
    if len(sys.argv) == 3:
        email = sys.argv[1]
        password = sys.argv[2]
    else:
        # Interactive mode
        print("Enter admin user details:")
        email = input("Email: ").strip()
        password = input("Password: ").strip()
        confirm_password = input("Confirm Password: ").strip()
        
        if password != confirm_password:
            print("❌ Passwords do not match!")
            return
        
        if not email or not password:
            print("❌ Email and password are required!")
            return
    
    # Validate email format
    if '@' not in email or '.' not in email:
        print("❌ Invalid email format!")
        return
    
    # Validate password length
    if len(password) < 6:
        print("❌ Password must be at least 6 characters long!")
        return
    
    # Check MongoDB connection
    try:
        client = MongoClient("mongodb://localhost:27017/ecommerce")
        client.admin.command('ping')
        client.close()
        print("✅ MongoDB connection successful")
    except Exception as e:
        print(f"❌ MongoDB connection failed: {e}")
        print("Make sure MongoDB is running and accessible")
        return
    
    # Create admin user
    success = create_admin_user(email, password)
    
    if success:
        print("\n🎉 Admin user creation completed!")
        print(f"You can now login with email: {email}")
    else:
        print("\n💥 Admin user creation failed!")
        sys.exit(1)

if __name__ == "__main__":
    main()
