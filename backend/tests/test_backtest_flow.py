"""
백테스트 흐름 통합 테스트
전략 생성 -> 백테스트 실행 요청 -> 결과 조회 -> 비교 -> Counterfactual
Celery task는 목(mock)으로 대체
"""
import pytest
from datetime import date, datetime, timezone
from unittest.mock import patch, MagicMock

from app.models.backtest import BacktestRun, BacktestStatus, ValidationMode
from app.models.account import Account, AccountType, Order, OrderSide, OrderStatus
from tests.conftest import user_auth_header


class TestBacktestFlow:
    """백테스트 전체 흐름 통합 테스트"""

    @pytest.fixture
    def mock_celery(self):
        """Celery send_task를 목으로 대체하는 픽스처"""
        mock_task = MagicMock()
        mock_task.id = "mock-celery-task-id"
        with patch("app.routers.backtest._get_celery_app") as mock_app:
            mock_app.return_value.send_task.return_value = mock_task
            mock_app.return_value.AsyncResult.return_value = MagicMock(
                ready=lambda: False, id="mock-celery-task-id"
            )
            yield mock_app

    async def test_create_backtest_run(
        self, client, db_session, test_user, test_strategy, user_token, mock_celery
    ):
        """백테스트 실행 요청 시 RUNNING 상태 레코드 생성"""
        # 가격 데이터 없어도 run 레코드 자체는 생성되어야 함
        r = await client.post(
            "/backtest/run",
            json={
                "strategy_id": test_strategy.id,
                "tickers": ["005930"],
                "start_date": "2023-01-01",
                "end_date": "2023-12-31",
                "benchmark_ticker": "069500",
                "validation_type": "SIMPLE",
            },
            headers=user_auth_header(user_token),
        )
        assert r.status_code == 201
        data = r.json()
        assert data["status"] == "RUNNING"
        assert data["tickers"] == ["005930"]
        assert data["celery_task_id"] == "mock-celery-task-id"

    async def test_create_backtest_with_nonowned_strategy(
        self, client, test_user, user_token, mock_celery
    ):
        """소유하지 않은 전략으로 백테스트 요청 시 404 에러"""
        r = await client.post(
            "/backtest/run",
            json={
                "strategy_id": 99999,
                "tickers": ["005930"],
                "start_date": "2023-01-01",
                "end_date": "2023-12-31",
            },
            headers=user_auth_header(user_token),
        )
        assert r.status_code == 404

    async def test_list_backtest_runs(
        self, client, db_session, test_user, test_strategy, user_token, mock_celery
    ):
        """백테스트 실행 목록 조회"""
        # 먼저 백테스트 하나 생성
        await client.post(
            "/backtest/run",
            json={
                "strategy_id": test_strategy.id,
                "tickers": ["005930"],
                "start_date": "2023-01-01",
                "end_date": "2023-12-31",
            },
            headers=user_auth_header(user_token),
        )

        r = await client.get("/backtest/runs", headers=user_auth_header(user_token))
        assert r.status_code == 200
        runs = r.json()
        assert len(runs) >= 1

    async def test_get_backtest_run_detail(
        self, client, db_session, test_user, test_strategy, user_token, mock_celery
    ):
        """백테스트 실행 상세 조회 (아직 RUNNING 상태)"""
        r = await client.post(
            "/backtest/run",
            json={
                "strategy_id": test_strategy.id,
                "tickers": ["005930"],
                "start_date": "2023-01-01",
                "end_date": "2023-12-31",
            },
            headers=user_auth_header(user_token),
        )
        run_id = r.json()["id"]

        r = await client.get(
            f"/backtest/runs/{run_id}",
            headers=user_auth_header(user_token),
        )
        assert r.status_code == 200
        data = r.json()
        assert data["id"] == run_id

    async def test_get_nonexistent_run(self, client, test_user, user_token):
        """존재하지 않는 백테스트 조회 시 404 에러"""
        r = await client.get(
            "/backtest/runs/99999",
            headers=user_auth_header(user_token),
        )
        assert r.status_code == 404

    async def test_get_completed_run_syncs_result(
        self, client, db_session, test_user, test_strategy, user_token
    ):
        """Celery 태스크가 완료되면 결과가 동기화되는지 검증"""
        # 직접 DB에 RUNNING 상태 레코드 생성
        run = BacktestRun(
            user_id=test_user.id,
            strategy_id=test_strategy.id,
            status=BacktestStatus.RUNNING,
            validation_mode=ValidationMode.SIMPLE,
            tickers=["005930"],
            start_date=date(2023, 1, 1),
            end_date=date(2023, 12, 31),
            celery_task_id="done-task-id",
        )
        db_session.add(run)
        await db_session.commit()
        await db_session.refresh(run)

        # Celery 태스크가 성공적으로 완료된 것으로 목킹
        mock_result = MagicMock()
        mock_result.ready.return_value = True
        mock_result.successful.return_value = True
        mock_result.result = {
            "metrics": {"total_return_pct": 15.5, "sharpe_ratio": 1.2},
            "trades": [],
            "equity_curve": [],
        }

        with patch("app.routers.backtest._get_celery_app") as mock_app:
            mock_app.return_value.AsyncResult.return_value = mock_result

            r = await client.get(
                f"/backtest/runs/{run.id}",
                headers=user_auth_header(user_token),
            )
            assert r.status_code == 200
            data = r.json()
            assert data["status"] == "DONE"
            assert data["result_json"] is not None

    async def test_compare_strategies(
        self, client, db_session, test_user, test_strategy, user_token
    ):
        """전략 비교 요청 시 여러 백테스트 실행"""
        from app.models.strategy import Strategy, AlgorithmType

        # 비교할 두 번째 전략 생성
        strategy2 = Strategy(
            user_id=test_user.id,
            name="RSI Strategy",
            algorithm_type=AlgorithmType.RSI,
            params={"period": 14},
            trade_params={},
            is_active=True,
        )
        db_session.add(strategy2)
        await db_session.commit()
        await db_session.refresh(strategy2)

        mock_task = MagicMock()
        mock_task.id = "compare-task-id"
        with patch("app.routers.backtest._get_celery_app") as mock_app:
            mock_app.return_value.send_task.return_value = mock_task

            r = await client.post(
                "/backtest/compare",
                json={
                    "strategy_ids": [test_strategy.id, strategy2.id],
                    "tickers": ["005930"],
                    "start_date": "2023-01-01",
                    "end_date": "2023-12-31",
                },
                headers=user_auth_header(user_token),
            )
            assert r.status_code == 200
            data = r.json()
            assert len(data["runs"]) == 2

    async def test_counterfactual_analysis(
        self, client, db_session, test_user, test_account, test_strategy, user_token
    ):
        """Counterfactual 분석 - 거래 이력이 없으면 ValueError
        backtest_service.run_counterfactual을 목킹하여 PostgreSQL 전용 SQL 우회
        """
        with patch("app.routers.backtest.run_counterfactual", side_effect=ValueError("No orders found")):
            r = await client.post(
                "/backtest/counterfactual",
                json={
                    "account_id": test_account.id,
                    "strategy_ids": [test_strategy.id],
                },
                headers=user_auth_header(user_token),
            )
            assert r.status_code == 400
            assert "No orders found" in r.json()["detail"]

    async def test_walk_forward_validation_mode(
        self, client, db_session, test_user, test_strategy, user_token, mock_celery
    ):
        """WALK_FORWARD 유효성 검사 모드로 백테스트 실행"""
        r = await client.post(
            "/backtest/run",
            json={
                "strategy_id": test_strategy.id,
                "tickers": ["005930"],
                "start_date": "2023-01-01",
                "end_date": "2023-12-31",
                "validation_type": "WALK_FORWARD",
                "validation_params": {"n_splits": 5},
            },
            headers=user_auth_header(user_token),
        )
        assert r.status_code == 201
        data = r.json()
        assert data["validation_mode"] == "WALK_FORWARD"
