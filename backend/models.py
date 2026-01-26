from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, JSON, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from backend.db import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(255))
    password_hash: Mapped[str] = mapped_column(String(255))
    role: Mapped[str] = mapped_column(String(50), default="user")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class Session(Base):
    __tablename__ = "sessions"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    ip: Mapped[str] = mapped_column(String(64))
    user_agent: Mapped[str | None] = mapped_column(String(255), nullable=True)
    connected_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    disconnected_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)


class PresenceEvent(Base):
    __tablename__ = "presence_events"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    event_type: Mapped[str] = mapped_column(String(32))
    ip: Mapped[str] = mapped_column(String(64))
    user_agent: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class Client(Base):
    __tablename__ = "clients"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(255))
    code: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    description: Mapped[str | None] = mapped_column(String(500), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class ClientAssignment(Base):
    __tablename__ = "client_assignments"
    __table_args__ = (UniqueConstraint("client_id", "user_id", name="uq_client_user"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    client_id: Mapped[int] = mapped_column(ForeignKey("clients.id"))
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class ExcelFile(Base):
    __tablename__ = "excel_files"

    id: Mapped[int] = mapped_column(primary_key=True)
    client_id: Mapped[int] = mapped_column(ForeignKey("clients.id"))
    display_name: Mapped[str] = mapped_column(String(255))
    file_path: Mapped[str] = mapped_column(String(1024))
    sheet_name: Mapped[str | None] = mapped_column(String(128), nullable=True)
    has_header: Mapped[bool] = mapped_column(default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class ColumnMapping(Base):
    __tablename__ = "column_mappings"

    id: Mapped[int] = mapped_column(primary_key=True)
    file_id: Mapped[int] = mapped_column(ForeignKey("excel_files.id"))
    excel_column: Mapped[str] = mapped_column(String(64))
    field_name: Mapped[str] = mapped_column(String(64))
    data_type: Mapped[str] = mapped_column(String(32), default="text")


class ReportConfig(Base):
    __tablename__ = "report_configs"

    id: Mapped[int] = mapped_column(primary_key=True)
    client_id: Mapped[int] = mapped_column(ForeignKey("clients.id"))
    file_id: Mapped[int] = mapped_column(ForeignKey("excel_files.id"))
    name: Mapped[str] = mapped_column(String(255))
    config: Mapped[dict] = mapped_column(JSON)
    created_by: Mapped[int] = mapped_column(ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
