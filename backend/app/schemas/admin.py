from typing import Optional

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class AdminLoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)


class AdminProfileResponse(BaseModel):
    id: int
    full_name: str
    email: EmailStr
    role: str
    is_active: bool
    last_login_at: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class AdminTokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in_minutes: int
    admin: AdminProfileResponse


class AdminAppointmentUpdate(BaseModel):
    customer_name: Optional[str] = None
    phone_number: Optional[str] = None
    appointment_date: Optional[str] = None
    appointment_time: Optional[str] = None
    status: Optional[str] = None
    calendar_event_id: Optional[str] = None
    reason: str = Field(min_length=3, max_length=1000)
