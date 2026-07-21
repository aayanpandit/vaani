from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database.dependencies import get_db
from app.models.admin import Admin
from app.schemas.admin import AdminLoginRequest, AdminProfileResponse, AdminTokenResponse
from app.services.admin_auth_service import (
    ACCESS_TOKEN_EXPIRE_MINUTES,
    authenticate_admin,
    create_access_token,
    get_current_admin,
)

router = APIRouter(prefix="/admin/auth", tags=["Admin authentication"])


def serialize_admin(admin: Admin) -> AdminProfileResponse:
    return AdminProfileResponse(
        id=admin.id,
        full_name=admin.full_name,
        email=admin.email,
        role=admin.role,
        is_active=admin.is_active,
        last_login_at=admin.last_login_at.isoformat() if admin.last_login_at else None,
    )


@router.post("/login", response_model=AdminTokenResponse)
def admin_login(request: AdminLoginRequest, db: Session = Depends(get_db)):
    admin = authenticate_admin(db, request.email, request.password)
    if not admin:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid email or password.")
    admin.last_login_at = datetime.utcnow()
    db.commit()
    db.refresh(admin)
    return AdminTokenResponse(
        access_token=create_access_token(admin),
        expires_in_minutes=ACCESS_TOKEN_EXPIRE_MINUTES,
        admin=serialize_admin(admin),
    )


@router.get("/me", response_model=AdminProfileResponse)
def admin_profile(admin: Admin = Depends(get_current_admin)):
    return serialize_admin(admin)
