import pytest

from tests.conftest import user_auth_header


class TestCreateStrategy:
    async def test_create_success(self, client, test_user, user_token):
        r = await client.post(
            "/strategies/",
            json={
                "name": "My MA Strategy",
                "algorithm_type": "MA_CROSS",
                "params": {"short_period": 5, "long_period": 20},
                "trade_params": {"initial_capital": 10_000_000},
            },
            headers=user_auth_header(user_token),
        )
        assert r.status_code == 201
        data = r.json()
        assert data["name"] == "My MA Strategy"
        assert data["algorithm_type"] == "MA_CROSS"

    async def test_create_invalid_algorithm(self, client, test_user, user_token):
        r = await client.post(
            "/strategies/",
            json={"name": "Bad", "algorithm_type": "INVALID"},
            headers=user_auth_header(user_token),
        )
        assert r.status_code == 400

    async def test_create_requires_auth(self, client):
        r = await client.post(
            "/strategies/",
            json={"name": "Test", "algorithm_type": "RSI"},
        )
        assert r.status_code == 401

    async def test_create_all_algorithm_types(self, client, test_user, user_token):
        types = ["MA_CROSS", "RSI", "MACD", "BOLLINGER", "MOMENTUM", "STOCHASTIC", "MEAN_REVERT", "MULTI", "CUSTOM"]
        for algo_type in types:
            r = await client.post(
                "/strategies/",
                json={"name": f"Strategy {algo_type}", "algorithm_type": algo_type},
                headers=user_auth_header(user_token),
            )
            assert r.status_code == 201, f"Failed for {algo_type}"


class TestListStrategies:
    async def test_list_empty(self, client, test_user, user_token):
        r = await client.get("/strategies/", headers=user_auth_header(user_token))
        assert r.status_code == 200
        assert r.json() == []

    async def test_list_returns_own_strategies(self, client, test_user, user_token, test_strategy):
        r = await client.get("/strategies/", headers=user_auth_header(user_token))
        assert r.status_code == 200
        data = r.json()
        assert len(data) == 1
        assert data[0]["name"] == test_strategy.name


class TestGetStrategy:
    async def test_get_success(self, client, test_user, user_token, test_strategy):
        r = await client.get(
            f"/strategies/{test_strategy.id}",
            headers=user_auth_header(user_token),
        )
        assert r.status_code == 200
        assert r.json()["id"] == test_strategy.id

    async def test_get_not_found(self, client, test_user, user_token):
        r = await client.get("/strategies/9999", headers=user_auth_header(user_token))
        assert r.status_code == 404

    async def test_get_other_users_strategy(self, client, test_admin, admin_token, test_strategy):
        """Admin should not see another user's strategy via this endpoint."""
        r = await client.get(
            f"/strategies/{test_strategy.id}",
            headers=user_auth_header(admin_token),
        )
        assert r.status_code == 404


class TestUpdateStrategy:
    async def test_update_name(self, client, test_user, user_token, test_strategy):
        r = await client.put(
            f"/strategies/{test_strategy.id}",
            json={"name": "Updated Name"},
            headers=user_auth_header(user_token),
        )
        assert r.status_code == 200
        assert r.json()["name"] == "Updated Name"

    async def test_update_params(self, client, test_user, user_token, test_strategy):
        r = await client.put(
            f"/strategies/{test_strategy.id}",
            json={"params": {"short_period": 10, "long_period": 50}},
            headers=user_auth_header(user_token),
        )
        assert r.status_code == 200
        assert r.json()["params"]["short_period"] == 10

    async def test_update_not_found(self, client, test_user, user_token):
        r = await client.put(
            "/strategies/9999",
            json={"name": "Nope"},
            headers=user_auth_header(user_token),
        )
        assert r.status_code == 404


class TestDeleteStrategy:
    async def test_delete_soft_deactivates(self, client, test_user, user_token, test_strategy):
        r = await client.delete(
            f"/strategies/{test_strategy.id}",
            headers=user_auth_header(user_token),
        )
        assert r.status_code == 204

        # Should no longer appear in list
        r2 = await client.get("/strategies/", headers=user_auth_header(user_token))
        assert len(r2.json()) == 0

    async def test_delete_not_found(self, client, test_user, user_token):
        r = await client.delete("/strategies/9999", headers=user_auth_header(user_token))
        assert r.status_code == 404
