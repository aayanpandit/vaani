from pydantic import BaseModel


class AppointmentCreate(BaseModel):
    customer_name: str
    phone_number: str
    appointment_time: str


class AppointmentResponse(AppointmentCreate):
    id: int
    status: str

    class Config:
        from_attributes = True