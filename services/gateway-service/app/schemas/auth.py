"""Contratos publicos de autenticacao e sessao (RF26)."""

from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class LoginRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    email: EmailStr
    password: str = Field(min_length=1, max_length=72)


class OperatorInfo(BaseModel):
    id: UUID
    name: str
    email: EmailStr
    role: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    operator: OperatorInfo


class SessionResponse(BaseModel):
    active: bool = True
    operator: OperatorInfo


class ErrorBody(BaseModel):
    code: str
    message: str
    details: dict[str, object] | None = None
    request_id: str | None = None


class ErrorResponse(BaseModel):
    error: ErrorBody
