from __future__ import annotations

import time
from collections import defaultdict, deque

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.security import ROLE_PERMISSIONS, Role, decode_access_token, has_permission
from app.database.session import get_db
from app.models.entities import Organization, OrganizationMember, User
from app.services.auth_service import AuthContext

_bearer = HTTPBearer(auto_error=False)
_rate_buckets: dict[str, deque[float]] = defaultdict(deque)


def rate_limit_guard(request: Request) -> None:
    settings = get_settings()
    client_ip = request.client.host if request.client else "unknown"
    now = time.monotonic()
    bucket = _rate_buckets[client_ip]
    cutoff = now - 60.0
    while bucket and bucket[0] < cutoff:
        bucket.popleft()
    if len(bucket) >= settings.RATE_LIMIT_PER_MINUTE:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Rate limit exceeded. Please retry shortly.",
        )
    bucket.append(now)


def get_current_auth(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer),
    db: Session = Depends(get_db),
) -> AuthContext:
    if credentials is None or not credentials.credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication credentials missing.",
        )
    try:
        claims = decode_access_token(credentials.credentials)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired access token.",
        ) from exc

    user_id = claims.get("sub")
    org_id = claims.get("org_id")
    if not user_id or not org_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Malformed token claims.")

    user = db.scalar(select(User).where(User.id == user_id, User.is_active.is_(True)))
    member = db.scalar(
        select(OrganizationMember).where(
            OrganizationMember.user_id == user_id,
            OrganizationMember.organization_id == org_id,
        )
    )
    org = db.scalar(select(Organization).where(Organization.id == org_id, Organization.is_active.is_(True)))
    if user is None or member is None or org is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Account or tenant inactive.")

    role_enum = Role(member.role)
    perms = sorted(ROLE_PERMISSIONS.get(role_enum, set()))
    return AuthContext(
        user_id=user.id,
        email=user.email,
        full_name=user.full_name,
        role=member.role,
        org_id=org.id,
        org_name=org.name,
        department=member.department,
        permissions=perms,
    )


def require_permission(permission: str):
    def _checker(auth: AuthContext = Depends(get_current_auth)) -> AuthContext:
        if not has_permission(auth.role, permission):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Role '{auth.role}' lacks required permission '{permission}'.",
            )
        return auth

    return _checker
