"""
Database connection utilities for API service
"""
import os
import psycopg
from typing import Optional


def get_database_url() -> str:
    """Get database URL from environment."""
    dsn = os.environ.get("DATABASE_URL")
    if not dsn:
        raise ValueError("DATABASE_URL environment variable not set")
    return dsn


def get_db_connection() -> psycopg.Connection:
    """
    Get a synchronous database connection.
    
    Returns:
        psycopg.Connection: Database connection (caller must close)
        
    Raises:
        ValueError: If DATABASE_URL not configured
        psycopg.Error: If connection fails
        
    Example:
        conn = get_db_connection()
        try:
            with conn.cursor() as cur:
                cur.execute("SELECT * FROM api.webhook_subscriptions")
                rows = cur.fetchall()
        finally:
            conn.close()
    """
    dsn = get_database_url()
    return psycopg.connect(dsn, autocommit=False)


# For future async implementation if needed
# async def get_async_db_connection():
#     """Get an async database connection using psycopg AsyncConnection."""
#     dsn = get_database_url()
#     return await psycopg.AsyncConnection.connect(dsn)
