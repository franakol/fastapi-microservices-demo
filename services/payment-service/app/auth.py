"""
Authentication utilities for Payment Service
"""

from typing import Optional, Dict, Any
from jose import JWTError, jwt
from .config import settings


def verify_token(token: str) -> Optional[Dict[str, Any]]:
    """Verify and decode a JWT token"""
    try:
        payload = jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
        return payload
    except JWTError:
        return None
