import os
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, Header
from pydantic import BaseModel, EmailStr, Field
from typing import Optional
import jwt as pyjwt

try:
    import psycopg
except Exception:  # pragma: no cover
    psycopg = None  # Optional import; endpoint will report if missing

from .services.database import init_database
from .services import users, otp, jwt, sms
from .services import email as email_service


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize database on startup."""
    try:
        init_database()
        print("Database initialized successfully")
    except Exception as e:
        print(f"Database initialization failed: {e}")
    yield


app = FastAPI(title="Auth Service", version="0.1.0", lifespan=lifespan)


# Request/Response Models
class RequestOtpRequest(BaseModel):
    email: EmailStr
    phone: Optional[str] = None
    preference: Optional[str] = Field(None, pattern="^(sms|email)$")


class RequestOtpResponse(BaseModel):
    success: bool
    message: str
    isNewUser: bool


class VerifyOtpRequest(BaseModel):
    email: EmailStr
    otp: str = Field(..., min_length=6, max_length=6, pattern="^[0-9]{6}$")


class UserProfile(BaseModel):
    id: str
    email: str
    phone: Optional[str]
    otpPreference: Optional[str]
    createdAt: Optional[str]
    lastLoginAt: Optional[str]


class VerifyOtpResponse(BaseModel):
    success: bool
    token: str
    user: UserProfile


class CreateUserRequest(BaseModel):
    email: EmailStr
    phone: str = Field(..., pattern=r"^\+?[1-9]\d{1,14}$")
    preference: str = Field(..., pattern="^(sms|email)$")


class CreateUserResponse(BaseModel):
    success: bool
    message: str
    user: UserProfile


@app.get("/auth/health")
def health():
    """Minimal liveness endpoint for internal checks."""
    return {"status": "ok"}


@app.get("/auth/db/health")
def db_health():
    """Lightweight DB connectivity check using DATABASE_URL.

    Returns:
        { status: "ok" | "skipped" | "error", details?: str }
    """
    dsn = os.environ.get("DATABASE_URL")
    if not dsn:
        return {"status": "skipped", "details": "DATABASE_URL not set"}
    if psycopg is None:
        raise HTTPException(status_code=500, detail="psycopg not installed in image")
    try:
        with psycopg.connect(dsn, connect_timeout=3) as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT version(), current_database(), current_user")
                version, dbname, user = cur.fetchone()
        return {"status": "ok", "database": dbname, "user": user, "version": str(version)}
    except Exception as e:  # pragma: no cover
        raise HTTPException(status_code=500, detail=f"DB check failed: {e}")


@app.get("/auth/egress/health")
def egress_health(url: str | None = None):
    """Simple outbound HTTP check.

    Args:
        url: Optional override of the target URL. If not provided, uses
             EXTERNAL_PING_URL env var or defaults to https://example.com.

    Returns:
        JSON with status ok and the HTTP status code from the target on success.
    """
    target = url or os.environ.get("EXTERNAL_PING_URL", "https://example.com")
    try:
        import urllib.request

        with urllib.request.urlopen(target, timeout=3) as resp:  # nosec B310
            code = resp.getcode()
            return {"status": "ok", "url": target, "code": int(code)}
    except Exception as e:  # pragma: no cover
        raise HTTPException(status_code=500, detail=f"Egress failed: {e}")


@app.get("/auth/versions")
def versions(n: int = 5):
    """Return the last n applied schema versions for the auth service (newest first).

    If the history table is not present yet, falls back to the single current entry
    from auth.schema_registry (if available).
    """
    dsn = os.environ.get("DATABASE_URL")
    if not dsn:
        return []
    if psycopg is None:
        raise HTTPException(status_code=500, detail="psycopg not installed in image")

    try:
        with psycopg.connect(dsn, connect_timeout=3, autocommit=True) as conn:
            with conn.cursor() as cur:
                # Try history first
                try:
                    cur.execute(
                        (
                            "SELECT service, semver, ts_key, applied_at "
                            "FROM auth.schema_registry_history WHERE service='auth' "
                            "ORDER BY applied_at DESC LIMIT %s"
                        ),
                        (max(1, min(n, 100)),),
                    )
                    rows = cur.fetchall()
                except Exception:
                    # If the first query fails (e.g., history table missing), reset state and fallback
                    try:
                        conn.rollback()
                    except Exception:
                        pass
                    rows = []

                if not rows:
                    # Fallback to single pointer row
                    try:
                        cur.execute(
                            "SELECT service, semver, ts_key, applied_at FROM auth.schema_registry WHERE service='auth'"
                        )
                        one = cur.fetchone()
                        if one:
                            rows = [one]
                    except Exception:
                        # Neither history nor pointer exists yet
                        rows = []
        return [
            {
                "service": r[0],
                "semver": r[1],
                "ts_key": int(r[2]) if r[2] is not None else None,
                "applied_at": (r[3].isoformat() if hasattr(r[3], "isoformat") else str(r[3])) if r[3] is not None else None,
            }
            for r in rows
        ]
    except Exception as e:  # pragma: no cover
        raise HTTPException(status_code=500, detail=f"Version lookup failed: {e}")


# OTP Authentication Endpoints

@app.post("/auth/request-otp", response_model=RequestOtpResponse)
def request_otp(request: RequestOtpRequest):
    """Request OTP for email authentication.
    
    Only existing users (created by admin) can request OTP.
    Self-registration is disabled.
    """
    email = request.email.lower()
    
    # Check rate limiting
    if otp.check_rate_limit(email):
        raise HTTPException(
            status_code=429,
            detail="Too many OTP requests. Please try again later."
        )
    
    # Check if user exists
    user = users.find_user_by_email(email)
    
    if user is None:
        # User not found - deny access (no self-registration)
        raise HTTPException(
            status_code=403,
            detail="Access denied. Please contact an administrator to create your account."
        )
    
    # Generate and store OTP
    otp_code = otp.generate_otp()
    otp.store_otp(email, otp_code)
    
    # Send OTP based on preference
    preference = user.otp_preference
    
    try:
        if preference == "sms":
            if not sms.is_twilio_configured():
                raise HTTPException(
                    status_code=500,
                    detail="SMS delivery not configured"
                )
            if not sms.send_otp_sms(user.phone, otp_code):
                raise HTTPException(
                    status_code=500,
                    detail="Failed to send SMS"
                )
        else:  # email
            if not email_service.is_smtp_configured():
                raise HTTPException(
                    status_code=500,
                    detail="Email delivery not configured"
                )
            if not email_service.send_otp_email(email, otp_code):
                raise HTTPException(
                    status_code=500,
                    detail="Failed to send email"
                )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to deliver OTP: {str(e)}"
        )
    
    return RequestOtpResponse(
        success=True,
        message=f"OTP sent to your {preference}",
        isNewUser=False  # All users are pre-created by admin
    )


@app.post("/auth/verify-otp", response_model=VerifyOtpResponse)
def verify_otp(request: VerifyOtpRequest):
    """Verify OTP and issue JWT token."""
    email_addr = request.email.lower()
    
    # Validate OTP
    success, error_msg = otp.validate_otp(email_addr, request.otp)
    
    if not success:
        raise HTTPException(status_code=400, detail=error_msg)
    
    # Get user
    user = users.find_user_by_email(email_addr)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Update last login
    users.update_last_login(email_addr)
    
    # Generate JWT
    token = jwt.generate_jwt(str(user.id), user.email)
    
    # Return token and user profile
    user_dict = user.to_dict()
    return VerifyOtpResponse(
        success=True,
        token=token,
        user=UserProfile(
            id=user_dict["id"],
            email=user_dict["email"],
            phone=user_dict["phone"],
            otpPreference=user_dict["otp_preference"],
            createdAt=user_dict["created_at"],
            lastLoginAt=user_dict["last_login_at"]
        )
    )


@app.get("/auth/me", response_model=UserProfile)
def get_current_user(authorization: Optional[str] = Header(None)):
    """Get current user profile from JWT token."""
    if not authorization:
        raise HTTPException(status_code=401, detail="Authorization header required")
    
    # Extract token from "Bearer <token>"
    parts = authorization.split()
    if len(parts) != 2 or parts[0].lower() != "bearer":
        raise HTTPException(status_code=401, detail="Invalid authorization header format")
    
    token = parts[1]
    
    try:
        payload = jwt.verify_jwt(token)
        email_addr = payload.get("email")
        
        if not email_addr:
            raise HTTPException(status_code=401, detail="Invalid token payload")
        
        user = users.find_user_by_email(email_addr)
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        user_dict = user.to_dict()
        return UserProfile(
            id=user_dict["id"],
            email=user_dict["email"],
            phone=user_dict["phone"],
            otpPreference=user_dict["otp_preference"],
            createdAt=user_dict["created_at"],
            lastLoginAt=user_dict["last_login_at"]
        )
    except pyjwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token has expired")
    except pyjwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")


# Admin Endpoints

@app.post("/auth/admin/create-user", response_model=CreateUserResponse)
def create_user_admin(
    request: CreateUserRequest,
    x_admin_token: Optional[str] = Header(None)
):
    """Admin endpoint to create new users.
    
    Requires X-Admin-Token header matching ADMIN_TOKEN environment variable.
    """
    # Verify admin token
    admin_token = os.environ.get("ADMIN_TOKEN")
    if not admin_token:
        raise HTTPException(
            status_code=500,
            detail="Admin functionality not configured"
        )
    
    if not x_admin_token or x_admin_token != admin_token:
        raise HTTPException(
            status_code=403,
            detail="Invalid or missing admin token"
        )
    
    email = request.email.lower()
    
    # Check if user already exists
    existing_user = users.find_user_by_email(email)
    if existing_user:
        raise HTTPException(
            status_code=409,
            detail=f"User with email {email} already exists"
        )
    
    # Create user
    try:
        user = users.create_user(email, request.phone, request.preference)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    
    user_dict = user.to_dict()
    return CreateUserResponse(
        success=True,
        message=f"User {email} created successfully",
        user=UserProfile(
            id=user_dict["id"],
            email=user_dict["email"],
            phone=user_dict["phone"],
            otpPreference=user_dict["otp_preference"],
            createdAt=user_dict["created_at"],
            lastLoginAt=user_dict["last_login_at"]
        )
    )


@app.post("/auth/logout")
def logout():
    """Logout endpoint (client should clear cookie)."""
    return {"success": True, "message": "Logged out successfully"}
