import logging
from datetime import datetime, timezone

import httpx
from cryptography.fernet import Fernet
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..config import get_settings
from ..database import async_session_factory
from ..models.account import Account, AccountType

logger = logging.getLogger(__name__)


def _get_fernet() -> Fernet:
    settings = get_settings()
    return Fernet(settings.KIS_ENCRYPT_KEY.encode())


def encrypt_value(value: str) -> str:
    return _get_fernet().encrypt(value.encode()).decode()


def decrypt_value(encrypted: str) -> str:
    return _get_fernet().decrypt(encrypted.encode()).decode()


async def refresh_kis_tokens():
    """
    Refresh KIS API access tokens for all REAL accounts.
    Called daily at 08:30 before market open.
    KIS tokens expire every ~24 hours.
    """
    settings = get_settings()
    async with async_session_factory() as db:
        result = await db.execute(
            select(Account).where(
                Account.type == AccountType.REAL,
                Account.is_active == True,  # noqa: E712
                Account.kis_app_key.isnot(None),
            )
        )
        accounts = result.scalars().all()

        for account in accounts:
            try:
                app_key = decrypt_value(account.kis_app_key)
                app_secret = decrypt_value(account.kis_app_secret)

                async with httpx.AsyncClient() as client:
                    resp = await client.post(
                        f"{settings.KIS_BASE_URL}/oauth2/tokenP",
                        json={
                            "grant_type": "client_credentials",
                            "appkey": app_key,
                            "appsecret": app_secret,
                        },
                        timeout=30,
                    )
                    resp.raise_for_status()
                    data = resp.json()

                account.kis_access_token = encrypt_value(data["access_token"])
                expires_in = data.get("expires_in", 86400)
                account.kis_token_expires_at = datetime.now(timezone.utc).replace(
                    second=0, microsecond=0
                ) + __import__("datetime").timedelta(seconds=expires_in)

                logger.info(f"Refreshed KIS token for account {account.id}")
            except Exception as e:
                logger.error(f"Failed to refresh KIS token for account {account.id}: {e}")

        await db.commit()
