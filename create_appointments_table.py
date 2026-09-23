"""
Database migration & tool registration for Provaani Appointment Management System.
Creates the appointments table in PostgreSQL with indexes and
registers the book_appointment tool in the tools table.
"""

import asyncio
import json
import os
import sys

# Support running inside container or locally
try:
    from api.db import db_client
except ImportError:
    # If running locally outside container, load from patches or fallback
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), "patches"))
    from api.db import db_client

from sqlalchemy import text

BOOK_APPOINTMENT_TOOL_UUID = "c84e1234-5678-4321-9876-abcdef012345"


async def main():
    print("=== 1. Initializing appointments table in PostgreSQL ===")
    async with db_client.async_session() as session:
        # Create appointments table
        await session.execute(
            text("""
                CREATE TABLE IF NOT EXISTS appointments (
                    id SERIAL PRIMARY KEY,
                    organization_id INTEGER NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
                    branch_id VARCHAR(100) NOT NULL,
                    branch_name VARCHAR(255) NOT NULL,
                    patient_name VARCHAR(255) NOT NULL,
                    phone_number VARCHAR(50) NOT NULL,
                    procedure_of_interest VARCHAR(255),
                    appointment_date DATE NOT NULL,
                    appointment_time VARCHAR(20) NOT NULL,
                    time_window VARCHAR(100),
                    booked_by VARCHAR(50) NOT NULL DEFAULT 'voice_agent',
                    status VARCHAR(50) NOT NULL DEFAULT 'confirmed',
                    call_run_id INTEGER NULL,
                    notes TEXT,
                    whatsapp_sent BOOLEAN DEFAULT FALSE,
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
                );
            """)
        )

        # Create indexes separately for asyncpg
        await session.execute(
            text("CREATE INDEX IF NOT EXISTS idx_appointments_org_date ON appointments(organization_id, appointment_date);")
        )
        await session.execute(
            text("CREATE INDEX IF NOT EXISTS idx_appointments_branch ON appointments(organization_id, branch_id, appointment_date);")
        )
        await session.execute(
            text("CREATE INDEX IF NOT EXISTS idx_appointments_phone ON appointments(phone_number);")
        )
        await session.execute(
            text("CREATE INDEX IF NOT EXISTS idx_appointments_status ON appointments(status);")
        )
        print("Appointments table and indexes verified.")

        print("\n=== 2. Ensuring book_appointment tool exists in tools table ===")
        tool_def = {
            "schema_version": 1,
            "type": "http_api",
            "config": {
                "method": "POST",
                "url": "http://api:8000/api/v1/campaign/appointments/book",
                "headers": {
                    "Content-Type": "application/json"
                },
                "parameters": [
                    {
                        "name": "patient_name",
                        "type": "string",
                        "description": "Full name of the patient requesting the consultation.",
                        "required": True
                    },
                    {
                        "name": "phone_number",
                        "type": "string",
                        "description": "Patient's 10-digit mobile number.",
                        "required": True
                    },
                    {
                        "name": "branch_id",
                        "type": "string",
                        "description": "Branch ID where the consultation is requested (e.g. 'durgapur' or 'burdwan').",
                        "required": True
                    },
                    {
                        "name": "appointment_date",
                        "type": "string",
                        "description": "Appointment date in YYYY-MM-DD format.",
                        "required": True
                    },
                    {
                        "name": "appointment_time",
                        "type": "string",
                        "description": "Requested consultation time (e.g. '03:30 PM' or '11:00 AM') within the clinic open hours.",
                        "required": True
                    },
                    {
                        "name": "procedure_of_interest",
                        "type": "string",
                        "description": "The treatment or procedure of interest (e.g. Liposuction, Rhinoplasty, Hair Transplant).",
                        "required": False
                    }
                ],
                "body_template": {
                    "patient_name": "{{ patient_name }}",
                    "phone_number": "{{ phone_number }}",
                    "branch_id": "{{ branch_id }}",
                    "appointment_date": "{{ appointment_date }}",
                    "appointment_time": "{{ appointment_time }}",
                    "procedure_of_interest": "{{ procedure_of_interest }}",
                    "booked_by": "voice_agent"
                },
                "timeout_ms": 10000
            }
        }

        # Check existing tool
        res = await session.execute(
            text("SELECT id, tool_uuid, name FROM tools WHERE name = 'book_appointment' AND organization_id = 1;")
        )
        existing_tool = res.first()

        if existing_tool:
            await session.execute(
                text("UPDATE tools SET definition = :def, description = :desc, status = 'active' WHERE id = :id;"),
                {
                    "def": json.dumps(tool_def),
                    "desc": "Book a patient consultation appointment strictly within the clinic open hours and time chunks.",
                    "id": existing_tool.id
                }
            )
            print(f"Updated existing book_appointment tool (UUID: {existing_tool.tool_uuid}).")
        else:
            await session.execute(
                text("""
                    INSERT INTO tools (tool_uuid, organization_id, name, description, category, status, definition, created_by, created_at, updated_at)
                    VALUES (:uuid, 1, 'book_appointment', 'Book a patient consultation appointment strictly within the clinic open hours and time chunks.', 'http_api', 'active', :def, 1, NOW(), NOW());
                """),
                {
                    "uuid": BOOK_APPOINTMENT_TOOL_UUID,
                    "def": json.dumps(tool_def)
                }
            )
            print(f"Created new book_appointment tool (UUID: {BOOK_APPOINTMENT_TOOL_UUID}).")

        await session.commit()
    print("Database initialization completed successfully.")


if __name__ == "__main__":
    asyncio.run(main())
