"""JWT token generation and verification."""
import os
from datetime import datetime, timedelta
import jwt


def get_jwt_secret() -> str:
    """Get JWT secret from environment."""
    secret = os.environ.get("JWT_SECRET")
    if not secret:
        raise ValueError("JWT_SECRET environment variable not set")
    return secret


def generate_jwt(user_id: str, email: str) -> str:
    """Generate JWT token for user.
    
    Args:
        user_id: User UUID as string
        email: User email
    
    Returns:
        JWT token string
    """
    secret = get_jwt_secret()
    expiry = datetime.utcnow() + timedelta(days=7)
    
    payload = {
        "userId": user_id,
        "email": email,
        "exp": expiry,
        "iat": datetime.utcnow(),
    }
    
    return jwt.encode(payload, secret, algorithm="HS256")


def verify_jwt(token: str) -> dict:
    """Verify and decode JWT token.
    
    Args:
        token: JWT token string
    
    Returns:
        Decoded payload dictionary
    
    Raises:
        jwt.ExpiredSignatureError: Token has expired
        jwt.InvalidTokenError: Token is invalid
    """
    secret = get_jwt_secret()
    return jwt.decode(token, secret, algorithms=["HS256"])
