from sqlalchemy import Column, Integer, String

from app.database.db import Base


class Appointment(Base):
    __tablename__ = "appointments"

    id = Column(Integer, primary_key=True, index=True)
    customer_name = Column(String, nullable=False)
    phone_number = Column(String, nullable=False)
    appointment_time = Column(String, nullable=False)
    status = Column(String, default="scheduled")
    calendar_event_id = Column(String, nullable=True)
    
