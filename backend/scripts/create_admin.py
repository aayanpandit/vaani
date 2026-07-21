import getpass

from app.database.db import SessionLocal
from app.models.admin import Admin
from app.services.admin_auth_service import hash_password


def main() -> None:
    full_name = input("Admin full name: ").strip()
    email = input("Admin email: ").strip().lower()
    password = getpass.getpass("Admin password: ")
    confirm = getpass.getpass("Confirm password: ")

    if len(password) < 8:
        raise SystemExit("Password must be at least 8 characters.")
    if password != confirm:
        raise SystemExit("Passwords do not match.")

    db = SessionLocal()
    try:
        existing = db.query(Admin).filter(Admin.email == email).first()
        if existing:
            raise SystemExit("An admin with that email already exists.")
        db.add(
            Admin(
                full_name=full_name,
                email=email,
                password_hash=hash_password(password),
                role="admin",
                is_active=True,
            )
        )
        db.commit()
        print(f"Admin created successfully: {email}")
    finally:
        db.close()


if __name__ == "__main__":
    main()
