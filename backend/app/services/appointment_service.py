from sqlalchemy.orm import Session

from app.models.appointment import Appointment
from app.schemas.appointment import AppointmentCreate


def create_appointment(db: Session, appointment: AppointmentCreate):
    db_appointment = Appointment(**appointment.model_dump())

    db.add(db_appointment)
    db.commit()
    db.refresh(db_appointment)

    return db_appointment

def get_appointment(db, appointment_id: int):
    return db.query(Appointment).filter(Appointment.id == appointment_id).first()


def cancel_appointment(db, appointment_id: int):
    appointment = get_appointment(db, appointment_id)

    if not appointment:
        return None

    appointment.status = "cancelled"
    db.commit()
    db.refresh(appointment)

    return appointment