from datetime import datetime

from sqlalchemy import Column, DateTime, Integer, String

from app.database.db import Base


class Appointment(Base):
    __tablename__ = "appointments"

    id = Column(
        Integer,
        primary_key=True,
        index=True,
    )

    appointment_code = Column(
        String(5),
        unique=True,
        index=True,
        nullable=False,
    )

    customer_name = Column(
        String,
        nullable=True,
    )

    phone_number = Column(
        String,
        index=True,
        nullable=True,
    )

    appointment_date = Column(
        String,
        index=True,
        nullable=True,
    )

    appointment_time = Column(
        String,
        nullable=True,
    )

    status = Column(
        String,
        default="on_hold",
        nullable=False,
        index=True,
    )

    calendar_event_id = Column(
        String,
        nullable=True,
    )

    created_at = Column(
        DateTime,
        default=datetime.utcnow,
        nullable=False,
    )

    updated_at = Column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False,
    )