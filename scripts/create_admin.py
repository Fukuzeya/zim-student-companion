# ============================================================================
# Create Admin User
# ============================================================================
"""
Script to create an admin user.

Usage:
    python scripts/create_admin.py --phone +263771234567 --email admin@zimstudent.com --password SecurePass123
"""

import asyncio
import argparse
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.database import async_session_maker
from app.core.security import get_password_hash
from app.models.user import User, UserRole, SubscriptionTier

async def create_admin(phone: str, email: str, password: str):
    """Create an admin user"""
    async with async_session_maker() as db:
        from sqlalchemy import select
        
        # Check if user exists
        result = await db.execute(
            select(User).where(User.phone_number == phone)
        )
        existing = result.scalar_one_or_none()
        
        if existing:
            print(f"User with phone {phone} already exists")
            existing.role = UserRole.ADMIN
            existing.email = email
            existing.password_hash = get_password_hash(password)
            await db.commit()
            print(f"Updated existing user to admin")
        else:
            user = User(
                phone_number=phone,
                email=email,
                password_hash=get_password_hash(password),
                role=UserRole.ADMIN,
                subscription_tier=SubscriptionTier.SCHOOL,
                is_active=True,
                is_verified=True
            )
            db.add(user)
            await db.commit()
            print(f"Created admin user: {email}")

def main():
    parser = argparse.ArgumentParser(description="Create admin user")
    parser.add_argument("--phone", required=True, help="Phone number")
    parser.add_argument("--email", required=True, help="Email address")
    parser.add_argument("--password", required=True, help="Password")
    
    args = parser.parse_args()
    asyncio.run(create_admin(args.phone, args.email, args.password))

if __name__ == "__main__":
    main()