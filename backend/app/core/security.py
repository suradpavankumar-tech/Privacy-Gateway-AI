"""
=========================================================================================
security.py — Enterprise Cryptography, Password Hashing & RBAC Permission Matrix
=========================================================================================

Tech Stack:
 - PyJWT (RFC 7519 JSON Web Token issuance and claims verification)
 - Bcrypt (Adaptive one-way cryptographic password hashing)
 - Python Standard Library (hmac, hashlib, datetime, enum)

Key Architectural Responsibilities:
 1. Role-Based Access Control (RBAC) Specification:
    - Formalizes enterprise system roles (Admin, Privacy Officer, Security Officer,
      Loan Underwriter, Analyst, Support Agent, Auditor).
    - Maps each role to explicit functional capabilities (e.g. `restore:execute`,
      `policy:write`, `audit:export`).

 2. Credential Security:
    - Implements salted bcrypt hashing for persistent user passwords.

 3. Session Cryptography:
    - Mints and validates cryptographically signed JWT access tokens (HS256)
      embedding subject, role, tenant, and expiration claims.
=========================================================================================
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Any

import bcrypt
import jwt

from app.core.config import get_settings


class Role(str, Enum):
    ADMIN = "admin"
    SECURITY_OFFICER = "security_officer"
    PRIVACY_OFFICER = "privacy_officer"
    LOAN_UNDERWRITER = "loan_underwriter"
    DEVELOPER = "developer"
    ANALYST = "analyst"
    SUPPORT_AGENT = "support_agent"
    AUDITOR = "auditor"


ROLE_PERMISSIONS: dict[Role, set[str]] = {
    Role.ADMIN: {
        "process:submit",
        "process:analyze",
        "process:mask",
        "restore:execute",
        "policy:read",
        "policy:write",
        "audit:read",
        "audit:export",
        "evaluation:run",
        "evaluation:read",
        "providers:read",
    },
    Role.SECURITY_OFFICER: {
        "process:submit",
        "process:analyze",
        "process:mask",
        "restore:execute",
        "policy:read",
        "policy:write",
        "audit:read",
        "audit:export",
        "evaluation:run",
        "evaluation:read",
        "providers:read",
    },
    Role.PRIVACY_OFFICER: {
        "process:submit",
        "process:analyze",
        "process:mask",
        "restore:execute",
        "policy:read",
        "policy:write",
        "audit:read",
        "audit:export",
        "evaluation:run",
        "evaluation:read",
        "providers:read",
    },
    Role.LOAN_UNDERWRITER: {
        "process:submit",
        "process:analyze",
        "process:mask",
        "restore:execute",
        "policy:read",
        "evaluation:read",
        "providers:read",
    },
    Role.DEVELOPER: {
        "process:submit",
        "process:analyze",
        "process:mask",
        "policy:read",
        "evaluation:read",
        "providers:read",
    },
    Role.ANALYST: {
        "process:submit",
        "process:analyze",
        "process:mask",
        "policy:read",
        "evaluation:read",
        "providers:read",
    },
    Role.SUPPORT_AGENT: {
        "process:submit",
        "process:analyze",
        "process:mask",
        "policy:read",
        "evaluation:read",
        "providers:read",
    },
    Role.AUDITOR: {
        "policy:read",
        "audit:read",
        "audit:export",
        "evaluation:read",
        "providers:read",
    },
}


def hash_password(password: str) -> str:
    salt = bcrypt.gensalt(rounds=12)
    return bcrypt.hashpw(password.encode("utf-8"), salt).decode("utf-8")


def verify_password(password: str, password_hash: str) -> bool:
    return bcrypt.checkpw(password.encode("utf-8"), password_hash.encode("utf-8"))


def create_access_token(
    subject: str,
    org_id: str,
    role: str,
    email: str,
    extra_claims: dict[str, Any] | None = None,
) -> str:
    settings = get_settings()
    now = datetime.now(timezone.utc)
    payload: dict[str, Any] = {
        "sub": subject,
        "org_id": org_id,
        "role": role,
        "email": email,
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(minutes=settings.JWT_EXPIRY_MINUTES)).timestamp()),
    }
    if extra_claims:
        payload.update(extra_claims)
    return jwt.encode(payload, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)


def decode_access_token(token: str) -> dict[str, Any]:
    settings = get_settings()
    return jwt.decode(token, settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM])


def has_permission(role: str | Role, permission: str) -> bool:
    try:
        role_enum = Role(role) if not isinstance(role, Role) else role
    except ValueError:
        return False
    return permission in ROLE_PERMISSIONS.get(role_enum, set())
