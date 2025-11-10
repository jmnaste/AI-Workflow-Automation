"""OTP generation, storage, and validation service."""
import os
import secrets
from datetime import datetime, timedelta
import bcrypt
from .database import get_db_connection


def get_otp_config():
    """Get OTP configuration from environment."""
    return {
        "expiry_minutes": int(os.environ.get("OTP_EXPIRY_MINUTES", "5")),
        "max_attempts": int(os.environ.get("OTP_MAX_ATTEMPTS", "3")),
        "rate_limit_window_minutes": int(os.environ.get("RATE_LIMIT_WINDOW_MINUTES", "15")),
        "rate_limit_max_requests": int(os.environ.get("RATE_LIMIT_MAX_REQUESTS", "3")),
    }


def generate_otp() -> str:
    """Generate a random 6-digit OTP."""
    return f"{secrets.randbelow(1000000):06d}"


def hash_otp(otp: str) -> str:
    """Hash OTP using bcrypt."""
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(otp.encode(), salt).decode()


def verify_otp_hash(otp: str, otp_hash: str) -> bool:
    """Verify OTP against hash."""
    try:
        return bcrypt.checkpw(otp.encode(), otp_hash.encode())
    except Exception:
        return False


def check_rate_limit(email: str) -> bool:
    """Check if email has exceeded rate limit.
    
    Returns:
        True if rate limit exceeded, False otherwise
    """
    config = get_otp_config()
    window_minutes = config["rate_limit_window_minutes"]
    max_requests = config["rate_limit_max_requests"]
    
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            # Get current rate limit record
            cur.execute(
                "SELECT request_count, window_start FROM auth.rate_limit WHERE email = %s",
                (email.lower(),)
            )
            row = cur.fetchone()
            
            now = datetime.now()
            window_start = now
            request_count = 0
            
            if row:
                window_start = row["window_start"]
                request_count = row["request_count"]
                
                # Check if window has expired
                if now - window_start > timedelta(minutes=window_minutes):
                    # Reset window
                    window_start = now
                    request_count = 0
            
            # Check if limit exceeded
            if request_count >= max_requests:
                return True
            
            # Increment counter
            cur.execute(
                """
                INSERT INTO auth.rate_limit (email, request_count, window_start)
                VALUES (%s, %s, %s)
                ON CONFLICT (email) DO UPDATE 
                SET request_count = %s, window_start = %s
                """,
                (email.lower(), request_count + 1, window_start, request_count + 1, window_start)
            )
            conn.commit()
            
            return False


def store_otp(email: str, otp: str) -> None:
    """Store OTP hash with expiry."""
    config = get_otp_config()
    otp_hash = hash_otp(otp)
    expires_at = datetime.now() + timedelta(minutes=config["expiry_minutes"])
    
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO auth.otp_storage (email, otp_hash, attempts, expires_at)
                VALUES (%s, %s, 0, %s)
                ON CONFLICT (email) DO UPDATE 
                SET otp_hash = %s, attempts = 0, expires_at = %s, created_at = NOW()
                """,
                (email.lower(), otp_hash, expires_at, otp_hash, expires_at)
            )
            conn.commit()


def validate_otp(email: str, otp: str) -> tuple[bool, str]:
    """Validate OTP for email.
    
    Returns:
        (success, error_message)
    """
    config = get_otp_config()
    
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT otp_hash, attempts, expires_at FROM auth.otp_storage WHERE email = %s",
                (email.lower(),)
            )
            row = cur.fetchone()
            
            if not row:
                return False, "No OTP found for this email"
            
            # Check expiry
            if datetime.now() > row["expires_at"]:
                # Clean up expired OTP
                cur.execute("DELETE FROM auth.otp_storage WHERE email = %s", (email.lower(),))
                conn.commit()
                return False, "OTP has expired"
            
            # Check attempts
            if row["attempts"] >= config["max_attempts"]:
                return False, "Maximum attempts exceeded"
            
            # Verify OTP
            if not verify_otp_hash(otp, row["otp_hash"]):
                # Increment attempts
                cur.execute(
                    "UPDATE auth.otp_storage SET attempts = attempts + 1 WHERE email = %s",
                    (email.lower(),)
                )
                conn.commit()
                return False, "Invalid OTP"
            
            # Success - clean up OTP
            cur.execute("DELETE FROM auth.otp_storage WHERE email = %s", (email.lower(),))
            conn.commit()
            
            return True, ""


def cleanup_expired_otps() -> int:
    """Remove expired OTPs from database.
    
    Returns:
        Number of OTPs deleted
    """
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM auth.otp_storage WHERE expires_at < NOW()")
            deleted = cur.rowcount
            conn.commit()
            return deleted
