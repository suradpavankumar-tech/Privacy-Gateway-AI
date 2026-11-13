"""
=========================================================================================
auth.py — Enterprise Authentication & Role-Based Access Control (RBAC) Router
=========================================================================================

Tech Stack:
 - FastAPI (REST routing, dependency injection for DB session and auth context)
 - SQLAlchemy (User account and credential verification)
 - PyJWT & Passlib / Bcrypt (Cryptographic password verification and token minting)

Key Architectural Responsibilities:
 1. User Authentication (`/auth/login`):
    - Verifies user email and salted bcrypt password hash.
    - Issues cryptographically signed JSON Web Tokens (JWT) containing tenant
      and role claims (`admin`, `privacy_officer`, `loan_underwriter`, etc.).

 2. Session Context Discovery (`/auth/me`):
    - Decodes incoming Bearer JWT to construct the request's security context.
    - Returns permissions, organization membership, and role authorizations.
=========================================================================================
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_auth, rate_limit_guard
from app.database.session import get_db
from app.schemas.gateway import LoginRequest, TokenResponse, UserProfile
from app.services.auth_service import AuthContext, authenticate_user

router = APIRouter(prefix="/api/v1/auth", tags=["Authentication"], dependencies=[Depends(rate_limit_guard)])


@router.post("/login", response_model=TokenResponse)
def login(payload: LoginRequest, db: Session = Depends(get_db)) -> TokenResponse:
    token_res = authenticate_user(db, payload.email, payload.password)
    if token_res is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password.",
        )
    return token_res


@router.get("/me", response_model=UserProfile)
def get_me(auth: AuthContext = Depends(get_current_auth)) -> UserProfile:
    return UserProfile(
        id=auth.user_id,
        email=auth.email,
        full_name=auth.full_name,
        role=auth.role,
        org_id=auth.org_id,
        org_name=auth.org_name,
        department=auth.department,
        permissions=auth.permissions,
    )
