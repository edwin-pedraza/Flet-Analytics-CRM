from __future__ import annotations

import asyncio
import os
from datetime import datetime, timedelta
from pathlib import Path

from openpyxl import Workbook


def write_sales_file(path: Path) -> None:
    workbook = Workbook()
    sheet = workbook.active
    sheet.title = "Sales"
    sheet.append(["Date", "Product", "Quantity", "Revenue", "Region", "Salesperson"])
    today = datetime.now().date()
    rows = [
        (today - timedelta(days=3), "Widget A", 120, 3600, "North", "Sarah"),
        (today - timedelta(days=3), "Widget B", 80, 2800, "South", "John"),
        (today - timedelta(days=2), "Widget A", 150, 4500, "North", "Sarah"),
        (today - timedelta(days=2), "Widget C", 60, 2100, "East", "Maria"),
        (today - timedelta(days=1), "Widget B", 200, 7000, "South", "John"),
        (today - timedelta(days=1), "Widget C", 90, 3150, "West", "Ava"),
        (today, "Widget A", 140, 4200, "North", "Sarah"),
        (today, "Widget B", 110, 3850, "East", "Bob"),
        (today, "Widget C", 70, 2450, "West", "Ava"),
    ]
    for row in rows:
        sheet.append(list(row))
    path.parent.mkdir(parents=True, exist_ok=True)
    workbook.save(path)


def write_customers_file(path: Path) -> None:
    workbook = Workbook()
    sheet = workbook.active
    sheet.title = "Customers"
    sheet.append(["Customer", "SignupDate", "Region", "Owner"])
    today = datetime.now().date()
    rows = [
        ("Acme Retail", today - timedelta(days=120), "North", "Sarah"),
        ("Beta Wholesale", today - timedelta(days=60), "South", "John"),
        ("Gamma Labs", today - timedelta(days=30), "East", "Maria"),
        ("Delta Foods", today - timedelta(days=10), "West", "Ava"),
    ]
    for row in rows:
        sheet.append(list(row))
    path.parent.mkdir(parents=True, exist_ok=True)
    workbook.save(path)


def write_templates(root: Path) -> None:
    templates = root / "templates"
    templates.mkdir(parents=True, exist_ok=True)
    sales_template = templates / "sales_template.xlsx"
    customers_template = templates / "customer_template.xlsx"
    if not sales_template.exists():
        write_sales_file(sales_template)
    if not customers_template.exists():
        write_customers_file(customers_template)


async def create_sample_clients() -> None:
    """Create sample client and file records in the database."""
    import sys
    app_path = Path(__file__).resolve().parents[1]
    if str(app_path) not in sys.path:
        sys.path.insert(0, str(app_path))

    try:
        from backend.db import SessionLocal, init_db
        from backend.sample_data import seed_sample_data
    except ImportError as e:
        print(f"Warning: Could not import database modules: {e}")
        print("Skipping database sample seeding")
        return

    await init_db()

    async with SessionLocal() as session:
        await seed_sample_data(session)


def main() -> None:
    root_env = os.getenv("DATA_ROOT")
    if root_env:
        root = Path(root_env)
    else:
        root = Path(__file__).resolve().parents[1] / "data" / "network_share"

    print("Generating sample Excel files (only if they don't exist)...")

    # Only create files if they don't exist - preserves user modifications
    acme_sales = root / "clients" / "acme_corporation" / "sales_2026.xlsx"
    if not acme_sales.exists():
        write_sales_file(acme_sales)
        print(f"  Created: {acme_sales}")
    else:
        print(f"  Skipped (exists): {acme_sales}")

    acme_customers = root / "clients" / "acme_corporation" / "customers.xlsx"
    if not acme_customers.exists():
        write_customers_file(acme_customers)
        print(f"  Created: {acme_customers}")
    else:
        print(f"  Skipped (exists): {acme_customers}")

    beta_sales = root / "clients" / "beta_limited" / "sales_q1.xlsx"
    if not beta_sales.exists():
        write_sales_file(beta_sales)
        print(f"  Created: {beta_sales}")
    else:
        print(f"  Skipped (exists): {beta_sales}")

    write_templates(root)
    print("Excel files check completed")

    print("\nCreating database records...")
    asyncio.run(create_sample_clients())
    print("Sample data generation completed!")


if __name__ == "__main__":
    main()
