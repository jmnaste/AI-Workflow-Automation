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

from .services.migrations import run_migrations
from .services import users, otp, jwt, sms
from .services import email as email_service
from .routers import oauth, credentials, credentials_oauth

"""
User Role Definitions:
- user: Standard user with basic access (no admin console access)
- super: Elevated user with additional privileges in business workflows (no admin console access)
- admin: Full administrative access including admin console and user management

Note: Only 'admin' role has access to admin console endpoints (/auth/admin/*).
Super users have elevated business privileges but cannot access user management.
"""


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Run database migrations on startup."""
    try:
        run_migrations()
        print("Database migrations completed successfully")
    except Exception as e:
        print(f"Database migration failed: {e}")
        raise
    yield


app = FastAPI(title="Auth Service", version="0.1.0", lifespan=lifespan)

# Include routers
app.include_router(oauth.router)  # Old tenant OAuth flow (to be deprecated)
app.include_router(credentials.router)  # New credentials CRUD
app.include_router(credentials_oauth.router)  # New credentials OAuth flow

# Request/Response Models
class RequestOtpRequest(BaseModel):
    email: EmailStr
    phone: Optional[str] = Field(None, pattern=r"^\+[1-9]\d{1,14}$")
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
    role: str
    isActive: bool
    verifiedAt: Optional[str]
    createdAt: Optional[str]
    lastLoginAt: Optional[str]


class VerifyOtpResponse(BaseModel):
    success: bool
    token: str
    user: UserProfile


class CreateUserRequest(BaseModel):
    email: EmailStr
    phone: Optional[str] = Field(None, pattern=r"^\+[1-9]\d{1,14}$")
    preference: Optional[str] = Field(None, pattern="^(sms|email)$")
    role: str = Field(default="user", pattern="^(user|admin|super)$")


class CreateUserResponse(BaseModel):
    success: bool
    message: str
    user: UserProfile


class ListUsersResponse(BaseModel):
    users: list[UserProfile]
    total: int
    page: int
    limit: int


class UpdateUserRequest(BaseModel):
    role: Optional[str] = Field(None, pattern="^(user|admin|super)$")
    isActive: Optional[bool] = None


class UpdateUserResponse(BaseModel):
    success: bool
    message: str
    user: UserProfile


class SystemSettings(BaseModel):
    otpExpiry: int  # minutes
    otpMaxAttempts: int
    rateLimitWindow: int  # minutes
    rateLimitMaxRequests: int


class UpdateUserRequest(BaseModel):
    email: Optional[str] = None
    phone: Optional[str] = None
    preference: Optional[str] = None
    role: Optional[str] = None
    isActive: Optional[bool] = None


class DeleteUserResponse(BaseModel):
    success: bool
    message: str


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
    """Request OTP for email-based authentication.
    
    For new users: requires phone and preference (sms or email)
    For existing users: uses saved phone and preference
    """
    email_addr = request.email.lower()
    
    # Check rate limiting
    if otp.check_rate_limit(email_addr):
        raise HTTPException(
            status_code=429,
            detail="Too many OTP requests. Please try again later."
        )
    
    # Check if user exists
    user = users.find_user_by_email(email_addr)
    is_new_user = user is None
    
    if is_new_user:
        # New user - require phone and preference
        if not request.phone or not request.preference:
            raise HTTPException(
                status_code=400,
                detail="Phone number and OTP preference required for new users"
            )
        
        # Create new user
        try:
            user = users.create_user(email_addr, request.phone, request.preference)
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))
    
    if not user.is_active:
        raise HTTPException(
            status_code=403,
            detail="User account is inactive"
        )
    
    # Generate and store OTP
    otp_code = otp.generate_otp()
    otp.store_otp(user.id, otp_code)
    
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
            if not email_service.send_otp_email(email_addr, otp_code):
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
        isNewUser=is_new_user
    )


@app.post("/auth/verify-otp", response_model=VerifyOtpResponse)
def verify_otp_endpoint(request: VerifyOtpRequest):
    """Verify OTP and issue JWT token."""
    email_addr = request.email.lower()
    
    # Get user
    user = users.find_user_by_email(email_addr)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Validate OTP
    success, error_msg = otp.validate_otp(user.id, request.otp)
    
    if not success:
        raise HTTPException(status_code=400, detail=error_msg)
    
    # Update last login and verify user if not already verified
    users.update_last_login(email_addr)
    if not user.verified_at:
        users.verify_user(email_addr)
    
    # Generate JWT
    token = jwt.generate_jwt(str(user.id), user.email, user.role)
    
    # Return token and user profile
    user_dict = user.to_dict()
    return VerifyOtpResponse(
        success=True,
        token=token,
        user=UserProfile(
            id=user_dict["id"],
            email=user_dict["email"],
            phone=user_dict.get("phone"),
            otpPreference=user_dict.get("otp_preference"),
            role=user_dict["role"],
            isActive=user_dict["is_active"],
            verifiedAt=user_dict.get("verified_at"),
            createdAt=user_dict.get("created_at"),
            lastLoginAt=user_dict.get("last_login_at")
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
            phone=user_dict.get("phone"),
            otpPreference=user_dict.get("otp_preference"),
            role=user_dict["role"],
            isActive=user_dict["is_active"],
            verifiedAt=user_dict.get("verified_at"),
            createdAt=user_dict.get("created_at"),
            lastLoginAt=user_dict.get("last_login_at")
        )
    except pyjwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token has expired")
    except pyjwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")


# Admin Endpoints

def verify_admin_jwt(authorization: Optional[str]) -> dict:
    """Verify JWT and check for admin role.
    
    Only 'admin' role has access to admin console endpoints.
    'super' users have elevated business privileges but NOT admin console access.
    
    Raises:
        HTTPException: 401 if token is missing/invalid/expired
        HTTPException: 403 if user role is not 'admin'
    """
    if not authorization:
        raise HTTPException(status_code=401, detail="Authorization header required")
    
    parts = authorization.split()
    if len(parts) != 2 or parts[0].lower() != "bearer":
        raise HTTPException(status_code=401, detail="Invalid authorization header format")
    
    token = parts[1]
    
    try:
        payload = jwt.verify_jwt(token)
        role = payload.get("role")
        
        # Only 'admin' role can access admin console
        if role != "admin":
            raise HTTPException(status_code=403, detail="Admin access required")
        
        return payload
    except pyjwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token has expired")
    except pyjwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")


@app.post("/auth/admin/create-user", response_model=CreateUserResponse)
def create_user_admin(
    request: CreateUserRequest,
    authorization: Optional[str] = Header(None),
    x_admin_token: Optional[str] = Header(None)
):
    """Admin endpoint to create new users.
    
    Supports two auth methods:
    1. JWT Bearer token with admin/super role (preferred)
    2. X-Admin-Token header (legacy, for bootstrapping first admin)
    """
    # Try JWT authentication first
    if authorization:
        verify_admin_jwt(authorization)
    elif x_admin_token:
        # Fallback to legacy X-Admin-Token for bootstrapping
        admin_token = os.environ.get("ADMIN_TOKEN")
        if not admin_token:
            raise HTTPException(
                status_code=500,
                detail="Admin functionality not configured"
            )
        
        if x_admin_token != admin_token:
            raise HTTPException(
                status_code=403,
                detail="Invalid admin token"
            )
    else:
        raise HTTPException(
            status_code=401,
            detail="Authorization required (Bearer token or X-Admin-Token)"
        )
    
    email_addr = request.email.lower()
    
    # Check if user already exists
    existing_user = users.find_user_by_email(email_addr)
    if existing_user:
        raise HTTPException(
            status_code=409,
            detail=f"User with email {email_addr} already exists"
        )
    
    # Create user
    try:
        user = users.create_user(email_addr, request.phone, request.preference, request.role)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    
    user_dict = user.to_dict()
    return CreateUserResponse(
        success=True,
        message=f"User {email_addr} created successfully",
        user=UserProfile(
            id=user_dict["id"],
            email=user_dict["email"],
            phone=user_dict.get("phone"),
            otpPreference=user_dict.get("otp_preference"),
            role=user_dict["role"],
            isActive=user_dict["is_active"],
            verifiedAt=user_dict.get("verified_at"),
            createdAt=user_dict.get("created_at"),
            lastLoginAt=user_dict.get("last_login_at")
        )
    )


@app.get("/auth/admin/users", response_model=ListUsersResponse)
def list_users_admin(
    authorization: Optional[str] = Header(None),
    page: int = 1,
    limit: int = 50,
    search: Optional[str] = None
):
    """Admin endpoint to list all users.
    
    Requires JWT Bearer token with admin/super role.
    """
    verify_admin_jwt(authorization)
    
    # Validate pagination
    if page < 1:
        raise HTTPException(status_code=400, detail="Page must be >= 1")
    if limit < 1 or limit > 100:
        raise HTTPException(status_code=400, detail="Limit must be between 1 and 100")
    
    offset = (page - 1) * limit
    
    # Get all users (simplified - no search yet)
    all_users = users.list_all_users()
    
    # Apply search filter if provided
    if search:
        search_lower = search.lower()
        all_users = [
            u for u in all_users
            if search_lower in u.to_dict()["email"].lower()
            or (u.to_dict().get("phone") and search_lower in u.to_dict()["phone"])
        ]
    
    total = len(all_users)
    paginated_users = all_users[offset:offset + limit]
    
    user_profiles = []
    for user in paginated_users:
        user_dict = user.to_dict()
        user_profiles.append(UserProfile(
            id=user_dict["id"],
            email=user_dict["email"],
            phone=user_dict.get("phone"),
            otpPreference=user_dict.get("otp_preference"),
            role=user_dict["role"],
            isActive=user_dict["is_active"],
            verifiedAt=user_dict.get("verified_at"),
            createdAt=user_dict.get("created_at"),
            lastLoginAt=user_dict.get("last_login_at")
        ))
    
    return ListUsersResponse(
        users=user_profiles,
        total=total,
        page=page,
        limit=limit
    )


@app.patch("/auth/admin/users/{user_id}", response_model=UpdateUserResponse)
def update_user_admin(
    user_id: str,
    request: UpdateUserRequest,
    authorization: Optional[str] = Header(None)
):
    """Admin endpoint to update user role or status.
    
    Requires JWT Bearer token with admin/super role.
    """
    verify_admin_jwt(authorization)
    
    # Find user
    user = users.find_user_by_id(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Update user fields
    try:
        if request.role is not None:
            user = users.update_user_role(user_id, request.role)
        if request.isActive is not None:
            user = users.update_user_status(user_id, request.isActive)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    
    user_dict = user.to_dict()
    return UpdateUserResponse(
        success=True,
        message=f"User {user_dict['email']} updated successfully",
        user=UserProfile(
            id=user_dict["id"],
            email=user_dict["email"],
            phone=user_dict.get("phone"),
            otpPreference=user_dict.get("otp_preference"),
            role=user_dict["role"],
            isActive=user_dict["is_active"],
            verifiedAt=user_dict.get("verified_at"),
            createdAt=user_dict.get("created_at"),
            lastLoginAt=user_dict.get("last_login_at")
        )
    )


@app.post("/auth/admin/users", response_model=CreateUserResponse)
def create_user_by_admin(
    request: CreateUserRequest,
    authorization: Optional[str] = Header(None)
):
    """Admin endpoint to create a new user.
    
    Requires JWT Bearer token with admin/super role.
    """
    verify_admin_jwt(authorization)
    
    email_addr = request.email.lower()
    
    # Check if user already exists
    existing_user = users.find_user_by_email(email_addr)
    if existing_user:
        raise HTTPException(
            status_code=409,
            detail=f"User with email {email_addr} already exists"
        )
    
    # Create user
    try:
        user = users.create_user(email_addr, request.phone, request.preference, request.role)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    
    user_dict = user.to_dict()
    return CreateUserResponse(
        success=True,
        message=f"User {email_addr} created successfully",
        user=UserProfile(
            id=user_dict["id"],
            email=user_dict["email"],
            phone=user_dict.get("phone"),
            otpPreference=user_dict.get("otp_preference"),
            role=user_dict["role"],
            isActive=user_dict["is_active"],
            verifiedAt=user_dict.get("verified_at"),
            createdAt=user_dict.get("created_at"),
            lastLoginAt=user_dict.get("last_login_at")
        )
    )


@app.patch("/auth/admin/users/{user_id}", response_model=UpdateUserResponse)
def update_user_admin(
    user_id: str,
    update_data: UpdateUserRequest,
    authorization: Optional[str] = Header(None)
):
    """Admin endpoint to update a user.
    
    Requires JWT Bearer token with admin/super role.
    """
    verify_admin_jwt(authorization)
    
    # Find user
    user = users.find_user_by_id(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Update user
    try:
        updated_user = users.update_user(
            user_id=user_id,
            email=update_data.email,
            phone=update_data.phone,
            otp_preference=update_data.preference,
            role=update_data.role,
            is_active=update_data.isActive
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    
    user_dict = updated_user.to_dict()
    
    return UpdateUserResponse(
        success=True,
        message=f"User {user_dict['email']} updated successfully",
        user=UserProfile(
            id=user_dict["id"],
            email=user_dict["email"],
            phone=user_dict.get("phone"),
            otpPreference=user_dict.get("otp_preference"),
            role=user_dict["role"],
            isActive=user_dict["is_active"],
            verifiedAt=user_dict.get("verified_at"),
            createdAt=user_dict.get("created_at"),
            lastLoginAt=user_dict.get("last_login_at")
        )
    )


@app.delete("/auth/admin/users/{user_id}", response_model=DeleteUserResponse)
def delete_user_admin(
    user_id: str,
    authorization: Optional[str] = Header(None)
):
    """Admin endpoint to delete a user.
    
    Requires JWT Bearer token with admin/super role.
    """
    verify_admin_jwt(authorization)
    
    # Find user
    user = users.find_user_by_id(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    email = user.to_dict()["email"]
    
    # Delete user
    try:
        users.delete_user(user_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    
    return DeleteUserResponse(
        success=True,
        message=f"User {email} deleted successfully"
    )


class TenantResponse(BaseModel):
    id: str
    provider: str
    externalTenantId: str
    externalAccountId: str
    displayName: str
    metadata: dict
    createdAt: str
    updatedAt: str
    lastRefreshedAt: Optional[str] = None


class ListTenantsResponse(BaseModel):
    tenants: list[TenantResponse]


@app.get("/auth/tenants", response_model=ListTenantsResponse)
def list_tenants_admin(authorization: Optional[str] = Header(None)):
    """Admin endpoint to list all connected tenants.
    
    Requires JWT Bearer token with admin role.
    Returns list of all connected external accounts (MS365, Google Workspace, etc).
    """
    verify_admin_jwt(authorization)
    
    dsn = os.environ.get("DATABASE_URL")
    if not dsn or psycopg is None:
        raise HTTPException(status_code=500, detail="Database not configured")
    
    try:
        with psycopg.connect(dsn) as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT 
                        t.id, 
                        t.provider, 
                        t.external_tenant_id,
                        t.external_tenant_id as external_account_id,
                        t.display_name, 
                        t.metadata, 
                        t.created_at, 
                        t.updated_at,
                        tt.last_refreshed_at
                    FROM auth.tenants t
                    LEFT JOIN auth.tenant_tokens tt ON t.id = tt.tenant_id
                    ORDER BY t.created_at DESC
                """)
                rows = cur.fetchall()
                
                tenants = []
                for row in rows:
                    tenants.append(TenantResponse(
                        id=str(row['id']),
                        provider=row['provider'],
                        externalTenantId=row['external_tenant_id'],
                        externalAccountId=row['external_account_id'],
                        displayName=row['display_name'],
                        metadata=row['metadata'] or {},
                        createdAt=row['created_at'].isoformat(),
                        updatedAt=row['updated_at'].isoformat(),
                        lastRefreshedAt=row['last_refreshed_at'].isoformat() if row['last_refreshed_at'] else None
                    ))
                
                return ListTenantsResponse(tenants=tenants)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database query failed: {str(e)}")


@app.delete("/auth/tenants/{tenant_id}")
def delete_tenant_admin(tenant_id: str, authorization: Optional[str] = Header(None)):
    """Admin endpoint to disconnect (delete) a tenant.
    
    Requires JWT Bearer token with admin role.
    Deletes the tenant and all associated tokens (CASCADE).
    """
    verify_admin_jwt(authorization)
    
    dsn = os.environ.get("DATABASE_URL")
    if not dsn or psycopg is None:
        raise HTTPException(status_code=500, detail="Database not configured")
    
    try:
        with psycopg.connect(dsn) as conn:
            with conn.cursor() as cur:
                cur.execute("DELETE FROM auth.tenants WHERE id = %s", (tenant_id,))
                if cur.rowcount == 0:
                    raise HTTPException(status_code=404, detail="Tenant not found")
            conn.commit()
        
        return {"success": True, "message": "Tenant disconnected successfully"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete tenant: {str(e)}")


@app.get("/auth/admin/settings", response_model=SystemSettings)
def get_settings_admin(authorization: Optional[str] = Header(None)):
    """Admin endpoint to get system settings.
    
    Requires JWT Bearer token with admin/super role.
    Returns current environment variable values.
    """
    verify_admin_jwt(authorization)
    
    return SystemSettings(
        otpExpiry=int(os.environ.get("OTP_EXPIRY_MINUTES", "5")),
        otpMaxAttempts=int(os.environ.get("OTP_MAX_ATTEMPTS", "8")),
        rateLimitWindow=int(os.environ.get("RATE_LIMIT_WINDOW_MINUTES", "15")),
        rateLimitMaxRequests=int(os.environ.get("RATE_LIMIT_MAX_REQUESTS", "3"))
    )


@app.post("/auth/admin/settings", response_model=SystemSettings)
def update_settings_admin(
    settings: SystemSettings,
    authorization: Optional[str] = Header(None)
):
    """Admin endpoint to update system settings.
    
    Requires JWT Bearer token with admin/super role.
    Note: Currently returns the requested settings but does not persist them.
    Settings are configured via environment variables.
    """
    verify_admin_jwt(authorization)
    
    # Note: This endpoint accepts settings but doesn't persist them
    # Settings are currently environment-variable based
    # Future enhancement: Add runtime configuration storage
    
    return settings


@app.post("/auth/logout")
def logout():
    """Logout endpoint (client should clear cookie)."""
    return {"success": True, "message": "Logged out successfully"}
