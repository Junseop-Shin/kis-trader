"""
백테스트 확장 통합 테스트
비교 실행(compare), counterfactual 분석, WebSocket, 실행 상태 조회 등
"""
import pytest
from datetime import date
from unittest.mock import MagicMock, patch, AsyncMock

from app.models.backtest import BacktestRun, BacktestStatus, ValidationMode
from app.models.strategy import Strategy, AlgorithmType
from tests.conftest import user_auth_header


# 가격 데이터 없이도 백테스트 run 생성은 가능 (Celery mock 사용)


class TestBacktestRun:
    """백테스트 실행 API 테스트"""

    @pytest.fixture
    def mock_celery(self):
        """Celery send_task mock — 실제 Redis 연결 불필요"""
        with patch("app.routers.backtest._get_celery_app") as mock:
            celery_instance = MagicMock()
            task_mock = MagicMock()
            task_mock.id = "test-task-id-123"
            celery_instance.send_task.return_value = task_mock
            mock.return_value = celery_instance
            yield mock

    async def test_create_backtest_run(self, client, test_user, user_token, test_strategy, mock_celery):
        """백테스트 실행 생성 — 201 응답 및 RUNNING 상태"""
        payload = {
            "strategy_id": test_strategy.id,
            "tickers": ["005930"],
            "start_date": "2022-01-03",
            "end_date": "2022-03-31",
            "validation_type": "SIMPLE",
        }
        r = await client.post(
            "/backtest/run",
            json=payload,
            headers=user_auth_header(user_token),
        )
        assert r.status_code == 201
        data = r.json()
        assert data["status"] == "RUNNING"
        assert data["strategy_id"] == test_strategy.id

    async def test_create_backtest_nonexistent_strategy(self, client, test_user, user_token, mock_celery):
        """존재하지 않는 전략으로 백테스트 실행 → 404"""
        payload = {
            "strategy_id": 99999,
            "tickers": ["005930"],
            "start_date": "2022-01-03",
            "end_date": "2022-03-31",
            "validation_type": "SIMPLE",
        }
        r = await client.post(
            "/backtest/run",
            json=payload,
            headers=user_auth_header(user_token),
        )
        assert r.status_code == 404

    async def test_list_backtest_runs(self, client, db_session, test_user, user_token, test_strategy, mock_celery):
        """백테스트 실행 목록 조회"""
        # 실행 생성
        run = BacktestRun(
            user_id=test_user.id,
            strategy_id=test_strategy.id,
            status=BacktestStatus.DONE,
            validation_mode=ValidationMode.SIMPLE,
            tickers=["005930"],
            start_date=date(2022, 1, 3),
            end_date=date(2022, 3, 31),
        )
        db_session.add(run)
        await db_session.commit()

        r = await client.get(
            "/backtest/runs",
            headers=user_auth_header(user_token),
        )
        assert r.status_code == 200
        runs = r.json()
        assert len(runs) >= 1

    async def test_get_backtest_run(self, client, db_session, test_user, user_token, test_strategy):
        """특정 백테스트 실행 상세 조회"""
        run = BacktestRun(
            user_id=test_user.id,
            strategy_id=test_strategy.id,
            status=BacktestStatus.DONE,
            validation_mode=ValidationMode.SIMPLE,
            tickers=["005930"],
            start_date=date(2022, 1, 3),
            end_date=date(2022, 3, 31),
            result_json={"return_pct": 5.2, "sharpe": 1.1, "mdd": -3.2},
        )
        db_session.add(run)
        await db_session.commit()

        r = await client.get(
            f"/backtest/runs/{run.id}",
            headers=user_auth_header(user_token),
        )
        assert r.status_code == 200
        data = r.json()
        assert data["id"] == run.id
        assert data["status"] == "DONE"

    async def test_get_nonexistent_run(self, client, test_user, user_token):
        """존재하지 않는 백테스트 실행 조회 → 404"""
        r = await client.get(
            "/backtest/runs/99999",
            headers=user_auth_header(user_token),
        )
        assert r.status_code == 404

    async def test_get_running_backtest_celery_done(self, client, db_session, test_user, user_token, test_strategy):
        """RUNNING 상태 백테스트 조회 시 Celery 결과가 완료되면 DONE으로 업데이트"""
        run = BacktestRun(
            user_id=test_user.id,
            strategy_id=test_strategy.id,
            status=BacktestStatus.RUNNING,
            validation_mode=ValidationMode.SIMPLE,
            tickers=["005930"],
            start_date=date(2022, 1, 3),
            end_date=date(2022, 3, 31),
            celery_task_id="done-task-id",
        )
        db_session.add(run)
        await db_session.commit()

        # Celery 태스크가 완료된 상태로 mock
        mock_result = MagicMock()
        mock_result.ready.return_value = True
        mock_result.successful.return_value = True
        mock_result.result = {"return_pct": 8.5, "sharpe": 1.5, "mdd": -5.0}

        with patch("app.routers.backtest._get_celery_app") as mock_celery:
            celery_instance = MagicMock()
            celery_instance.AsyncResult.return_value = mock_result
            mock_celery.return_value = celery_instance

            r = await client.get(
                f"/backtest/runs/{run.id}",
                headers=user_auth_header(user_token),
            )

        assert r.status_code == 200
        data = r.json()
        assert data["status"] == "DONE"

    async def test_get_running_backtest_celery_failed(self, client, db_session, test_user, user_token, test_strategy):
        """RUNNING 상태 백테스트 조회 시 Celery 태스크 실패 → FAILED 업데이트"""
        run = BacktestRun(
            user_id=test_user.id,
            strategy_id=test_strategy.id,
            status=BacktestStatus.RUNNING,
            validation_mode=ValidationMode.SIMPLE,
            tickers=["005930"],
            start_date=date(2022, 1, 3),
            end_date=date(2022, 3, 31),
            celery_task_id="failed-task-id",
        )
        db_session.add(run)
        await db_session.commit()

        mock_result = MagicMock()
        mock_result.ready.return_value = True
        mock_result.successful.return_value = False
        mock_result.info = Exception("Worker error occurred")

        with patch("app.routers.backtest._get_celery_app") as mock_celery:
            celery_instance = MagicMock()
            celery_instance.AsyncResult.return_value = mock_result
            mock_celery.return_value = celery_instance

            r = await client.get(
                f"/backtest/runs/{run.id}",
                headers=user_auth_header(user_token),
            )

        assert r.status_code == 200
        data = r.json()
        assert data["status"] == "FAILED"


class TestBacktestCompare:
    """전략 비교 백테스트 테스트"""

    @pytest.fixture
    def mock_celery(self):
        with patch("app.routers.backtest._get_celery_app") as mock:
            celery_instance = MagicMock()
            task_mock = MagicMock()
            task_mock.id = "compare-task-id"
            celery_instance.send_task.return_value = task_mock
            mock.return_value = celery_instance
            yield mock

    async def test_compare_strategies(self, client, db_session, test_user, user_token, test_strategy, mock_celery):
        """두 전략 비교 백테스트 실행 — 두 개의 run이 생성됨"""
        # 두 번째 전략 생성
        strategy2 = Strategy(
            user_id=test_user.id,
            name="RSI Strategy",
            algorithm_type=AlgorithmType.RSI,
            params={"period": 14, "oversold": 30, "overbought": 70},
            trade_params={"initial_capital": 10_000_000, "position_size_pct": 0.1},
            is_active=True,
        )
        db_session.add(strategy2)
        await db_session.commit()

        payload = {
            "strategy_ids": [test_strategy.id, strategy2.id],
            "tickers": ["005930"],
            "start_date": "2022-01-03",
            "end_date": "2022-03-31",
        }
        r = await client.post(
            "/backtest/compare",
            json=payload,
            headers=user_auth_header(user_token),
        )
        assert r.status_code == 200
        data = r.json()
        assert "runs" in data
        assert len(data["runs"]) == 2

    async def test_compare_validation_error(self, client, test_user, user_token, mock_celery):
        """strategy_ids가 최소 2개 미만이면 422 오류"""
        payload = {
            "strategy_ids": [1],  # min_length=2 위반
            "tickers": ["005930"],
            "start_date": "2022-01-03",
            "end_date": "2022-03-31",
        }
        r = await client.post(
            "/backtest/compare",
            json=payload,
            headers=user_auth_header(user_token),
        )
        assert r.status_code == 422


class TestCounterfactualAnalysis:
    """Counterfactual 분석 테스트"""

    @pytest.fixture
    def mock_backtest_service(self):
        """backtest_service.run_counterfactual mock"""
        with patch("app.routers.backtest.run_counterfactual") as mock:
            mock.return_value = {
                "account_id": 1,
                "period": "2022-01-03 ~ 2022-03-31",
                "tickers": ["005930"],
                "counterfactual_runs": [
                    {"run_id": 1, "strategy_id": 1, "strategy_name": "Test", "celery_task_id": "task-1"}
                ],
                "actual_equity_curve": [{"date": "2022-01-03", "portfolio_value": 10000000.0}],
            }
            yield mock

    async def test_counterfactual_success(self, client, test_user, user_token, test_strategy, test_account, mock_backtest_service):
        """Counterfactual 분석 성공 — 실제 거래 이력 기간 동안 전략 시뮬레이션"""
        payload = {
            "account_id": test_account.id,
            "strategy_ids": [test_strategy.id],
        }
        r = await client.post(
            "/backtest/counterfactual",
            json=payload,
            headers=user_auth_header(user_token),
        )
        assert r.status_code == 200
        data = r.json()
        assert "account_id" in data
        assert "counterfactual_runs" in data

    async def test_counterfactual_value_error(self, client, test_user, user_token, test_strategy, test_account):
        """Counterfactual 분석 실패 — 거래 이력 없을 때 400 에러"""
        with patch("app.routers.backtest.run_counterfactual") as mock:
            mock.side_effect = ValueError("No trading history found for this account")

            payload = {
                "account_id": test_account.id,
                "strategy_ids": [test_strategy.id],
            }
            r = await client.post(
                "/backtest/counterfactual",
                json=payload,
                headers=user_auth_header(user_token),
            )
        assert r.status_code == 400
        assert "No trading history" in r.json()["detail"]
