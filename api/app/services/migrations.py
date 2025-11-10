"""SQL migration runner for API service."""
import os
from pathlib import Path
import psycopg


def get_database_url() -> str:
    """Get database URL from environment."""
    dsn = os.environ.get("DATABASE_URL")
    if not dsn:
        raise ValueError("DATABASE_URL environment variable not set")
    return dsn


def run_migrations():
    """Run all SQL migrations in order.
    
    Simply executes migration files sequentially. Each migration file is
    responsible for its own idempotency and history tracking.
    """
    migrations_dir = Path(__file__).parent.parent.parent / "migrations"
    
    if not migrations_dir.exists():
        print("No migrations directory found, skipping migrations")
        return
    
    # Get all .sql files except templates and health checks
    # Sort them to run in order (0000, 0001, 0002, etc.)
    migration_files = sorted([
        f for f in migrations_dir.glob("*.sql")
        if not f.name.startswith("_") and not f.name.startswith("9999")
    ])
    
    if not migration_files:
        print("No migration files found")
        return
    
    print(f"Found {len(migration_files)} migration files")
    
    dsn = get_database_url()
    
    with psycopg.connect(dsn, autocommit=False) as conn:
        with conn.cursor() as cur:
            # Apply each migration
            for migration_file in migration_files:
                filename = migration_file.name
                
                print(f"Applying migration: {filename}")
                
                try:
                    sql = migration_file.read_text(encoding='utf-8')
                    cur.execute(sql)
                    conn.commit()
                    
                    print(f"✓ Successfully applied {filename}")
                    
                except Exception as e:
                    print(f"✗ Failed to apply {filename}: {e}")
                    conn.rollback()
                    raise
    
    print("All migrations applied successfully")
