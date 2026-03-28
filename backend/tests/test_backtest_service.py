"""
백테스트 서비스 통합 테스트
_fetch_prices_for_tickers, _fetch_benchmark_prices, run_counterfactual 함수 검증
"""
import json
import pytest
from datetime import date
from unittest.mock import MagicMock, patch, AsyncMock

from app.services.backtest_service import (
    _fetch_prices_for_tickers,
    _fetch_benchmark_prices,
    run_counterfactual,
)
from app.models.strategy import AlgorithmType


class TestFetchPricesForTickers:
    """_fetch_prices_for_tickers 단위 테스트"""

    async def test_fetch_single_ticker(self):
        """단일 티커 가격 데이터 조회 — JSON 문자열 반환"""
        mock_db = AsyncMock()
        mock_result = MagicMock()
        mock_result.fetchall.return_value = [
            (date(2022, 1, 3), 70000, 72000, 68000, 71000, 1_000_000),
            (date(2022, 1, 4), 71000, 73000, 69000, 72000, 1_200_000),
        ]
        mock_db.execute = AsyncMock(return_value=mock_result)

        result = await _fetch_prices_for_tickers(mock_db, ["005930"], date(2022, 1, 3), date(2022, 1, 4))
        data = json.loads(result)

        assert len(data) == 2
        assert data[0]["close"] == 71000
        assert data[1]["close"] == 72000
        assert "date" in data[0]
        assert "open" in data[0]

    async def test_fetch_multiple_tickers(self):
        """복수 티커 가격 데이터 조회 — 모든 티커 데이터 합산"""
        mock_db = AsyncMock()

        # 첫 번째 티커 조회 결과
        mock_result1 = MagicMock()
        mock_result1.fetchall.return_value = [
            (date(2022, 1, 3), 70000, 72000, 68000, 71000, 1_000_000),
        ]
        # 두 번째 티커 조회 결과
        mock_result2 = MagicMock()
        mock_result2.fetchall.return_value = [
            (date(2022, 1, 3), 50000, 52000, 48000, 51000, 500_000),
        ]

        mock_db.execute = AsyncMock(side_effect=[mock_result1, mock_result2])

        result = await _fetch_prices_for_tickers(
            mock_db, ["005930", "000660"], date(2022, 1, 3), date(2022, 1, 3)
        )
        data = json.loads(result)

        # 두 티커 데이터 합산 = 2개
        assert len(data) == 2

    async def test_fetch_empty_result(self):
        """데이터 없을 때 빈 JSON 배열 반환"""
        mock_db = AsyncMock()
        mock_result = MagicMock()
        mock_result.fetchall.return_value = []
        mock_db.execute = AsyncMock(return_value=mock_result)

        result = await _fetch_prices_for_tickers(mock_db, ["999999"], date(2022, 1, 3), date(2022, 1, 4))
        data = json.loads(result)
        assert data == []


class TestFetchBenchmarkPrices:
    """_fetch_benchmark_prices 단위 테스트"""

    async def test_fetch_benchmark_with_data(self):
        """벤치마크 가격 데이터 조회 성공"""
        mock_db = AsyncMock()
        mock_result = MagicMock()
        mock_result.fetchall.return_value = [
            (date(2022, 1, 3), 30000, 31000, 29000, 30500, 5_000_000),
        ]
        mock_db.execute = AsyncMock(return_value=mock_result)

        result = await _fetch_benchmark_prices(mock_db, "069500", date(2022, 1, 3), date(2022, 1, 3))
        assert result is not None
        data = json.loads(result)
        assert len(data) == 1
        assert data[0]["close"] == 30500

    async def test_fetch_benchmark_none_ticker(self):
        """벤치마크 티커가 None이면 None 반환"""
        mock_db = AsyncMock()

        result = await _fetch_benchmark_prices(mock_db, None, date(2022, 1, 3), date(2022, 1, 3))
        assert result is None
        # DB 호출 없어야 함
        mock_db.execute.assert_not_called()

    async def test_fetch_benchmark_no_data(self):
        """벤치마크 데이터 없을 때 None 반환"""
        mock_db = AsyncMock()
        mock_result = MagicMock()
        mock_result.fetchall.return_value = []
        mock_db.execute = AsyncMock(return_value=mock_result)

        result = await _fetch_benchmark_prices(mock_db, "069500", date(2022, 1, 3), date(2022, 1, 3))
        assert result is None


class TestRunCounterfactual:
    """run_counterfactual 통합 테스트"""

    def _make_settings(self):
        """테스트용 Settings mock"""
        settings = MagicMock()
        settings.REDIS_URL = "redis://localhost:6379/0"
        return settings

    def _make_strategy(self, strategy_id=1, user_id=1):
        """테스트용 Strategy mock"""
        strategy = MagicMock()
        strategy.id = strategy_id
        strategy.user_id = user_id
        strategy.name = "Test Strategy"
        strategy.algorithm_type = MagicMock()
        strategy.algorithm_type.value = "MA_CROSS"
        strategy.params = {"short_period": 5, "long_period": 20}
        strategy.trade_params = {"initial_capital": 10_000_000, "position_size_pct": 0.1}
        return strategy

    async def test_run_counterfactual_account_not_found(self):
        """계정을 찾지 못하면 ValueError 발생"""
        mock_db = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute = AsyncMock(return_value=mock_result)

        with pytest.raises(ValueError, match="Account not found"):
            await run_counterfactual(
                account_id=99999,
                strategy_ids=[1],
                user_id=1,
                db=mock_db,
                settings=self._make_settings(),
            )

    async def test_run_counterfactual_no_trading_history(self):
        """거래 이력이 없으면 ValueError 발생"""
        mock_db = AsyncMock()

        # 계정 조회 성공
        account_result = MagicMock()
        account_result.scalar_one_or_none.return_value = MagicMock()

        # 기간 조회 - 결과 없음
        period_result = MagicMock()
        period_result.fetchone.return_value = (None, None)

        mock_db.execute = AsyncMock(side_effect=[account_result, period_result])

        with pytest.raises(ValueError, match="No trading history found"):
            await run_counterfactual(
                account_id=1,
                strategy_ids=[1],
                user_id=1,
                db=mock_db,
                settings=self._make_settings(),
            )

    async def test_run_counterfactual_no_tickers(self):
        """거래 티커가 없으면 ValueError 발생"""
        mock_db = AsyncMock()

        # 계정 조회 성공
        account_result = MagicMock()
        account_result.scalar_one_or_none.return_value = MagicMock()

        # 기간 조회 성공
        period_result = MagicMock()
        period_result.fetchone.return_value = (date(2022, 1, 3), date(2022, 3, 31))

        # 티커 조회 - 빈 결과
        ticker_result = MagicMock()
        ticker_result.fetchall.return_value = []

        mock_db.execute = AsyncMock(side_effect=[account_result, period_result, ticker_result])

        with pytest.raises(ValueError, match="No tickers found"):
            await run_counterfactual(
                account_id=1,
                strategy_ids=[1],
                user_id=1,
                db=mock_db,
                settings=self._make_settings(),
            )

    async def test_run_counterfactual_success(self):
        """정상 시나리오 — Celery 태스크 디스패치 후 결과 반환"""
        mock_db = AsyncMock()

        # 계정 조회 성공
        account_result = MagicMock()
        account_result.scalar_one_or_none.return_value = MagicMock()

        # 기간 조회 성공
        period_result = MagicMock()
        period_result.fetchone.return_value = (date(2022, 1, 3), date(2022, 3, 31))

        # 티커 조회 성공
        ticker_result = MagicMock()
        ticker_result.fetchall.return_value = [("005930",)]

        # 가격 데이터 조회 (005930 일봉)
        price_result = MagicMock()
        price_result.fetchall.return_value = [
            (date(2022, 1, 3), 70000, 72000, 68000, 71000, 1_000_000),
        ]

        # 벤치마크 가격 조회 (069500)
        bench_result = MagicMock()
        bench_result.fetchall.return_value = []

        # 전략 조회 성공
        strat_result = MagicMock()
        strat_result.scalar_one_or_none.return_value = self._make_strategy()

        # 실제 자산 곡선 조회
        equity_result = MagicMock()
        equity_result.fetchall.return_value = [
            (date(2022, 1, 3), 10_000_000),
            (date(2022, 1, 4), 10_200_000),
        ]

        mock_db.execute = AsyncMock(side_effect=[
            account_result, period_result, ticker_result,
            price_result, bench_result,
            strat_result,
            equity_result,
        ])
        mock_db.flush = AsyncMock()
        mock_db.add = MagicMock()

        # Celery mock
        mock_task = MagicMock()
        mock_task.id = "celery-task-id-123"
        mock_celery = MagicMock()
        mock_celery.send_task.return_value = mock_task

        with patch("app.services.backtest_service._get_celery_app", return_value=mock_celery):
            result = await run_counterfactual(
                account_id=1,
                strategy_ids=[1],
                user_id=1,
                db=mock_db,
                settings=self._make_settings(),
            )

        assert result["account_id"] == 1
        assert "period" in result
        assert result["tickers"] == ["005930"]
        assert len(result["counterfactual_runs"]) == 1
        assert "actual_equity_curve" in result

    async def test_run_counterfactual_strategy_not_owned(self):
        """전략이 사용자 소유가 아닌 경우 해당 전략 건너뜀 (runs가 빈 목록)"""
        mock_db = AsyncMock()

        # 계정 조회 성공
        account_result = MagicMock()
        account_result.scalar_one_or_none.return_value = MagicMock()

        # 기간 조회 성공
        period_result = MagicMock()
        period_result.fetchone.return_value = (date(2022, 1, 3), date(2022, 3, 31))

        # 티커 조회 성공
        ticker_result = MagicMock()
        ticker_result.fetchall.return_value = [("005930",)]

        # 가격 데이터 조회
        price_result = MagicMock()
        price_result.fetchall.return_value = []

        # 벤치마크 없음
        bench_result = MagicMock()
        bench_result.fetchall.return_value = []

        # 전략 소유권 없음 (None 반환)
        strat_result = MagicMock()
        strat_result.scalar_one_or_none.return_value = None

        # 실제 자산 곡선 조회 (빈 결과)
        equity_result = MagicMock()
        equity_result.fetchall.return_value = []

        mock_db.execute = AsyncMock(side_effect=[
            account_result, period_result, ticker_result,
            price_result, bench_result,
            strat_result,
            equity_result,
        ])
        mock_db.flush = AsyncMock()
        mock_db.add = MagicMock()

        with patch("app.services.backtest_service._get_celery_app"):
            result = await run_counterfactual(
                account_id=1,
                strategy_ids=[1],
                user_id=1,
                db=mock_db,
                settings=self._make_settings(),
            )

        # 소유권 없는 전략은 건너뜀 → runs 빈 목록
        assert result["counterfactual_runs"] == []
