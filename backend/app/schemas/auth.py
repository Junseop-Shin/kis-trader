from pydantic import BaseModel, EmailStr, Field


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    name: str = Field(min_length=1, max_length=100)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str
    totp_code: str | None = None


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class RefreshRequest(BaseModel):
    refresh_token: str


class TOTPSetupResponse(BaseModel):
    qr_code_base64: str


class TOTPVerifyRequest(BaseModel):
    code: str


class UserResponse(BaseModel):
    id: int
    email: str
    name: str
    role: str
    totp_enabled: bool
    is_active: bool

    model_config = {"from_attributes": True}


class MessageResponse(BaseModel):
    message: str
