import ipaddress
from datetime import datetime

from fastapi import Depends, FastAPI, HTTPException, Query, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.auth import create_access_token, hash_password, token_user_id, verify_password
from backend.db import SessionLocal, get_session, init_db
from backend.models import PresenceEvent, Session, User
from backend.presence import PresenceManager
from backend.schemas import LoginRequest, TokenResponse, UserCreate, UserOut
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

        await presence_manager.connect(
            websocket,
            {"id": user.id, "email": user.email, "name": user.name, "role": user.role},
            session_row.connected_at,
        )

        try:
            while True:
                await websocket.receive_text()
        except WebSocketDisconnect:
            pass
        finally:
            await presence_manager.disconnect(websocket)
            session_row.disconnected_at = datetime.utcnow()
            session.add(session_row)
            session.add(
                PresenceEvent(
                    user_id=user.id,
                    event_type="disconnect",
                    ip=client_ip,
                    user_agent=user_agent,
                )
            )
            await session.commit()
