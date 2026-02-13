"""Database initialization and management utilities"""

import os
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from loguru import logger

# Force new settings instance
if "config.settings" in sys.modules:
    del sys.modules["config.settings"]

from config.settings import Settings
from src.database import init_db, drop_db, engine, Base

# Create fresh settings without caching
settings = Settings()


def setup_database():
    """Initialize the database with all tables"""
    logger.info(f"Setting up database at: {settings.database_url}")
    
    try:
        # Create all tables
        init_db()
        logger.success("✓ Database setup completed successfully")
        return True
    except Exception as e:
        logger.error(f"✗ Database setup failed: {str(e)}")
        return False


def reset_database():
    """Reset the database - DROP and CREATE all tables"""
    logger.warning("⚠️  WARNING: This will DELETE all data from the database!")
    confirm = input("Type 'yes' to confirm database reset: ")
    
    if confirm.lower() == "yes":
        try:
            drop_db()
            init_db()
            logger.success("✓ Database reset completed successfully")
            return True
        except Exception as e:
            logger.error(f"✗ Database reset failed: {str(e)}")
            return False
    else:
        logger.info("Database reset cancelled")
        return False


def create_admin_user():
    """Create a default admin user for testing"""
    from src.models import User, UserRole
    from src.database import SessionLocal
    from passlib.context import CryptContext

    pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
    db = SessionLocal()

    try:
        # Check if admin already exists
        existing_admin = db.query(User).filter(User.username == "admin").first()
        if existing_admin:
            logger.info("Admin user already exists")
            return existing_admin

        # Create admin user
        admin_user = User(
            username="admin",
            email="admin@financialanalytics.local",
            hashed_password=pwd_context.hash("admin123"),
            full_name="System Administrator",
            role=UserRole.ADMIN,
            is_active=True,
        )
        db.add(admin_user)
        db.commit()
        logger.success(f"✓ Admin user created successfully")
        logger.info("  Username: admin")
        logger.info("  Password: admin123")
        logger.info("  Email: admin@financialanalytics.local")
        return admin_user

    except Exception as e:
        db.rollback()
        logger.error(f"✗ Failed to create admin user: {str(e)}")
        return None
    finally:
        db.close()


def check_database_connection():
    """Check if database connection is working"""
    try:
        with engine.connect() as connection:
            result = connection.execute("SELECT 1")
            logger.success("✓ Database connection successful")
            return True
    except Exception as e:
        logger.error(f"✗ Database connection failed: {str(e)}")
        return False


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Database management utilities")
    parser.add_argument(
        "command",
        choices=["setup", "reset", "check", "create-admin"],
        help="Command to execute",
    )

    args = parser.parse_args()

    if args.command == "setup":
        setup_database()
    elif args.command == "reset":
        reset_database()
    elif args.command == "check":
        check_database_connection()
    elif args.command == "create-admin":
        create_admin_user()
