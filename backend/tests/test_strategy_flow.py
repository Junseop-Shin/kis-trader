"""
전략 CRUD 전체 흐름 통합 테스트
전략 생성 -> 조회 -> 수정 -> 삭제, 권한 분리 검증
"""
import pytest

from tests.conftest import user_auth_header


class TestStrategyFlow:
    """전략 CRUD 흐름 및 권한 분리 통합 테스트"""

    async def test_create_and_list_strategies(self, client, test_user, user_token):
        """전략 생성 후 목록 조회에 포함되는지 검증"""
        # 전략 생성
        r = await client.post(
            "/strategies/",
            json={
                "name": "My MA Cross",
                "description": "Test strategy",
                "algorithm_type": "MA_CROSS",
                "params": {"short_period": 5, "long_period": 20},
                "trade_params": {"initial_capital": 10000000, "position_size_pct": 0.1},
            },
            headers=user_auth_header(user_token),
        )
        assert r.status_code == 201
        strategy = r.json()
        assert strategy["name"] == "My MA Cross"
        assert strategy["algorithm_type"] == "MA_CROSS"
        assert strategy["is_active"] is True
        strategy_id = strategy["id"]

        # 목록 조회 시 방금 생성한 전략이 포함되어야 함
        r = await client.get("/strategies/", headers=user_auth_header(user_token))
        assert r.status_code == 200
        items = r.json()
        assert any(s["id"] == strategy_id for s in items)

    async def test_get_strategy_by_id(self, client, test_user, user_token, test_strategy):
        """특정 전략 ID로 상세 조회"""
        r = await client.get(
            f"/strategies/{test_strategy.id}",
            headers=user_auth_header(user_token),
        )
        assert r.status_code == 200
        data = r.json()
        assert data["id"] == test_strategy.id
        assert data["name"] == test_strategy.name

    async def test_update_strategy(self, client, test_user, user_token, test_strategy):
        """전략 이름/파라미터 수정"""
        r = await client.put(
            f"/strategies/{test_strategy.id}",
            json={"name": "Updated Name", "params": {"short_period": 10, "long_period": 50}},
            headers=user_auth_header(user_token),
        )
        assert r.status_code == 200
        data = r.json()
        assert data["name"] == "Updated Name"
        assert data["params"]["short_period"] == 10

    async def test_delete_strategy_soft_delete(self, client, test_user, user_token, test_strategy):
        """전략 삭제 시 소프트 삭제(is_active=False) 확인"""
        r = await client.delete(
            f"/strategies/{test_strategy.id}",
            headers=user_auth_header(user_token),
        )
        assert r.status_code == 204

        # 삭제 후 목록에서 제외되는지 확인
        r = await client.get("/strategies/", headers=user_auth_header(user_token))
        items = r.json()
        assert not any(s["id"] == test_strategy.id for s in items)

    async def test_get_nonexistent_strategy(self, client, test_user, user_token):
        """존재하지 않는 전략 조회 시 404 에러"""
        r = await client.get("/strategies/99999", headers=user_auth_header(user_token))
        assert r.status_code == 404

    async def test_create_strategy_with_invalid_algorithm(self, client, test_user, user_token):
        """유효하지 않은 알고리즘 타입으로 생성 시 400 에러"""
        r = await client.post(
            "/strategies/",
            json={
                "name": "Invalid Algo",
                "algorithm_type": "NONEXISTENT",
                "params": {},
                "trade_params": {},
            },
            headers=user_auth_header(user_token),
        )
        assert r.status_code == 400

    # --- 권한 분리 ---

    async def test_other_user_cannot_access_strategy(
        self, client, db_session, test_user, test_strategy, user_token
    ):
        """다른 사용자가 소유하지 않은 전략에 접근 시 404 에러"""
        from app.models.user import User, UserRole
        from passlib.context import CryptContext
        from app.services.auth_service import create_access_token
        from app.config import get_settings

        pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
        other_user = User(
            email="other@test.com",
            password_hash=pwd_context.hash("OtherPass123!"),
            name="Other User",
            role=UserRole.USER,
            is_active=True,
            is_locked=False,
            login_fail_count=0,
        )
        db_session.add(other_user)
        await db_session.commit()
        await db_session.refresh(other_user)

        settings = get_settings()
        other_token = create_access_token(other_user.id, settings)

        # 다른 사용자가 test_strategy에 접근
        r = await client.get(
            f"/strategies/{test_strategy.id}",
            headers=user_auth_header(other_token),
        )
        assert r.status_code == 404

    async def test_unauthenticated_access_denied(self, client):
        """인증 없이 전략 목록 조회 시 401 에러"""
        r = await client.get("/strategies/")
        assert r.status_code == 401

    async def test_create_all_algorithm_types(self, client, test_user, user_token):
        """모든 유효한 알고리즘 타입으로 전략 생성 가능한지 검증"""
        algo_types = ["MA_CROSS", "RSI", "MACD", "BOLLINGER", "MOMENTUM",
                      "STOCHASTIC", "MEAN_REVERT", "MULTI", "CUSTOM"]
        for algo in algo_types:
            r = await client.post(
                "/strategies/",
                json={
                    "name": f"Strategy {algo}",
                    "algorithm_type": algo,
                    "params": {},
                    "trade_params": {},
                },
                headers=user_auth_header(user_token),
            )
            assert r.status_code == 201, f"Failed for algorithm_type={algo}"
