"""add admin authentication and appointment audit logs

Revision ID: 20260721_admin_security
Revises: 7bf4596c123b
Create Date: 2026-07-21
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "20260721_admin_security"
down_revision: Union[str, None] = "7bf4596c123b"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "admins",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("full_name", sa.String(length=120), nullable=False),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("password_hash", sa.String(length=255), nullable=False),
        sa.Column("role", sa.String(length=50), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("last_login_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("email"),
    )
    op.create_index(op.f("ix_admins_id"), "admins", ["id"], unique=False)
    op.create_index(op.f("ix_admins_email"), "admins", ["email"], unique=True)

    op.create_table(
        "appointment_audit_logs",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("appointment_id", sa.Integer(), nullable=False),
        sa.Column("admin_id", sa.Integer(), nullable=True),
        sa.Column("action", sa.String(length=80), nullable=False),
        sa.Column("old_values", sa.Text(), nullable=True),
        sa.Column("new_values", sa.Text(), nullable=True),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["admin_id"], ["admins.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["appointment_id"], ["appointments.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_appointment_audit_logs_id"), "appointment_audit_logs", ["id"], unique=False)
    op.create_index(op.f("ix_appointment_audit_logs_admin_id"), "appointment_audit_logs", ["admin_id"], unique=False)
    op.create_index(op.f("ix_appointment_audit_logs_appointment_id"), "appointment_audit_logs", ["appointment_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_appointment_audit_logs_appointment_id"), table_name="appointment_audit_logs")
    op.drop_index(op.f("ix_appointment_audit_logs_admin_id"), table_name="appointment_audit_logs")
    op.drop_index(op.f("ix_appointment_audit_logs_id"), table_name="appointment_audit_logs")
    op.drop_table("appointment_audit_logs")
    op.drop_index(op.f("ix_admins_email"), table_name="admins")
    op.drop_index(op.f("ix_admins_id"), table_name="admins")
    op.drop_table("admins")
