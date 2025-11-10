"""Database connection and schema management."""
import os
from contextlib import contextmanager
import psycopg
from psycopg.rows import dict_row


def get_database_url() -> str:
    """Get database URL from environment."""
    dsn = os.environ.get("DATABASE_URL")
    if not dsn:
        raise ValueError("DATABASE_URL environment variable not set")
    return dsn


@contextmanager
def get_db_connection():
    """Get a database connection context manager."""
    dsn = get_database_url()
    conn = psycopg.connect(dsn, row_factory=dict_row)
    try:
        yield conn
    finally:
        conn.close()


def init_database():
    """Initialize database schema for auth service."""
    dsn = get_database_url()
    
    with psycopg.connect(dsn, autocommit=True) as conn:
        with conn.cursor() as cur:
            # Create auth schema if not exists
            cur.execute("CREATE SCHEMA IF NOT EXISTS auth")
            
            # Create users table
            cur.execute("""
                CREATE TABLE IF NOT EXISTS auth.users (
                    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                    email VARCHAR(255) UNIQUE NOT NULL,
                    phone VARCHAR(50),
                    otp_preference VARCHAR(10) CHECK (otp_preference IN ('sms', 'email')),
                    created_at TIMESTAMPTZ DEFAULT NOW(),
                    last_login_at TIMESTAMPTZ,
                    CONSTRAINT email_lowercase CHECK (email = LOWER(email))
                )
            """)
            
            # Create indexes
            cur.execute("""
                CREATE INDEX IF NOT EXISTS idx_users_email 
                ON auth.users(email)
            """)
            
            cur.execute("""
                CREATE INDEX IF NOT EXISTS idx_users_created_at 
                ON auth.users(created_at DESC)
            """)
            
            # Create OTP storage table
            cur.execute("""
                CREATE TABLE IF NOT EXISTS auth.otp_storage (
                    email VARCHAR(255) PRIMARY KEY,
                    otp_hash VARCHAR(255) NOT NULL,
                    attempts INTEGER DEFAULT 0,
                    expires_at TIMESTAMPTZ NOT NULL,
                    created_at TIMESTAMPTZ DEFAULT NOW()
                )
            """)
            
            # Create rate limit table
            cur.execute("""
                CREATE TABLE IF NOT EXISTS auth.rate_limit (
                    email VARCHAR(255) PRIMARY KEY,
                    request_count INTEGER DEFAULT 0,
                    window_start TIMESTAMPTZ NOT NULL
                )
            """)
            
            print("Auth database schema initialized successfully")
