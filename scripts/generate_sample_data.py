from __future__ import annotations

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


def main() -> None:
    root_env = os.getenv("DATA_ROOT")
    if root_env:
        root = Path(root_env)
    else:
        root = Path(__file__).resolve().parents[1] / "data" / "network_share"
    write_sales_file(root / "clients" / "acme_corporation" / "sales_2026.xlsx")
    write_customers_file(root / "clients" / "acme_corporation" / "customers.xlsx")
    write_sales_file(root / "clients" / "beta_limited" / "sales_q1.xlsx")
    write_templates(root)


if __name__ == "__main__":
    main()
