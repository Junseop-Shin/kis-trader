import base64
import io
import secrets
from datetime import datetime, timedelta, timezone

import pyotp
import qrcode
from jose import jwt
from passlib.context import CryptContext
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from ..config import Settings
from ..models.user import User, UserRole, RefreshToken

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

MAX_LOGIN_FAILURES = 5


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)


def create_access_token(user_id: int, settings: Settings) -> str:
    expire = datetime.now(timezone.utc) + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    payload = {"sub": str(user_id), "exp": expire}
    return jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def create_refresh_token() -> str:
    return secrets.token_urlsafe(64)


async def register_user(
    email: str, password: str, name: str, db: AsyncSession
) -> User:
    existing = await db.execute(select(User).where(User.email == email))
    if existing.scalar_one_or_none():
        raise ValueError("Email already registered")

    user = User(
        email=email,
        password_hash=hash_password(password),
        name=name,
        role=UserRole.USER,
    )
    db.add(user)
    await db.flush()
    return user


async def authenticate_user(
    email: str,
    password: str,
    totp_code: str | None,
    ip_address: str | None,
    db: AsyncSession,
    settings: Settings,
) -> dict:
    result = await db.execute(select(User).where(User.email == email))
    user = result.scalar_one_or_none()

    if not user or not user.is_active:
        raise ValueError("Invalid email or password")

    if user.is_locked:
        raise ValueError("ACCOUNT_LOCKED")

    # IP check for ADMIN — fail closed: no IP = deny
    if user.role == UserRole.ADMIN and user.allowed_ips:
        if not ip_address or ip_address not in user.allowed_ips:
            raise ValueError(f"IP {ip_address!r} not allowed for admin account")

    if not verify_password(password, user.password_hash):
        user.login_fail_count += 1
        if user.login_fail_count >= MAX_LOGIN_FAILURES:
            user.is_locked = True
            user.locked_at = datetime.now(timezone.utc)
        await db.flush()
        if user.is_locked:
            raise ValueError("ACCOUNT_LOCKED")
        raise ValueError("Invalid email or password")

    # TOTP check
    if user.totp_enabled:
        if not totp_code:
            raise ValueError("TOTP code required")
        totp = pyotp.TOTP(user.totp_secret)
        if not totp.verify(totp_code, valid_window=1):
            raise ValueError("Invalid TOTP code")

    # Reset fail count on success
    user.login_fail_count = 0
    await db.flush()

    access_token = create_access_token(user.id, settings)
    refresh_token_str = create_refresh_token()

    refresh_token = RefreshToken(
        user_id=user.id,
        token=refresh_token_str,
        expires_at=datetime.now(timezone.utc) + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS),
    )
    db.add(refresh_token)
    await db.flush()

    return {
        "access_token": access_token,
        "refresh_token": refresh_token_str,
        "token_type": "bearer",
    }


async def refresh_tokens(
    refresh_token_str: str, db: AsyncSession, settings: Settings
) -> dict:
    result = await db.execute(
        select(RefreshToken).where(
            RefreshToken.token == refresh_token_str,
            RefreshToken.revoked == False,  # noqa: E712
        )
    )
    token = result.scalar_one_or_none()

    if not token:
        raise ValueError("Invalid refresh token")

    expires_at = token.expires_at if token.expires_at.tzinfo else token.expires_at.replace(tzinfo=timezone.utc)
    if expires_at < datetime.now(timezone.utc):
        token.revoked = True
        await db.flush()
        raise ValueError("Refresh token expired")

    # Revoke old token
    token.revoked = True

    # Issue new tokens
    access_token = create_access_token(token.user_id, settings)
    new_refresh_str = create_refresh_token()
    new_refresh = RefreshToken(
        user_id=token.user_id,
        token=new_refresh_str,
        expires_at=datetime.now(timezone.utc) + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS),
    )
    db.add(new_refresh)
    await db.flush()

    return {
        "access_token": access_token,
        "refresh_token": new_refresh_str,
        "token_type": "bearer",
    }


async def revoke_refresh_token(refresh_token_str: str, db: AsyncSession) -> None:
    await db.execute(
        update(RefreshToken)
        .where(RefreshToken.token == refresh_token_str)
        .values(revoked=True)
    )
    await db.flush()


def generate_totp_secret() -> str:
    return pyotp.random_base32()


def generate_totp_qr(secret: str, email: str) -> str:
    totp = pyotp.TOTP(secret)
    uri = totp.provisioning_uri(name=email, issuer_name="KIS Trader")
    img = qrcode.make(uri)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)
    return base64.b64encode(buf.read()).decode("utf-8")


async def setup_totp(user: User, db: AsyncSession) -> dict:
    secret = generate_totp_secret()
    user.totp_secret = secret
    await db.flush()
    qr_base64 = generate_totp_qr(secret, user.email)
    return {"qr_code_base64": qr_base64}


async def verify_totp(user: User, code: str, db: AsyncSession) -> bool:
    if not user.totp_secret:
        raise ValueError("TOTP not set up")
    totp = pyotp.TOTP(user.totp_secret)
    if totp.verify(code, valid_window=1):
        user.totp_enabled = True
        await db.flush()
        return True
    return False
