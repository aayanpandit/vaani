from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict


class AppointmentCreate(BaseModel):
    customer_name: Optional[str] = None
    phone_number: Optional[str] = None
    appointment_date: Optional[str] = None
    appointment_time: Optional[str] = None
    status: str = "on_hold"


class AppointmentUpdate(BaseModel):
    customer_name: Optional[str] = None
    phone_number: Optional[str] = None
    appointment_date: Optional[str] = None
    appointment_time: Optional[str] = None
    status: Optional[str] = None


class AppointmentResponse(BaseModel):
    id: int
    appointment_code: str

    customer_name: Optional[str] = None
    phone_number: Optional[str] = None
    appointment_date: Optional[str] = None
    appointment_time: Optional[str] = None

    status: str
    calendar_event_id: Optional[str] = None

    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)