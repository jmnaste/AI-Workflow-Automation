"""User management service."""
from typing import Optional
from datetime import datetime
from uuid import UUID
import psycopg
from .database import get_db_connection


class User:
    """User model."""
    def __init__(self, id: UUID, email: str, phone: Optional[str], 
                 otp_preference: Optional[str], created_at: datetime, 
                 last_login_at: Optional[datetime]):
        self.id = id
        self.email = email
        self.phone = phone
        self.otp_preference = otp_preference
        self.created_at = created_at
        self.last_login_at = last_login_at
    
    def to_dict(self):
        """Convert to dictionary."""
        return {
            "id": str(self.id),
            "email": self.email,
            "phone": self.phone,
            "otp_preference": self.otp_preference,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "last_login_at": self.last_login_at.isoformat() if self.last_login_at else None,
        }


def find_user_by_email(email: str) -> Optional[User]:
    """Find user by email address."""
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT id, email, phone, otp_preference, created_at, last_login_at "
                "FROM auth.users WHERE email = %s",
                (email.lower(),)
            )
            row = cur.fetchone()
            if row:
                return User(**row)
            return None


def create_user(email: str, phone: str, otp_preference: str) -> User:
    """Create a new user."""
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            try:
                cur.execute(
                    """
                    INSERT INTO auth.users (email, phone, otp_preference)
                    VALUES (%s, %s, %s)
                    RETURNING id, email, phone, otp_preference, created_at, last_login_at
                    """,
                    (email.lower(), phone, otp_preference)
                )
                conn.commit()
                row = cur.fetchone()
                return User(**row)
            except psycopg.errors.UniqueViolation:
                conn.rollback()
                raise ValueError(f"User with email {email} already exists")


def update_last_login(email: str) -> None:
    """Update user's last login timestamp."""
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "UPDATE auth.users SET last_login_at = NOW() WHERE email = %s",
                (email.lower(),)
            )
            conn.commit()


def update_user(email: str, phone: Optional[str] = None, 
                otp_preference: Optional[str] = None) -> Optional[User]:
    """Update user information."""
    updates = []
    params = []
    
    if phone is not None:
        updates.append("phone = %s")
        params.append(phone)
    
    if otp_preference is not None:
        updates.append("otp_preference = %s")
        params.append(otp_preference)
    
    if not updates:
        return find_user_by_email(email)
    
    params.append(email.lower())
    
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                f"""
                UPDATE auth.users 
                SET {', '.join(updates)}
                WHERE email = %s
                RETURNING id, email, phone, otp_preference, created_at, last_login_at
                """,
                params
            )
            conn.commit()
            row = cur.fetchone()
            if row:
                return User(**row)
            return None
