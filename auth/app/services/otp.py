"""OTP generation, storage, and validation service."""
import os
import secrets
from datetime import datetime, timedelta, timezone
from uuid import UUID, uuid4
from typing import Optional
import bcrypt
from .database import get_db_connection


def get_otp_config():
    """Get OTP configuration from environment."""
    return {
        "expiry_minutes": int(os.environ.get("OTP_EXPIRY_MINUTES", "5")),
        "max_attempts": int(os.environ.get("OTP_MAX_ATTEMPTS", "8")),
        "rate_limit_window_minutes": int(os.environ.get("RATE_LIMIT_WINDOW_MINUTES", "15")),
        "rate_limit_max_requests": int(os.environ.get("RATE_LIMIT_MAX_REQUESTS", "3")),
    }


def generate_otp() -> str:
    """Generate a random 6-digit OTP."""
    return f"{secrets.randbelow(1000000):06d}"


def hash_otp(otp: str) -> bytes:
    """Hash OTP using bcrypt, return as bytes."""
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(otp.encode(), salt)


def verify_otp_hash(otp: str, otp_hash: bytes) -> bool:
    """Verify OTP against hash."""
    try:
        return bcrypt.checkpw(otp.encode(), otp_hash)
    except Exception:
        return False


def check_rate_limit(email: str, request_ip: Optional[str] = None) -> bool:
    """Check if email has exceeded rate limit for OTP requests.
    
    Uses auth.rate_limits table with subject_type='phone' (legacy naming, stores email).
    
    Returns:
        True if rate limit exceeded, False otherwise
    """
    config = get_otp_config()
    window_seconds = config["rate_limit_window_minutes"] * 60
    limit_value = config["rate_limit_max_requests"]
    
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            now = datetime.now(timezone.utc)
            window_start = now
            subject = email.lower()
            
            # Check email rate limit (using 'phone' subject_type for backwards compat)
            cur.execute(
                """SELECT count, window_start 
                   FROM auth.rate_limits 
                   WHERE subject_type = 'phone' AND subject = %s 
                   AND window_seconds = %s""",
                (subject, window_seconds)
            )
            row = cur.fetchone()
            
            if row:
                window_start_ts = row["window_start"]
                count = row["count"]
                
                # Check if window has expired
                if now - window_start_ts > timedelta(seconds=window_seconds):
                    # Reset window
                    window_start = now
                    count = 0
                else:
                    # Check if limit exceeded
                    if count >= limit_value:
                        return True
                    window_start = window_start_ts
                    count = count + 1
            else:
                count = 1
            
            # Upsert rate limit record
            cur.execute(
                """INSERT INTO auth.rate_limits 
                   (id, subject_type, subject, window_start, window_seconds, count, limit_value)
                   VALUES (%s, 'phone', %s, %s, %s, %s, %s)
                   ON CONFLICT (subject_type, subject, window_start, window_seconds) 
                   DO UPDATE SET count = %s""",
                (uuid4(), subject, window_start, window_seconds, count, limit_value, count)
            )
            conn.commit()
            
            return False


def store_otp(user_id: UUID, otp: str, request_ip: Optional[str] = None, 
               user_agent: Optional[str] = None) -> UUID:
    """Store OTP challenge in auth.otp_challenges table.
    
    Returns:
        Challenge ID
    """
    config = get_otp_config()
    code_hash = hash_otp(otp)
    expires_at = datetime.now(timezone.utc) + timedelta(minutes=config["expiry_minutes"])
    max_attempts = config["max_attempts"]
    challenge_id = uuid4()
    
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            # Cancel any existing 'sent' challenges for this user
            cur.execute(
                """UPDATE auth.otp_challenges 
                   SET status = 'canceled' 
                   WHERE user_id = %s AND status = 'sent'""",
                (user_id,)
            )
            
            # Insert new challenge
            cur.execute(
                """INSERT INTO auth.otp_challenges 
                   (id, user_id, code_hash, expires_at, max_attempts, request_ip, user_agent)
                   VALUES (%s, %s, %s, %s, %s, %s, %s)""",
                (challenge_id, user_id, code_hash, expires_at, max_attempts, request_ip, user_agent)
            )
            conn.commit()
            return challenge_id


def validate_otp(user_id: UUID, otp: str) -> tuple[bool, str]:
    """Validate OTP for user.
    
    Returns:
        (success, error_message)
    """
    config = get_otp_config()
    
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            # Get active challenge
            cur.execute(
                """SELECT id, code_hash, attempts, max_attempts, expires_at, status
                   FROM auth.otp_challenges 
                   WHERE user_id = %s AND status = 'sent'
                   ORDER BY sent_at DESC
                   LIMIT 1""",
                (user_id,)
            )
            row = cur.fetchone()
            
            if not row:
                return False, "No active OTP found for this user"
            
            challenge_id = row["id"]
            
            # Check expiry
            if datetime.now(timezone.utc) > row["expires_at"]:
                cur.execute(
                    "UPDATE auth.otp_challenges SET status = 'expired' WHERE id = %s",
                    (challenge_id,)
                )
                conn.commit()
                return False, "OTP has expired"
            
            # Check attempts
            if row["attempts"] >= row["max_attempts"]:
                cur.execute(
                    "UPDATE auth.otp_challenges SET status = 'denied' WHERE id = %s",
                    (challenge_id,)
                )
                conn.commit()
                return False, "Maximum attempts exceeded"
            
            # Verify OTP
            if not verify_otp_hash(otp, row["code_hash"]):
                # Increment attempts
                cur.execute(
                    "UPDATE auth.otp_challenges SET attempts = attempts + 1 WHERE id = %s",
                    (challenge_id,)
                )
                conn.commit()
                remaining = row["max_attempts"] - row["attempts"] - 1
                return False, f"Invalid OTP. {remaining} attempts remaining."
            
            # Success - mark as approved
            cur.execute(
                "UPDATE auth.otp_challenges SET status = 'approved', used_at = NOW() WHERE id = %s",
                (challenge_id,)
            )
            conn.commit()
            
            return True, ""


def cleanup_expired_otps() -> int:
    """Mark expired OTP challenges as expired.
    
    Returns:
        Number of OTPs marked as expired
    """
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """UPDATE auth.otp_challenges 
                   SET status = 'expired' 
                   WHERE status = 'sent' AND expires_at < NOW()"""
            )
            updated = cur.rowcount
            conn.commit()
            return updated
