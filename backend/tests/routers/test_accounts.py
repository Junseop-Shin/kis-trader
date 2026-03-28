import pytest
from unittest.mock import patch

from tests.conftest import user_auth_header


class TestCreateAccount:
    async def test_create_sim_account(self, client, test_user, user_token):
        r = await client.post(
            "/accounts/",
            json={"name": "My SIM", "type": "SIM", "initial_balance": 5_000_000},
            headers=user_auth_header(user_token),
        )
        assert r.status_code == 201
        data = r.json()
        assert data["name"] == "My SIM"
        assert data["type"] == "SIM"
        assert data["cash_balance"] == 5_000_000

    @patch("app.routers.accounts.encrypt_value", return_value="encrypted")
    async def test_create_real_account(self, mock_encrypt, client, test_user, user_token):
        r = await client.post(
            "/accounts/",
            json={
                "name": "Real Account",
                "type": "REAL",
                "kis_account_no": "12345678-01",
                "kis_app_key": "test_key",
                "kis_app_secret": "test_secret",
            },
            headers=user_auth_header(user_token),
        )
        assert r.status_code == 201

    async def test_create_requires_auth(self, client):
        r = await client.post(
            "/accounts/",
            json={"name": "Test", "type": "SIM"},
        )
        assert r.status_code == 401


class TestListAccounts:
    async def test_list_empty(self, client, test_user, user_token):
        r = await client.get("/accounts/", headers=user_auth_header(user_token))
        assert r.status_code == 200
        assert r.json() == []

    async def test_list_returns_own(self, client, test_user, user_token, test_account):
        r = await client.get("/accounts/", headers=user_auth_header(user_token))
        assert r.status_code == 200
        assert len(r.json()) == 1


class TestGetAccount:
    async def test_get_success(self, client, test_user, user_token, test_account):
        r = await client.get(
            f"/accounts/{test_account.id}",
            headers=user_auth_header(user_token),
        )
        assert r.status_code == 200
        assert r.json()["id"] == test_account.id

    async def test_get_not_found(self, client, test_user, user_token):
        r = await client.get("/accounts/9999", headers=user_auth_header(user_token))
        assert r.status_code == 404


class TestGetPositions:
    async def test_empty_positions(self, client, test_user, user_token, test_account):
        r = await client.get(
            f"/accounts/{test_account.id}/positions",
            headers=user_auth_header(user_token),
        )
        assert r.status_code == 200
        assert r.json() == []

    async def test_account_not_found(self, client, test_user, user_token):
        r = await client.get("/accounts/9999/positions", headers=user_auth_header(user_token))
        assert r.status_code == 404


class TestGetOrders:
    async def test_empty_orders(self, client, test_user, user_token, test_account):
        r = await client.get(
            f"/accounts/{test_account.id}/orders",
            headers=user_auth_header(user_token),
        )
        assert r.status_code == 200
        assert r.json() == []

    async def test_account_not_found(self, client, test_user, user_token):
        r = await client.get("/accounts/9999/orders", headers=user_auth_header(user_token))
        assert r.status_code == 404


class TestDeactivateAccount:
    async def test_deactivate_success(self, client, test_user, user_token, test_account):
        r = await client.delete(
            f"/accounts/{test_account.id}",
            headers=user_auth_header(user_token),
        )
        assert r.status_code == 204

    async def test_deactivate_not_found(self, client, test_user, user_token):
        r = await client.delete("/accounts/9999", headers=user_auth_header(user_token))
        assert r.status_code == 404
