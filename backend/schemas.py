from datetime import datetime
from typing import Any

from pydantic import BaseModel, EmailStr, Field


class LoginRequest(BaseModel):
    email: str = Field(min_length=3, max_length=255)
    password: str = Field(min_length=6)


class UserCreate(BaseModel):
    email: str = Field(min_length=3, max_length=255)
    name: str = Field(min_length=1, max_length=255)
    password: str = Field(min_length=6)
    role: str = Field(default="user")


class UserOut(BaseModel):
    id: int
    email: str
    name: str
    role: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut


class PresenceUser(BaseModel):
    id: int
    email: str
    name: str
    role: str
    connected_at: str
    connections: int


class ClientCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    code: str = Field(min_length=1, max_length=64)
    description: str | None = Field(default=None, max_length=500)


class ClientOut(BaseModel):
    id: int
    name: str
    code: str
    description: str | None


class ClientAssignmentCreate(BaseModel):
    user_id: int | None = None
    user_email: EmailStr | None = None


class ClientAssignmentOut(BaseModel):
    id: int
    client_id: int
    user_id: int
    created_at: datetime


class ColumnMappingIn(BaseModel):
    excel_column: str = Field(min_length=1, max_length=64)
    field_name: str = Field(min_length=1, max_length=64)
    data_type: str = Field(default="text", max_length=32)


class ColumnMappingOut(BaseModel):
    id: int
    excel_column: str
    field_name: str
    data_type: str


class ExcelFileCreate(BaseModel):
    display_name: str = Field(min_length=1, max_length=255)
    file_path: str = Field(min_length=1, max_length=1024)
    sheet_name: str | None = Field(default=None, max_length=128)
    has_header: bool = True
    mappings: list[ColumnMappingIn]


class ExcelFileOut(BaseModel):
    id: int
    client_id: int
    display_name: str
    file_path: str
    sheet_name: str | None
    has_header: bool
    created_at: datetime
    updated_at: datetime
    mappings: list[ColumnMappingOut] = []


class DataSourceStatus(BaseModel):
    file_id: int
    display_name: str
    file_path: str
    row_count: int
    last_modified: datetime | None
    last_read: datetime | None


class DashboardSeriesPoint(BaseModel):
    label: str
    value: float


class DashboardSummary(BaseModel):
    total_revenue: float
    total_transactions: int
    revenue_today: float
    revenue_by_date: list[DashboardSeriesPoint]
    revenue_by_product: list[DashboardSeriesPoint]
    data_sources: list[DataSourceStatus]


class FilePreview(BaseModel):
    columns: list[str]
    rows: list[list[Any]]


class ReportMetric(BaseModel):
    field: str
    agg: str


class ReportCreate(BaseModel):
    client_id: int
    file_id: int
    name: str = Field(min_length=1, max_length=255)
    date_range_days: int = Field(default=7, ge=1, le=3650)
    group_by: str = Field(min_length=1, max_length=64)
    metrics: list[ReportMetric]
    chart_type: str = Field(default="bar", max_length=32)
    filters: dict[str, Any] = Field(default_factory=dict)


class ReportOut(BaseModel):
    id: int
    client_id: int
    file_id: int
    name: str
    config: dict[str, Any]
    created_by: int
    created_at: datetime


class ReportRunResult(BaseModel):
    rows: list[dict[str, Any]]
