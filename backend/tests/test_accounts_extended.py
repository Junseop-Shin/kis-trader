"""
계정(Account) 확장 통합 테스트
계정 생성, 포지션/주문 조회, 계정 비활성화 등
"""
import pytest
from datetime import datetime, timezone
from unittest.mock import patch, MagicMock

from app.models.account import Account, AccountType, Position, Order, OrderSide, OrderStatus
from tests.conftest import user_auth_header


class TestAccountCRUD:
    """계정 CRUD API 테스트"""

    async def test_create_sim_account(self, client, test_user, user_token):
        """SIM 계정 생성 — 201 응답 및 초기 잔액 설정"""
        with patch("app.routers.accounts.encrypt_value", return_value="encrypted"):
            r = await client.post(
                "/accounts/",
                json={"name": "My SIM Account", "type": "SIM", "initial_balance": 10_000_000},
                headers=user_auth_header(user_token),
            )
        assert r.status_code == 201
        data = r.json()
        assert data["name"] == "My SIM Account"
        assert data["type"] == "SIM"

    async def test_create_real_account_with_kis(self, client, test_user, user_token):
        """REAL 계정 생성 — KIS 키 암호화 포함"""
        with patch("app.routers.accounts.encrypt_value", return_value="encrypted"):
            r = await client.post(
                "/accounts/",
                json={
                    "name": "Real Account",
                    "type": "REAL",
                    "initial_balance": 5_000_000,
                    "kis_account_no": "12345678-01",
                    "kis_app_key": "test-app-key",
                    "kis_app_secret": "test-app-secret",
                },
                headers=user_auth_header(user_token),
            )
        assert r.status_code == 201
        data = r.json()
        assert data["type"] == "REAL"

    async def test_list_accounts(self, client, test_user, test_account, user_token):
        """계정 목록 조회 — 본인 계정만 반환"""
        r = await client.get("/accounts/", headers=user_auth_header(user_token))
        assert r.status_code == 200
        accounts = r.json()
        assert len(accounts) >= 1
        for a in accounts:
            assert a["type"] in ["SIM", "REAL"]

    async def test_get_account_by_id(self, client, test_user, test_account, user_token):
        """특정 계정 상세 조회"""
        r = await client.get(f"/accounts/{test_account.id}", headers=user_auth_header(user_token))
        assert r.status_code == 200
        data = r.json()
        assert data["id"] == test_account.id

    async def test_get_nonexistent_account(self, client, test_user, user_token):
        """존재하지 않는 계정 조회 → 404"""
        r = await client.get("/accounts/99999", headers=user_auth_header(user_token))
        assert r.status_code == 404

    async def test_deactivate_account(self, client, test_user, test_account, user_token):
        """계정 비활성화(소프트 삭제) — 204 응답 확인"""
        r = await client.delete(f"/accounts/{test_account.id}", headers=user_auth_header(user_token))
        assert r.status_code == 204

    async def test_deactivate_nonexistent_account(self, client, test_user, user_token):
        """존재하지 않는 계정 비활성화 → 404"""
        r = await client.delete("/accounts/99999", headers=user_auth_header(user_token))
        assert r.status_code == 404

    async def test_other_user_cannot_access_account(self, client, db_session, test_admin, admin_token, test_account, user_token):
        """다른 사용자의 계정 접근 → 404"""
        # admin이 user의 계정 조회 시도
        r = await client.get(f"/accounts/{test_account.id}", headers=user_auth_header(admin_token))
        assert r.status_code == 404

    async def test_unauthenticated_account_access(self, client, test_account):
        """인증 없이 계정 접근 → 401"""
        r = await client.get("/accounts/")
        assert r.status_code == 401


class TestPositionsAndOrders:
    """포지션 및 주문 내역 조회 테스트"""

    @pytest.fixture
    async def account_with_position(self, db_session, test_user):
        """포지션 있는 계정 픽스처"""
        account = Account(
            user_id=test_user.id,
            name="Position Account",
            type=AccountType.SIM,
            initial_balance=10_000_000,
            cash_balance=9_000_000,
            is_active=True,
        )
        db_session.add(account)
        await db_session.flush()

        position = Position(
            account_id=account.id,
            ticker="005930",
            qty=10,
            avg_price=70000,
            current_price=71000,
            unrealized_pnl=10000,
        )
        db_session.add(position)
        await db_session.commit()
        await db_session.refresh(account)
        return account

    @pytest.fixture
    async def account_with_orders(self, db_session, test_user):
        """주문 내역 있는 계정 픽스처"""
        account = Account(
            user_id=test_user.id,
            name="Order Account",
            type=AccountType.SIM,
            initial_balance=10_000_000,
            cash_balance=9_000_000,
            is_active=True,
        )
        db_session.add(account)
        await db_session.flush()

        order = Order(
            account_id=account.id,
            ticker="005930",
            side=OrderSide.BUY,
            qty=10,
            price=70000,
            status=OrderStatus.FILLED,
            filled_price=70000,
            filled_qty=10,
            filled_at=datetime.now(timezone.utc),
        )
        db_session.add(order)
        await db_session.commit()
        await db_session.refresh(account)
        return account

    async def test_get_positions_with_data(self, client, test_user, user_token, account_with_position):
        """포지션 목록 조회 — qty > 0 포지션만 반환"""
        r = await client.get(
            f"/accounts/{account_with_position.id}/positions",
            headers=user_auth_header(user_token),
        )
        assert r.status_code == 200
        positions = r.json()
        assert len(positions) == 1
        assert positions[0]["ticker"] == "005930"
        assert positions[0]["qty"] == 10

    async def test_get_positions_empty(self, client, test_user, test_account, user_token):
        """포지션 없는 계정 조회 → 빈 목록"""
        r = await client.get(
            f"/accounts/{test_account.id}/positions",
            headers=user_auth_header(user_token),
        )
        assert r.status_code == 200
        assert r.json() == []

    async def test_get_positions_wrong_owner(self, client, test_admin, admin_token, account_with_position):
        """다른 사용자의 포지션 조회 → 404"""
        r = await client.get(
            f"/accounts/{account_with_position.id}/positions",
            headers=user_auth_header(admin_token),
        )
        assert r.status_code == 404

    async def test_get_orders_with_data(self, client, test_user, user_token, account_with_orders):
        """주문 내역 조회 — 최신순 반환"""
        r = await client.get(
            f"/accounts/{account_with_orders.id}/orders",
            headers=user_auth_header(user_token),
        )
        assert r.status_code == 200
        orders = r.json()
        assert len(orders) >= 1
        assert orders[0]["ticker"] == "005930"

    async def test_get_orders_empty(self, client, test_user, test_account, user_token):
        """주문 내역 없는 계정 조회 → 빈 목록"""
        r = await client.get(
            f"/accounts/{test_account.id}/orders",
            headers=user_auth_header(user_token),
        )
        assert r.status_code == 200
        assert r.json() == []

    async def test_get_orders_wrong_owner(self, client, test_admin, admin_token, account_with_orders):
        """다른 사용자의 주문 내역 조회 → 404"""
        r = await client.get(
            f"/accounts/{account_with_orders.id}/orders",
            headers=user_auth_header(admin_token),
        )
        assert r.status_code == 404
