from pydantic import BaseModel, EmailStr, Field


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=6)


class UserCreate(BaseModel):
    email: EmailStr
    name: str
    password: str = Field(min_length=6)
    role: str = Field(default="user")


class UserOut(BaseModel):
    id: int
    email: EmailStr
    name: str
    role: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut


class PresenceUser(BaseModel):
    id: int
    email: EmailStr
    name: str
    role: str
    connected_at: str
    connections: int
