from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.security import ROLE_PERMISSIONS, Role, create_access_token, hash_password, verify_password
from app.models.entities import Organization, OrganizationMember, User
from app.schemas.gateway import TokenResponse, UserProfile
from app.services.policies.policy_service import ensure_default_policies


@dataclass
class AuthContext:
    user_id: str
    email: str
    full_name: str
    role: str
    org_id: str
    org_name: str
    department: str
    permissions: list[str]


SEED_USERS = [
    ("admin@bharatfin.in", "Aarav Deshmukh", "Admin@2026!", Role.ADMIN.value, "security_engineering"),
    ("privacy@bharatfin.in", "Meera Iyer", "Privacy@2026!", Role.PRIVACY_OFFICER.value, "governance"),
    ("underwriter@bharatfin.in", "Siddharth Verma", "Underwriter@2026!", Role.LOAN_UNDERWRITER.value, "credit_risk"),
    ("analyst@bharatfin.in", "Rohan Kulkarni", "Analyst@2026!", Role.ANALYST.value, "loan_operations"),
    ("support@bharatfin.in", "Priya Nair", "Support@2026!", Role.SUPPORT_AGENT.value, "customer_support"),
    ("auditor@bharatfin.in", "Kavita Nair", "Auditor@2026!", Role.AUDITOR.value, "compliance"),
]


def ensure_seed_data(db: Session) -> None:
    """Seed initial enterprise organization, policies, and role-based demo accounts if empty."""
    org = db.scalar(select(Organization).where(Organization.slug == "bharatfin-enterprise"))
    if org is None:
        org = Organization(name="BharatFin Enterprise Ltd", slug="bharatfin-enterprise", is_active=True)
        db.add(org)
        db.flush()

    ensure_default_policies(db, org.id)

    for email, full_name, raw_pwd, role, dept in SEED_USERS:
        user = db.scalar(select(User).where(User.email == email))
        if user is None:
            user = User(
                email=email,
                full_name=full_name,
                password_hash=hash_password(raw_pwd),
                is_active=True,
            )
            db.add(user)
            db.flush()
        member = db.scalar(
            select(OrganizationMember).where(
                OrganizationMember.organization_id == org.id,
                OrganizationMember.user_id == user.id,
            )
        )
        if member is None:
            member = OrganizationMember(
                organization_id=org.id,
                user_id=user.id,
                role=role,
                department=dept,
            )
            db.add(member)
    db.commit()


def authenticate_user(db: Session, email: str, password: str) -> TokenResponse | None:
    user = db.scalar(select(User).where(User.email == email.strip().lower(), User.is_active.is_(True)))
    if user is None or not verify_password(password, user.password_hash):
        return None

    member = db.scalar(select(OrganizationMember).where(OrganizationMember.user_id == user.id))
    if member is None:
        return None
    org = db.scalar(select(Organization).where(Organization.id == member.organization_id, Organization.is_active.is_(True)))
    if org is None:
        return None

    role_enum = Role(member.role)
    perms = sorted(ROLE_PERMISSIONS.get(role_enum, set()))
    token = create_access_token(
        subject=user.id,
        org_id=org.id,
        role=member.role,
        email=user.email,
    )
    profile = UserProfile(
        id=user.id,
        email=user.email,
        full_name=user.full_name,
        role=member.role,
        org_id=org.id,
        org_name=org.name,
        department=member.department,
        permissions=perms,
    )
    return TokenResponse(access_token=token, user=profile)
