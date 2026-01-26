import ipaddress
from collections import defaultdict
from datetime import datetime, timedelta
from typing import Any

from fastapi import Depends, FastAPI, HTTPException, Query, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.auth import create_access_token, hash_password, token_user_id, verify_password
from backend.db import SessionLocal, get_session, init_db
from backend.excel_reader import excel_cache, map_rows, resolve_data_path
from backend.models import (
    Client,
    ClientAssignment,
    ColumnMapping,
    ExcelFile,
    PresenceEvent,
    ReportConfig,
    Session,
    User,
)
from backend.presence import PresenceManager
from backend.schemas import (
    ClientAssignmentCreate,
    ClientAssignmentOut,
    ClientCreate,
    ClientOut,
    ColumnMappingOut,
    DashboardSeriesPoint,
    DashboardSummary,
    DataSourceStatus,
    ExcelFileCreate,
    ExcelFileOut,
    FilePreview,
    LoginRequest,
    ReportCreate,
    ReportOut,
    ReportRunResult,
    TokenResponse,
    UserCreate,
    UserOut,
)
from backend.settings import get_settings


settings = get_settings()
presence_manager = PresenceManager()
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")


def _allowed_networks() -> list[ipaddress._BaseNetwork]:
    networks: list[ipaddress._BaseNetwork] = []
    for raw in settings.allowed_subnets.split(","):
        raw = raw.strip()
        if not raw:
            continue
        try:
            networks.append(ipaddress.ip_network(raw, strict=False))
        except ValueError:
            continue
    return networks


ALLOWED_NETWORKS = _allowed_networks()


def is_allowed_ip(ip: str) -> bool:
    try:
        ip_addr = ipaddress.ip_address(ip)
    except ValueError:
        return False
    return any(ip_addr in net for net in ALLOWED_NETWORKS)


async def get_current_user(
    token: str = Depends(oauth2_scheme),
    session: AsyncSession = Depends(get_session),
) -> User:
    user_id = token_user_id(token)
    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid token")
    result = await session.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=401, detail="User not found")
    return user


async def require_admin(user: User = Depends(get_current_user)) -> User:
    if user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    return user


async def get_client_or_404(client_id: int, session: AsyncSession) -> Client:
    result = await session.execute(select(Client).where(Client.id == client_id))
    client = result.scalar_one_or_none()
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")
    return client


async def require_client_access(
    client_id: int,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> Client:
    client = await get_client_or_404(client_id, session)
    if user.role == "admin":
        return client
    assignment = await session.execute(
        select(ClientAssignment).where(
            ClientAssignment.client_id == client_id,
            ClientAssignment.user_id == user.id,
        )
    )
    if not assignment.scalar_one_or_none():
        raise HTTPException(status_code=403, detail="Client access required")
    return client


async def get_file_or_404(file_id: int, session: AsyncSession) -> ExcelFile:
    result = await session.execute(select(ExcelFile).where(ExcelFile.id == file_id))
    file_row = result.scalar_one_or_none()
    if not file_row:
        raise HTTPException(status_code=404, detail="Excel file not found")
    return file_row


async def require_file_access(
    file_id: int,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> ExcelFile:
    file_row = await get_file_or_404(file_id, session)
    await require_client_access(file_row.client_id, user, session)
    return file_row


async def list_mappings(session: AsyncSession, file_id: int) -> list[ColumnMapping]:
    result = await session.execute(
        select(ColumnMapping).where(ColumnMapping.file_id == file_id)
    )
    return result.scalars().all()


app = FastAPI(title="CRM Analytics API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.cors_origins] if settings.cors_origins != "*" else ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def lan_only_middleware(request, call_next):
    if settings.enforce_lan_only:
        client_ip = request.client.host if request.client else ""
        if not is_allowed_ip(client_ip):
            return JSONResponse(status_code=403, content={"detail": "LAN access only"})
    return await call_next(request)


@app.on_event("startup")
async def startup() -> None:
    await init_db()
    await bootstrap_admin()
    await bootstrap_sample_clients()


async def bootstrap_admin() -> None:
    if not settings.bootstrap_admin_email or not settings.bootstrap_admin_password:
        return
    async with SessionLocal() as session:
        result = await session.execute(select(User).limit(1))
        if result.scalar_one_or_none():
            return
        admin = User(
            email=settings.bootstrap_admin_email,
            name="Admin",
            password_hash=hash_password(settings.bootstrap_admin_password),
            role="admin",
        )
        session.add(admin)
        await session.commit()


async def bootstrap_sample_clients() -> None:
    """Create sample client and Excel file records that match the generated data."""
    import os
    if os.getenv("GENERATE_SAMPLE_DATA", "1") != "1":
        return

    from backend.sample_data import seed_sample_data

    async with SessionLocal() as session:
        await seed_sample_data(session)


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/auth/login", response_model=TokenResponse)
async def login(payload: LoginRequest, session: AsyncSession = Depends(get_session)) -> TokenResponse:
    result = await session.execute(select(User).where(User.email == payload.email))
    user = result.scalar_one_or_none()
    if not user or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    token = create_access_token({"sub": str(user.id), "role": user.role})
    return TokenResponse(
        access_token=token,
        user=UserOut(id=user.id, email=user.email, name=user.name, role=user.role),
    )


@app.get("/me", response_model=UserOut)
async def me(user: User = Depends(get_current_user)) -> UserOut:
    return UserOut(id=user.id, email=user.email, name=user.name, role=user.role)


@app.get("/users", response_model=list[UserOut])
async def list_users(
    session: AsyncSession = Depends(get_session),
    _: User = Depends(require_admin),
) -> list[UserOut]:
    result = await session.execute(select(User))
    return [
        UserOut(id=u.id, email=u.email, name=u.name, role=u.role)
        for u in result.scalars().all()
    ]


@app.post("/users", response_model=UserOut)
async def create_user(
    payload: UserCreate,
    session: AsyncSession = Depends(get_session),
    _: User = Depends(require_admin),
) -> UserOut:
    existing = await session.execute(select(User).where(User.email == payload.email))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Email already exists")
    user = User(
        email=payload.email,
        name=payload.name,
        password_hash=hash_password(payload.password),
        role=payload.role,
    )
    session.add(user)
    await session.commit()
    await session.refresh(user)
    return UserOut(id=user.id, email=user.email, name=user.name, role=user.role)


@app.post("/clients", response_model=ClientOut)
async def create_client(
    payload: ClientCreate,
    session: AsyncSession = Depends(get_session),
    _: User = Depends(require_admin),
) -> ClientOut:
    existing = await session.execute(select(Client).where(Client.code == payload.code))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Client code already exists")
    client = Client(name=payload.name, code=payload.code, description=payload.description)
    session.add(client)
    await session.commit()
    await session.refresh(client)
    return ClientOut(
        id=client.id, name=client.name, code=client.code, description=client.description
    )


@app.get("/clients", response_model=list[ClientOut])
async def list_clients(
    session: AsyncSession = Depends(get_session),
    _: User = Depends(require_admin),
) -> list[ClientOut]:
    result = await session.execute(select(Client))
    return [
        ClientOut(id=c.id, name=c.name, code=c.code, description=c.description)
        for c in result.scalars().all()
    ]


@app.get("/clients/mine", response_model=list[ClientOut])
async def list_my_clients(
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
) -> list[ClientOut]:
    if user.role == "admin":
        result = await session.execute(select(Client))
        return [
            ClientOut(id=c.id, name=c.name, code=c.code, description=c.description)
            for c in result.scalars().all()
        ]
    result = await session.execute(
        select(Client)
        .join(ClientAssignment, ClientAssignment.client_id == Client.id)
        .where(ClientAssignment.user_id == user.id)
    )
    return [
        ClientOut(id=c.id, name=c.name, code=c.code, description=c.description)
        for c in result.scalars().all()
    ]


@app.post("/clients/{client_id}/assign", response_model=ClientAssignmentOut)
async def assign_client(
    client_id: int,
    payload: ClientAssignmentCreate,
    session: AsyncSession = Depends(get_session),
    _: User = Depends(require_admin),
) -> ClientAssignmentOut:
    await get_client_or_404(client_id, session)
    if not payload.user_id and not payload.user_email:
        raise HTTPException(status_code=400, detail="Provide user_id or user_email")
    if payload.user_id:
        result = await session.execute(select(User).where(User.id == payload.user_id))
    else:
        result = await session.execute(select(User).where(User.email == payload.user_email))
    target_user = result.scalar_one_or_none()
    if not target_user:
        raise HTTPException(status_code=404, detail="User not found")
    existing = await session.execute(
        select(ClientAssignment).where(
            ClientAssignment.client_id == client_id,
            ClientAssignment.user_id == target_user.id,
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="User already assigned")
    assignment = ClientAssignment(client_id=client_id, user_id=target_user.id)
    session.add(assignment)
    await session.commit()
    await session.refresh(assignment)
    return ClientAssignmentOut(
        id=assignment.id,
        client_id=assignment.client_id,
        user_id=assignment.user_id,
        created_at=assignment.created_at,
    )


@app.delete("/clients/{client_id}/assign/{user_id}")
async def unassign_client(
    client_id: int,
    user_id: int,
    session: AsyncSession = Depends(get_session),
    _: User = Depends(require_admin),
) -> dict[str, str]:
    await get_client_or_404(client_id, session)
    await session.execute(
        delete(ClientAssignment).where(
            ClientAssignment.client_id == client_id,
            ClientAssignment.user_id == user_id,
        )
    )
    await session.commit()
    return {"status": "ok"}


@app.post("/clients/{client_id}/files", response_model=ExcelFileOut)
async def register_file(
    client_id: int,
    payload: ExcelFileCreate,
    session: AsyncSession = Depends(get_session),
    _: User = Depends(require_admin),
) -> ExcelFileOut:
    await get_client_or_404(client_id, session)
    path = resolve_data_path(payload.file_path)
    if not path.exists():
        raise HTTPException(status_code=400, detail="File path does not exist")
    file_row = ExcelFile(
        client_id=client_id,
        display_name=payload.display_name,
        file_path=payload.file_path,
        sheet_name=payload.sheet_name,
        has_header=payload.has_header,
        updated_at=datetime.utcnow(),
    )
    session.add(file_row)
    await session.flush()
    mappings = []
    for mapping in payload.mappings:
        mappings.append(
            ColumnMapping(
                file_id=file_row.id,
                excel_column=mapping.excel_column,
                field_name=mapping.field_name,
                data_type=mapping.data_type,
            )
        )
    session.add_all(mappings)
    await session.commit()
    await session.refresh(file_row)
    return ExcelFileOut(
        id=file_row.id,
        client_id=file_row.client_id,
        display_name=file_row.display_name,
        file_path=file_row.file_path,
        sheet_name=file_row.sheet_name,
        has_header=file_row.has_header,
        created_at=file_row.created_at,
        updated_at=file_row.updated_at,
        mappings=[
            ColumnMappingOut(
                id=m.id,
                excel_column=m.excel_column,
                field_name=m.field_name,
                data_type=m.data_type,
            )
            for m in mappings
        ],
    )


@app.get("/clients/{client_id}/files", response_model=list[ExcelFileOut])
async def list_files(
    client: Client = Depends(require_client_access),
    session: AsyncSession = Depends(get_session),
) -> list[ExcelFileOut]:
    result = await session.execute(
        select(ExcelFile).where(ExcelFile.client_id == client.id)
    )
    files = result.scalars().all()
    payload = []
    for file_row in files:
        mappings = await list_mappings(session, file_row.id)
        payload.append(
            ExcelFileOut(
                id=file_row.id,
                client_id=file_row.client_id,
                display_name=file_row.display_name,
                file_path=file_row.file_path,
                sheet_name=file_row.sheet_name,
                has_header=file_row.has_header,
                created_at=file_row.created_at,
                updated_at=file_row.updated_at,
                mappings=[
                    ColumnMappingOut(
                        id=m.id,
                        excel_column=m.excel_column,
                        field_name=m.field_name,
                        data_type=m.data_type,
                    )
                    for m in mappings
                ],
            )
        )
    return payload


@app.get("/files/{file_id}/preview", response_model=FilePreview)
async def preview_file(
    file_row: ExcelFile = Depends(require_file_access),
    session: AsyncSession = Depends(get_session),
    limit: int = Query(default=25, ge=1, le=200),
) -> FilePreview:
    path = resolve_data_path(file_row.file_path)
    if not path.exists():
        raise HTTPException(status_code=404, detail="File not found")
    entry = await excel_cache.get_rows(path, file_row.sheet_name, file_row.has_header)
    rows = [
        [row.get(col) for col in entry.columns]
        for row in entry.rows[:limit]
    ]
    return FilePreview(columns=entry.columns, rows=rows)


@app.get("/clients/{client_id}/dashboard", response_model=DashboardSummary)
async def dashboard_summary(
    client: Client = Depends(require_client_access),
    session: AsyncSession = Depends(get_session),
    force: bool = Query(default=False),
) -> DashboardSummary:
    result = await session.execute(
        select(ExcelFile).where(ExcelFile.client_id == client.id)
    )
    files = result.scalars().all()
    now = datetime.now()
    today = now.date()
    total_revenue = 0.0
    total_transactions = 0
    revenue_today = 0.0
    revenue_by_date: dict[str, float] = defaultdict(float)
    revenue_by_product: dict[str, float] = defaultdict(float)
    data_sources: list[DataSourceStatus] = []

    for file_row in files:
        mappings = await list_mappings(session, file_row.id)
        mapping_payload = [
            {"excel_column": m.excel_column, "field_name": m.field_name, "data_type": m.data_type}
            for m in mappings
        ]
        path = resolve_data_path(file_row.file_path)
        if not path.exists():
            continue
        entry = await excel_cache.get_rows(
            path, file_row.sheet_name, file_row.has_header, force=force
        )
        normalized = map_rows(entry.rows, entry.columns, mapping_payload)
        row_count = len(entry.rows)
        total_transactions += row_count
        for row in normalized:
            revenue = row.get("revenue")
            if revenue is not None:
                total_revenue += float(revenue)
                date_value = row.get("date")
                if date_value and date_value.date() == today:
                    revenue_today += float(revenue)
                if date_value:
                    label = date_value.date().isoformat()
                    revenue_by_date[label] += float(revenue)
            product = row.get("product")
            if product and revenue is not None:
                revenue_by_product[str(product)] += float(revenue)
        data_sources.append(
            DataSourceStatus(
                file_id=file_row.id,
                display_name=file_row.display_name,
                file_path=file_row.file_path,
                row_count=row_count,
                last_modified=datetime.fromtimestamp(entry.mtime),
                last_read=now,
            )
        )

    revenue_by_date_points = [
        DashboardSeriesPoint(label=label, value=value)
        for label, value in sorted(revenue_by_date.items())
    ]
    revenue_by_product_points = [
        DashboardSeriesPoint(label=label, value=value)
        for label, value in sorted(revenue_by_product.items(), key=lambda x: x[1], reverse=True)[:10]
    ]

    return DashboardSummary(
        total_revenue=round(total_revenue, 2),
        total_transactions=total_transactions,
        revenue_today=round(revenue_today, 2),
        revenue_by_date=revenue_by_date_points,
        revenue_by_product=revenue_by_product_points,
        data_sources=data_sources,
    )


@app.post("/reports", response_model=ReportOut)
async def create_report(
    payload: ReportCreate,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
) -> ReportOut:
    await require_client_access(payload.client_id, user, session)
    file_row = await get_file_or_404(payload.file_id, session)
    if file_row.client_id != payload.client_id:
        raise HTTPException(status_code=400, detail="File does not belong to client")
    config = {
        "date_range_days": payload.date_range_days,
        "group_by": payload.group_by,
        "metrics": [metric.model_dump() for metric in payload.metrics],
        "chart_type": payload.chart_type,
        "filters": payload.filters,
    }
    report = ReportConfig(
        client_id=payload.client_id,
        file_id=payload.file_id,
        name=payload.name,
        config=config,
        created_by=user.id,
    )
    session.add(report)
    await session.commit()
    await session.refresh(report)
    return ReportOut(
        id=report.id,
        client_id=report.client_id,
        file_id=report.file_id,
        name=report.name,
        config=report.config,
        created_by=report.created_by,
        created_at=report.created_at,
    )


@app.get("/reports", response_model=list[ReportOut])
async def list_reports(
    client_id: int | None = None,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
) -> list[ReportOut]:
    query = select(ReportConfig)
    if client_id is not None:
        await require_client_access(client_id, user, session)
        query = query.where(ReportConfig.client_id == client_id)
    elif user.role != "admin":
        query = query.where(ReportConfig.created_by == user.id)
    result = await session.execute(query)
    return [
        ReportOut(
            id=r.id,
            client_id=r.client_id,
            file_id=r.file_id,
            name=r.name,
            config=r.config,
            created_by=r.created_by,
            created_at=r.created_at,
        )
        for r in result.scalars().all()
    ]


@app.get("/reports/{report_id}/run", response_model=ReportRunResult)
async def run_report(
    report_id: int,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
) -> ReportRunResult:
    result = await session.execute(select(ReportConfig).where(ReportConfig.id == report_id))
    report = result.scalar_one_or_none()
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")
    await require_client_access(report.client_id, user, session)
    file_row = await get_file_or_404(report.file_id, session)
    mappings = await list_mappings(session, file_row.id)
    mapping_payload = [
        {"excel_column": m.excel_column, "field_name": m.field_name, "data_type": m.data_type}
        for m in mappings
    ]
    path = resolve_data_path(file_row.file_path)
    if not path.exists():
        raise HTTPException(status_code=404, detail="File not found")
    entry = await excel_cache.get_rows(path, file_row.sheet_name, file_row.has_header)
    normalized = map_rows(entry.rows, entry.columns, mapping_payload)
    config = report.config
    group_by = config.get("group_by")
    metrics = config.get("metrics", [])
    date_range_days = int(config.get("date_range_days", 7))
    filters = config.get("filters", {})
    cutoff = datetime.now() - timedelta(days=date_range_days)

    groups: dict[str, dict[str, Any]] = {}
    for row in normalized:
        date_value = row.get("date")
        if date_value and date_value < cutoff:
            continue
        skip = False
        for key, expected in filters.items():
            if expected is None:
                continue
            if row.get(key) != expected:
                skip = True
                break
        if skip:
            continue
        group_value = row.get(group_by)
        if group_value is None:
            continue
        group_key = str(group_value)
        bucket = groups.setdefault(group_key, {"group": group_key})
        for metric in metrics:
            field = metric.get("field")
            agg = metric.get("agg")
            metric_key = f"{field}_{agg}"
            if agg == "sum":
                bucket[metric_key] = bucket.get(metric_key, 0.0) + float(row.get(field) or 0.0)
            elif agg == "count":
                bucket[metric_key] = bucket.get(metric_key, 0) + 1

    rows = list(groups.values())
    return ReportRunResult(rows=rows)


@app.get("/presence")
async def presence_snapshot(user: User = Depends(get_current_user)) -> dict:
    return {"users": await presence_manager.snapshot()}


@app.websocket("/ws/presence")
async def presence_ws(
    websocket: WebSocket,
    token: str = Query(default=""),
) -> None:
    client_ip = websocket.client.host if websocket.client else ""
    if settings.enforce_lan_only and not is_allowed_ip(client_ip):
        await websocket.close(code=1008)
        return

    user_id = token_user_id(token)
    if not user_id:
        await websocket.close(code=1008)
        return

    session_id: int | None = None
    user_agent: str | None = None
    user_payload: dict | None = None
    connected_at: datetime | None = None

    async with SessionLocal() as session:
        result = await session.execute(select(User).where(User.id == user_id))
        user = result.scalar_one_or_none()
        if not user:
            await websocket.close(code=1008)
            return

        await websocket.accept()
        user_agent = websocket.headers.get("user-agent")
        session_row = Session(
            user_id=user.id,
            ip=client_ip,
            user_agent=user_agent,
            connected_at=datetime.utcnow(),
        )
        session.add(session_row)
        session.add(
            PresenceEvent(
                user_id=user.id,
                event_type="connect",
                ip=client_ip,
                user_agent=user_agent,
            )
        )
        await session.commit()
        await session.refresh(session_row)

        session_id = session_row.id
        connected_at = session_row.connected_at
        user_payload = {"id": user.id, "email": user.email, "name": user.name, "role": user.role}

    if not user_payload or not connected_at:
        await websocket.close(code=1011)
        return

    await presence_manager.connect(websocket, user_payload, connected_at)

    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        pass
    finally:
        await presence_manager.disconnect(websocket)
        if session_id is None:
            return
        async with SessionLocal() as session:
            result = await session.execute(select(Session).where(Session.id == session_id))
            session_row = result.scalar_one_or_none()
            if session_row:
                session_row.disconnected_at = datetime.utcnow()
                session.add(session_row)
            session.add(
                PresenceEvent(
                    user_id=user_id,
                    event_type="disconnect",
                    ip=client_ip,
                    user_agent=user_agent,
                )
            )
            await session.commit()
