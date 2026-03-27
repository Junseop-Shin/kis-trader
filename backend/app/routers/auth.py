from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from ..config import Settings, get_settings
from ..database import get_db
from ..deps import get_current_user
from ..models.user import User
from ..schemas.auth import (
    LoginRequest,
    MessageResponse,
    RefreshRequest,
    RegisterRequest,
    TokenResponse,
    TOTPSetupResponse,
    TOTPVerifyRequest,
    UserResponse,
)
from ..services.auth_service import (
    authenticate_user,
    refresh_tokens,
    register_user,
    revoke_refresh_token,
    setup_totp,
    verify_totp,
)

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register(req: RegisterRequest, db: AsyncSession = Depends(get_db)):
    try:
        user = await register_user(req.email, req.password, req.name, db)
        return user
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post("/login", response_model=TokenResponse)
async def login(
    req: LoginRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
    settings: Settings = Depends(get_settings),
):
    ip_address = request.client.host if request.client else None
    try:
        tokens = await authenticate_user(
            req.email, req.password, req.totp_code, ip_address, db, settings
        )
        return tokens
    except ValueError as e:
        error_msg = str(e)
        if error_msg == "ACCOUNT_LOCKED":
            raise HTTPException(
                status_code=status.HTTP_423_LOCKED,
                detail="Account locked due to too many failed login attempts. Contact admin.",
            )
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=error_msg)


@router.post("/refresh", response_model=TokenResponse)
async def refresh(
    req: RefreshRequest,
    db: AsyncSession = Depends(get_db),
    settings: Settings = Depends(get_settings),
):
    try:
        tokens = await refresh_tokens(req.refresh_token, db, settings)
        return tokens
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(e))


@router.post("/logout", response_model=MessageResponse)
async def logout(req: RefreshRequest, db: AsyncSession = Depends(get_db)):
    await revoke_refresh_token(req.refresh_token, db)
    return {"message": "Logged out successfully"}


@router.get("/me", response_model=UserResponse)
async def me(current_user: User = Depends(get_current_user)):
    return current_user


@router.post("/totp/setup", response_model=TOTPSetupResponse)
async def totp_setup(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if current_user.totp_enabled:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="TOTP already enabled"
        )
    result = await setup_totp(current_user, db)
    return result


@router.post("/totp/verify", response_model=MessageResponse)
async def totp_verify(
    req: TOTPVerifyRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    try:
        success = await verify_totp(current_user, req.code, db)
        if not success:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid TOTP code"
            )
        return {"message": "TOTP enabled successfully"}
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
