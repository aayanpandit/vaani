"""update appointment model

Revision ID: 7bf4596c123b
Revises:
Create Date: 2026-07-21 11:37:08.099708
"""

from __future__ import annotations

import re
from datetime import datetime
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "7bf4596c123b"
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _name_prefix(customer_name: str | None) -> str:
    if not customer_name:
        return "OH"

    cleaned = re.sub(
        r"[^A-Za-z]",
        "",
        customer_name,
    ).upper()

    if len(cleaned) >= 2:
        return cleaned[:2]

    if len(cleaned) == 1:
        return f"{cleaned}X"

    return "OH"


def upgrade() -> None:
    connection = op.get_bind()

    # Add new columns as nullable first because existing rows
    # do not yet have values for them.
    with op.batch_alter_table("appointments") as batch_op:
        batch_op.add_column(
            sa.Column(
                "appointment_code",
                sa.String(length=5),
                nullable=True,
            )
        )
        batch_op.add_column(
            sa.Column(
                "appointment_date",
                sa.String(),
                nullable=True,
            )
        )
        batch_op.add_column(
            sa.Column(
                "created_at",
                sa.DateTime(),
                nullable=True,
            )
        )
        batch_op.add_column(
            sa.Column(
                "updated_at",
                sa.DateTime(),
                nullable=True,
            )
        )

    rows = connection.execute(
        sa.text(
            """
            SELECT id, customer_name, status
            FROM appointments
            ORDER BY id
            """
        )
    ).mappings().all()

    prefix_counters: dict[str, int] = {}
    current_time = datetime.utcnow()

    for row in rows:
        prefix = _name_prefix(row["customer_name"])

        prefix_counters[prefix] = (
            prefix_counters.get(prefix, 0) + 1
        )

        appointment_code = (
            f"{prefix}{prefix_counters[prefix]:03d}"
        )

        old_status = row["status"]

        # Convert the old "scheduled" status to the
        # new confirmed status.
        if old_status in (None, "", "scheduled"):
            new_status = "confirmed"
        else:
            new_status = old_status

        connection.execute(
            sa.text(
                """
                UPDATE appointments
                SET
                    appointment_code = :appointment_code,
                    status = :status,
                    created_at = :created_at,
                    updated_at = :updated_at
                WHERE id = :appointment_id
                """
            ),
            {
                "appointment_code": appointment_code,
                "status": new_status,
                "created_at": current_time,
                "updated_at": current_time,
                "appointment_id": row["id"],
            },
        )

    # SQLite requires batch mode for nullable/type changes.
    with op.batch_alter_table("appointments") as batch_op:
        batch_op.alter_column(
            "appointment_code",
            existing_type=sa.String(length=5),
            nullable=False,
        )

        batch_op.alter_column(
            "created_at",
            existing_type=sa.DateTime(),
            nullable=False,
        )

        batch_op.alter_column(
            "updated_at",
            existing_type=sa.DateTime(),
            nullable=False,
        )

        batch_op.alter_column(
            "customer_name",
            existing_type=sa.String(),
            nullable=True,
        )

        batch_op.alter_column(
            "phone_number",
            existing_type=sa.String(),
            nullable=True,
        )

        batch_op.alter_column(
            "appointment_time",
            existing_type=sa.String(),
            nullable=True,
        )

        batch_op.alter_column(
            "status",
            existing_type=sa.String(),
            nullable=False,
        )

        batch_op.create_index(
            "ix_appointments_appointment_code",
            ["appointment_code"],
            unique=True,
        )

        batch_op.create_index(
            "ix_appointments_appointment_date",
            ["appointment_date"],
            unique=False,
        )

        batch_op.create_index(
            "ix_appointments_phone_number",
            ["phone_number"],
            unique=False,
        )

        batch_op.create_index(
            "ix_appointments_status",
            ["status"],
            unique=False,
        )


def downgrade() -> None:
    connection = op.get_bind()

    # Nullable fields must receive fallback values before
    # restoring the old NOT NULL constraints.
    connection.execute(
        sa.text(
            """
            UPDATE appointments
            SET customer_name = 'Unknown'
            WHERE customer_name IS NULL OR customer_name = ''
            """
        )
    )

    connection.execute(
        sa.text(
            """
            UPDATE appointments
            SET phone_number = '0000000000'
            WHERE phone_number IS NULL OR phone_number = ''
            """
        )
    )

    connection.execute(
        sa.text(
            """
            UPDATE appointments
            SET appointment_time = 'Not specified'
            WHERE appointment_time IS NULL
               OR appointment_time = ''
            """
        )
    )

    connection.execute(
        sa.text(
            """
            UPDATE appointments
            SET status = 'scheduled'
            WHERE status = 'confirmed'
            """
        )
    )

    with op.batch_alter_table("appointments") as batch_op:
        batch_op.drop_index(
            "ix_appointments_status"
        )
        batch_op.drop_index(
            "ix_appointments_phone_number"
        )
        batch_op.drop_index(
            "ix_appointments_appointment_date"
        )
        batch_op.drop_index(
            "ix_appointments_appointment_code"
        )

        batch_op.alter_column(
            "customer_name",
            existing_type=sa.String(),
            nullable=False,
        )

        batch_op.alter_column(
            "phone_number",
            existing_type=sa.String(),
            nullable=False,
        )

        batch_op.alter_column(
            "appointment_time",
            existing_type=sa.String(),
            nullable=False,
        )

        batch_op.alter_column(
            "status",
            existing_type=sa.String(),
            nullable=True,
        )

        batch_op.drop_column("updated_at")
        batch_op.drop_column("created_at")
        batch_op.drop_column("appointment_date")
        batch_op.drop_column("appointment_code")