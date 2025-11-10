"""User management service."""
from typing import Optional
from datetime import datetime
from uuid import UUID, uuid4
import psycopg
from .database import get_db_connection


class User:
    """User model - email-primary authentication with optional phone and OTP preference."""
    def __init__(self, id: UUID, email: str, phone: Optional[str],
                 otp_preference: Optional[str], role: str, is_active: bool,
                 verified_at: Optional[datetime], last_login_at: Optional[datetime],
                 created_by: Optional[UUID], created_at: datetime, updated_at: datetime):
        self.id = id
        self.email = email
        self.phone = phone
        self.otp_preference = otp_preference
        self.role = role
        self.is_active = is_active
        self.verified_at = verified_at
        self.last_login_at = last_login_at
        self.created_by = created_by
        self.created_at = created_at
        self.updated_at = updated_at
    
    def to_dict(self):
        """Convert to dictionary."""
        def _to_iso(dt):
            """Helper to convert datetime to ISO string."""
            if dt is None:
                return None
            if hasattr(dt, 'isoformat'):
                return dt.isoformat()
            return str(dt)  # Already a string
        
        return {
            "id": str(self.id),
            "email": self.email,
            "phone": self.phone,
            "otp_preference": self.otp_preference,
            "role": self.role,
            "is_active": self.is_active,
            "verified_at": _to_iso(self.verified_at),
            "last_login_at": _to_iso(self.last_login_at),
            "created_by": str(self.created_by) if self.created_by else None,
            "created_at": _to_iso(self.created_at),
            "updated_at": _to_iso(self.updated_at),
        }


def find_user_by_email(email: str) -> Optional[User]:
    """Find user by email address (case-insensitive)."""
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """SELECT id, email, phone, otp_preference, role, is_active, verified_at,
                          last_login_at, created_by, created_at, updated_at
                   FROM auth.users WHERE lower(email) = lower(%s)""",
                (email,)
            )
            row = cur.fetchone()
            if row:
                return User(
                    row['id'], row['email'], row['phone'], row['otp_preference'],
                    row['role'], row['is_active'], row['verified_at'], row['last_login_at'],
                    row['created_by'], row['created_at'], row['updated_at']
                )
            return None


def find_user_by_id(user_id: UUID) -> Optional[User]:
    """Find user by ID."""
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """SELECT id, email, phone, otp_preference, role, is_active, verified_at,
                          last_login_at, created_by, created_at, updated_at
                   FROM auth.users WHERE id = %s""",
                (user_id,)
            )
            row = cur.fetchone()
            if row:
                return User(
                    row['id'], row['email'], row['phone'], row['otp_preference'],
                    row['role'], row['is_active'], row['verified_at'], row['last_login_at'],
                    row['created_by'], row['created_at'], row['updated_at']
                )
            return None


def create_user(email: str, phone: Optional[str] = None, 
                otp_preference: Optional[str] = None, role: str = 'user',
                created_by: Optional[UUID] = None) -> User:
    """Create a new user with email as primary identifier."""
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            try:
                user_id = uuid4()
                cur.execute(
                    """INSERT INTO auth.users (id, email, phone, otp_preference, role, is_active, created_by)
                       VALUES (%s, %s, %s, %s, %s, %s, %s)
                       RETURNING id, email, phone, otp_preference, role, is_active, verified_at,
                                 last_login_at, created_by, created_at, updated_at""",
                    (user_id, email.lower(), phone, otp_preference, role, True, created_by)
                )
                conn.commit()
                row = cur.fetchone()
                return User(
                    row['id'], row['email'], row['phone'], row['otp_preference'],
                    row['role'], row['is_active'], row['verified_at'], row['last_login_at'],
                    row['created_by'], row['created_at'], row['updated_at']
                )
            except psycopg.errors.UniqueViolation:
                conn.rollback()
                raise ValueError(f"User with email {email} already exists")


def update_last_login(email: str) -> None:
    """Update user's last login timestamp."""
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "UPDATE auth.users SET last_login_at = NOW(), updated_at = NOW() WHERE lower(email) = lower(%s)",
                (email,)
            )
            conn.commit()


def verify_user(email: str) -> None:
    """Mark user as verified (set verified_at timestamp)."""
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "UPDATE auth.users SET verified_at = NOW(), updated_at = NOW() WHERE lower(email) = lower(%s)",
                (email,)
            )
            conn.commit()


def update_user(email: str, phone: Optional[str] = None,
                otp_preference: Optional[str] = None, role: Optional[str] = None,
                is_active: Optional[bool] = None) -> Optional[User]:
    """Update user information."""
    updates = []
    params = []
    
    if phone is not None:
        updates.append("phone = %s")
        params.append(phone)
    
    if otp_preference is not None:
        updates.append("otp_preference = %s")
        params.append(otp_preference)
    
    if role is not None:
        updates.append("role = %s")
        params.append(role)
    
    if is_active is not None:
        updates.append("is_active = %s")
        params.append(is_active)
    
    if not updates:
        return find_user_by_email(email)
    
    updates.append("updated_at = NOW()")
    params.append(email.lower())
    
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                f"""UPDATE auth.users 
                    SET {', '.join(updates)}
                    WHERE lower(email) = lower(%s)
                    RETURNING id, email, phone, otp_preference, role, is_active, verified_at,
                              last_login_at, created_by, created_at, updated_at""",
                params
            )
            conn.commit()
            row = cur.fetchone()
            if row:
                return User(*row)
            return None
