import os
import pytest
import pytest_asyncio
from datetime import datetime, timedelta, timezone
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from unittest.mock import patch, MagicMock, AsyncMock

# Must set env before importing app modules
os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///:memory:"
os.environ["REDIS_URL"] = "redis://localhost:6379/0"
os.environ["JWT_SECRET_KEY"] = "test-secret-key-for-testing"
os.environ["JWT_ALGORITHM"] = "HS256"
os.environ["KIS_ENCRYPT_KEY"] = "oDcLjYF-wR1skxB_Hc5f4D5mFQKARmggSPSSm-tOH7Y="
os.environ["SLACK_WEBHOOK_URL"] = ""

from app.models.base import Base
from app.models.user import User, UserRole, RefreshToken
from app.models.account import Account, AccountType, Position, Order, OrderSide, OrderStatus
from app.models.strategy import Strategy, AlgorithmType
from app.models.backtest import BacktestRun, BacktestStatus, ValidationMode
from app.models.trading import StrategyActivation, ActivationStatus
from app.models.market import Stock, PriceDaily
from app.models.audit import AuditLog
from app.database import get_db
from app.config import get_settings, Settings


DATABASE_URL = "sqlite+aiosqlite:///:memory:"


@pytest.fixture(autouse=True)
def clear_settings_cache():
    """Clear the lru_cache on get_settings before each test."""
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


@pytest_asyncio.fixture
async def engine():
    eng = create_async_engine(DATABASE_URL, echo=False)
    async with eng.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield eng
    async with eng.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await eng.dispose()


@pytest_asyncio.fixture
async def db_session(engine):
    session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with session_factory() as session:
        yield session


@pytest_asyncio.fixture
async def client(engine, db_session):
    from app.main import app

    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as c:
        yield c
    app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def test_user(db_session):
    from passlib.context import CryptContext

    pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
    user = User(
        email="test@example.com",
        password_hash=pwd_context.hash("TestPassword123!"),
        name="Test User",
        role=UserRole.USER,
        is_active=True,
        is_locked=False,
        login_fail_count=0,
        totp_enabled=False,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest_asyncio.fixture
async def test_admin(db_session):
    from passlib.context import CryptContext

    pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
    admin = User(
        email="admin@example.com",
        password_hash=pwd_context.hash("AdminPass123!"),
        name="Admin User",
        role=UserRole.ADMIN,
        is_active=True,
        is_locked=False,
        login_fail_count=0,
        totp_enabled=False,
    )
    db_session.add(admin)
    await db_session.commit()
    await db_session.refresh(admin)
    return admin


@pytest.fixture
def settings():
    return Settings(
        DATABASE_URL="sqlite+aiosqlite:///:memory:",
        REDIS_URL="redis://localhost:6379/0",
        JWT_SECRET_KEY="test-secret-key-for-testing",
        JWT_ALGORITHM="HS256",
        ACCESS_TOKEN_EXPIRE_MINUTES=15,
        REFRESH_TOKEN_EXPIRE_DAYS=7,
        KIS_ENCRYPT_KEY="oDcLjYF-wR1skxB_Hc5f4D5mFQKARmggSPSSm-tOH7Y=",
    )


@pytest.fixture
def user_token(test_user, settings):
    from app.services.auth_service import create_access_token

    return create_access_token(test_user.id, settings)


@pytest.fixture
def admin_token(test_admin, settings):
    from app.services.auth_service import create_access_token

    return create_access_token(test_admin.id, settings)


def user_auth_header(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


@pytest_asyncio.fixture
async def test_account(db_session, test_user):
    account = Account(
        user_id=test_user.id,
        name="Test SIM Account",
        type=AccountType.SIM,
        initial_balance=10_000_000,
        cash_balance=10_000_000,
        is_active=True,
    )
    db_session.add(account)
    await db_session.commit()
    await db_session.refresh(account)
    return account


@pytest_asyncio.fixture
async def test_strategy(db_session, test_user):
    strategy = Strategy(
        user_id=test_user.id,
        name="Test MA Cross",
        description="Test strategy",
        algorithm_type=AlgorithmType.MA_CROSS,
        params={"short_period": 5, "long_period": 20},
        trade_params={"initial_capital": 10_000_000, "position_size_pct": 0.1},
        is_active=True,
    )
    db_session.add(strategy)
    await db_session.commit()
    await db_session.refresh(strategy)
    return strategy
