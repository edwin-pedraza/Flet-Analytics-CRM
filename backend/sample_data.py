from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.excel_reader import resolve_data_path
from backend.models import Client, ColumnMapping, ExcelFile


SALES_MAPPINGS: list[dict[str, str]] = [
    {"excel_column": "Date", "field_name": "date", "data_type": "date"},
    {"excel_column": "Product", "field_name": "product", "data_type": "text"},
    {"excel_column": "Quantity", "field_name": "quantity", "data_type": "number"},
    {"excel_column": "Revenue", "field_name": "revenue", "data_type": "number"},
    {"excel_column": "Region", "field_name": "region", "data_type": "text"},
    {"excel_column": "Salesperson", "field_name": "salesperson", "data_type": "text"},
]

SAMPLE_CLIENTS: list[dict[str, Any]] = [
    {
        "name": "Acme Corporation",
        "code": "acme_corporation",
        "description": "Sample client - Acme Corporation",
    },
    {
        "name": "Beta Limited",
        "code": "beta_limited",
        "description": "Sample client - Beta Limited",
    },
]

SAMPLE_FILES: list[dict[str, Any]] = [
    {
        "client_code": "acme_corporation",
        "display_name": "Sales 2026",
        "file_path": "clients/acme_corporation/sales_2026.xlsx",
        "sheet_name": "Sales",
        "has_header": True,
        "mappings": SALES_MAPPINGS,
    },
    {
        "client_code": "beta_limited",
        "display_name": "Sales Q1",
        "file_path": "clients/beta_limited/sales_q1.xlsx",
        "sheet_name": "Sales",
        "has_header": True,
        "mappings": SALES_MAPPINGS,
    },
]


async def _ensure_clients(session: AsyncSession) -> dict[str, Client]:
    clients_by_code: dict[str, Client] = {}
    for client_data in SAMPLE_CLIENTS:
        result = await session.execute(
            select(Client).where(Client.code == client_data["code"])
        )
        client = result.scalar_one_or_none()
        if not client:
            client = Client(**client_data)
            session.add(client)
            await session.flush()
        clients_by_code[client.code] = client
    return clients_by_code


async def _ensure_excel_files(
    session: AsyncSession, clients_by_code: dict[str, Client]
) -> None:
    for file_spec in SAMPLE_FILES:
        client = clients_by_code.get(file_spec["client_code"])
        if not client:
            continue
        path = resolve_data_path(file_spec["file_path"])
        if not path.exists():
            continue
        result = await session.execute(
            select(ExcelFile).where(
                ExcelFile.client_id == client.id,
                ExcelFile.file_path == file_spec["file_path"],
            )
        )
        file_row = result.scalar_one_or_none()
        if not file_row:
            file_row = ExcelFile(
                client_id=client.id,
                display_name=file_spec["display_name"],
                file_path=file_spec["file_path"],
                sheet_name=file_spec["sheet_name"],
                has_header=file_spec["has_header"],
                updated_at=datetime.utcnow(),
            )
            session.add(file_row)
            await session.flush()
        else:
            changed = False
            if file_row.display_name != file_spec["display_name"]:
                file_row.display_name = file_spec["display_name"]
                changed = True
            if file_row.sheet_name != file_spec["sheet_name"]:
                file_row.sheet_name = file_spec["sheet_name"]
                changed = True
            if file_row.has_header != file_spec["has_header"]:
                file_row.has_header = file_spec["has_header"]
                changed = True
            if changed:
                file_row.updated_at = datetime.utcnow()

        result = await session.execute(
            select(ColumnMapping).where(ColumnMapping.file_id == file_row.id)
        )
        existing = {
            (mapping.excel_column, mapping.field_name, mapping.data_type)
            for mapping in result.scalars().all()
        }
        new_mappings = []
        for mapping in file_spec["mappings"]:
            key = (mapping["excel_column"], mapping["field_name"], mapping["data_type"])
            if key in existing:
                continue
            new_mappings.append(
                ColumnMapping(
                    file_id=file_row.id,
                    excel_column=mapping["excel_column"],
                    field_name=mapping["field_name"],
                    data_type=mapping["data_type"],
                )
            )
        if new_mappings:
            session.add_all(new_mappings)


async def seed_sample_data(session: AsyncSession) -> None:
    clients_by_code = await _ensure_clients(session)
    await _ensure_excel_files(session, clients_by_code)
    await session.commit()
