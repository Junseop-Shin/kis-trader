"""
이상 감지 워커 통합 테스트
check_anomalies 함수의 개별 종목 급락, 포트폴리오 급락, 자동 매도 시나리오 검증
"""
import pytest
from unittest.mock import MagicMock, AsyncMock, patch

from app.workers.anomaly_detector import _get_price_change, check_anomalies


class TestGetPriceChange:
    """_get_price_change DB 조회 단위 테스트"""

    async def test_get_price_change_found(self):
        """가격 데이터 2행이 있으면 (current, daily_change) 반환"""
        mock_db = AsyncMock()
        mock_result = MagicMock()
        mock_result.fetchall.return_value = [(68000,), (70000,)]
        mock_db.execute = AsyncMock(return_value=mock_result)

        result = await _get_price_change("005930", mock_db)
        assert result is not None
        current, daily_change = result
        assert current == 68000.0
        assert abs(daily_change - (-0.0286)) < 0.001

    async def test_get_price_change_not_found(self):
        """가격 데이터가 없으면 None 반환"""
        mock_db = AsyncMock()
        mock_result = MagicMock()
        mock_result.fetchall.return_value = []
        mock_db.execute = AsyncMock(return_value=mock_result)

        result = await _get_price_change("999999", mock_db)
        assert result is None


class TestCheckAnomalies:
    """check_anomalies 통합 시나리오 테스트"""

    def _make_account(self, user_id=1, account_id=1, cash=9_800_000, initial=10_000_000):
        """테스트용 Account mock 객체 생성"""
        account = MagicMock()
        account.id = account_id
        account.user_id = user_id
        account.is_active = True
        account.cash_balance = cash
        account.initial_balance = initial
        account.type.value = "SIM"
        return account

    def _make_position(self, ticker="005930", qty=10, avg_price=70000):
        """테스트용 Position mock 객체 생성"""
        pos = MagicMock()
        pos.ticker = ticker
        pos.qty = qty
        pos.avg_price = float(avg_price)
        pos.current_price = float(avg_price)
        pos.unrealized_pnl = 0.0
        return pos

    async def test_check_anomalies_no_active_accounts(self):
        """활성화된 계정이 없으면 아무 작업도 수행하지 않음"""
        # MagicMock으로 scalars().all() 체인 올바르게 설정
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        mock_session = AsyncMock()
        mock_session.execute = AsyncMock(return_value=mock_result)
        mock_session.commit = AsyncMock()

        mock_cm = AsyncMock()
        mock_cm.__aenter__.return_value = mock_session
        mock_cm.__aexit__.return_value = None

        with patch("app.workers.anomaly_detector.async_session_factory", return_value=mock_cm):
            await check_anomalies()

        mock_session.commit.assert_awaited_once()

    async def test_check_anomalies_user_not_found(self):
        """계정 존재하지만 사용자 정보 없을 때 해당 계정 건너뜀"""
        account = self._make_account()

        # 계정 목록 조회 결과 (MagicMock으로 scalars 체인 처리)
        acct_result = MagicMock()
        acct_result.scalars.return_value.all.return_value = [account]

        # 사용자 정보 없음
        user_result = MagicMock()
        user_result.fetchone.return_value = None

        mock_session = AsyncMock()
        mock_session.execute = AsyncMock(side_effect=[acct_result, user_result])
        mock_session.commit = AsyncMock()

        mock_cm = AsyncMock()
        mock_cm.__aenter__.return_value = mock_session
        mock_cm.__aexit__.return_value = None

        with patch("app.workers.anomaly_detector.async_session_factory", return_value=mock_cm):
            await check_anomalies()

        mock_session.commit.assert_awaited_once()

    async def test_check_anomalies_alert_disabled(self):
        """사용자 설정에서 anomaly_alert=False이면 포지션 체크 건너뜀"""
        account = self._make_account()

        acct_result = MagicMock()
        acct_result.scalars.return_value.all.return_value = [account]

        # 사용자: anomaly_alert 비활성화
        user_result = MagicMock()
        user_result.fetchone.return_value = ({"anomaly_alert": False}, "https://slack.webhook")

        mock_session = AsyncMock()
        mock_session.execute = AsyncMock(side_effect=[acct_result, user_result])
        mock_session.commit = AsyncMock()

        mock_cm = AsyncMock()
        mock_cm.__aenter__.return_value = mock_session
        mock_cm.__aexit__.return_value = None

        with patch("app.workers.anomaly_detector.async_session_factory", return_value=mock_cm):
            await check_anomalies()

        mock_session.commit.assert_awaited_once()

    async def test_check_anomalies_normal_position_no_alert(self):
        """정상 가격 변동(임계값 미달) 시 알림 없음"""
        # 포트폴리오 급락 방지: 초기 잔액 대비 현금 잔액 충분하게 설정
        account = self._make_account(cash=9_800_000, initial=10_000_000)
        position = self._make_position(avg_price=70000)

        acct_result = MagicMock()
        acct_result.scalars.return_value.all.return_value = [account]

        # 사용자 설정: 기본값
        user_result = MagicMock()
        user_result.fetchone.return_value = (
            {"anomaly_alert": True, "crash_threshold": -0.05, "portfolio_crash_threshold": -0.15},
            "https://slack.webhook"
        )

        # 포지션 목록
        pos_result = MagicMock()
        pos_result.scalars.return_value.all.return_value = [position]

        # 현재 가격: 정상 (70000 → 68000, -2.8% — 임계값 -5% 미달)
        price_result = MagicMock()
        price_result.fetchall.return_value = [(68000,), (70000,)]

        mock_session = AsyncMock()
        mock_session.execute = AsyncMock(side_effect=[acct_result, user_result, pos_result, price_result])
        mock_session.commit = AsyncMock()

        mock_cm = AsyncMock()
        mock_cm.__aenter__.return_value = mock_session
        mock_cm.__aexit__.return_value = None

        with patch("app.workers.anomaly_detector.async_session_factory", return_value=mock_cm):
            with patch("app.workers.anomaly_detector.SlackService") as mock_slack_cls:
                await check_anomalies()

        # 임계값 미달이므로 Slack 알림 없음
        mock_slack_cls.assert_not_called()

    async def test_check_anomalies_crash_detection_alert_only(self):
        """개별 종목 급락 감지 — auto_sell=False 시 알림만 전송"""
        account = self._make_account(cash=9_800_000, initial=10_000_000)
        position = self._make_position(avg_price=70000)

        acct_result = MagicMock()
        acct_result.scalars.return_value.all.return_value = [account]

        # 사용자 설정: auto_sell 비활성화, 포트폴리오 임계값을 낮게 설정
        user_result = MagicMock()
        user_result.fetchone.return_value = (
            {"anomaly_alert": True, "crash_threshold": -0.05, "auto_sell_on_crash": False, "portfolio_crash_threshold": -0.50},
            "https://hooks.slack.com/test"
        )

        # 포지션 목록
        pos_result = MagicMock()
        pos_result.scalars.return_value.all.return_value = [position]

        # 현재 가격: 급락 (70000 → 63000, -10% — 임계값 -5% 초과)
        price_result = MagicMock()
        price_result.fetchall.return_value = [(63000,), (70000,)]

        mock_session = AsyncMock()
        mock_session.execute = AsyncMock(side_effect=[acct_result, user_result, pos_result, price_result])
        mock_session.commit = AsyncMock()

        mock_cm = AsyncMock()
        mock_cm.__aenter__.return_value = mock_session
        mock_cm.__aexit__.return_value = None

        with patch("app.workers.anomaly_detector.async_session_factory", return_value=mock_cm):
            with patch("app.workers.anomaly_detector.SlackService") as mock_slack_cls:
                mock_slack_instance = MagicMock()
                mock_slack_cls.return_value = mock_slack_instance
                await check_anomalies()

        # 알림 전송 확인
        mock_slack_instance.send_anomaly_alert.assert_called_once()
        call_args = mock_slack_instance.send_anomaly_alert.call_args
        assert call_args[0][0] == "005930"

    async def test_check_anomalies_auto_sell_on_crash(self):
        """개별 종목 급락 + auto_sell=True → SIM 계정 자동 매도 실행"""
        account = self._make_account(cash=9_800_000, initial=10_000_000)
        position = self._make_position(avg_price=70000)

        acct_result = MagicMock()
        acct_result.scalars.return_value.all.return_value = [account]

        # 사용자 설정: auto_sell 활성화, 포트폴리오 임계값 낮게 설정
        user_result = MagicMock()
        user_result.fetchone.return_value = (
            {"anomaly_alert": True, "crash_threshold": -0.05, "auto_sell_on_crash": True, "portfolio_crash_threshold": -0.50},
            "https://hooks.slack.com/test"
        )

        # 포지션 목록
        pos_result = MagicMock()
        pos_result.scalars.return_value.all.return_value = [position]

        # 현재 가격: 급락
        price_result = MagicMock()
        price_result.fetchall.return_value = [(63000,), (70000,)]

        mock_session = AsyncMock()
        mock_session.execute = AsyncMock(side_effect=[acct_result, user_result, pos_result, price_result])
        mock_session.commit = AsyncMock()

        mock_cm = AsyncMock()
        mock_cm.__aenter__.return_value = mock_session
        mock_cm.__aexit__.return_value = None

        with patch("app.workers.anomaly_detector.async_session_factory", return_value=mock_cm):
            with patch("app.workers.anomaly_detector.SlackService") as mock_slack_cls:
                with patch("app.workers.anomaly_detector.place_sim_order", new_callable=AsyncMock) as mock_place:
                    mock_slack_instance = MagicMock()
                    mock_slack_cls.return_value = mock_slack_instance
                    await check_anomalies()

        # 자동 매도 주문 실행 확인
        mock_place.assert_awaited_once()
        # Slack 알림 확인
        mock_slack_instance.send_anomaly_alert.assert_called_once()

    async def test_check_anomalies_portfolio_crash(self):
        """포트폴리오 전체 급락 → 포트폴리오 레벨 알림 전송"""
        # 초기 자산 10M, 현재 현금 1M + 포지션 시가 1M = 총 2M → -80% (임계값 -10% 초과)
        account = self._make_account(cash=1_000_000, initial=10_000_000)

        acct_result = MagicMock()
        acct_result.scalars.return_value.all.return_value = [account]

        # 사용자 설정: 포트폴리오 임계값 -10%, 개별 임계값 낮게 설정
        user_result = MagicMock()
        user_result.fetchone.return_value = (
            {"anomaly_alert": True, "crash_threshold": -0.90, "portfolio_crash_threshold": -0.10},
            "https://hooks.slack.com/test"
        )

        # 포지션 있음: avg_price=70000, qty=10 → total_invested=700000
        position = self._make_position(avg_price=70000, qty=10)
        pos_result = MagicMock()
        pos_result.scalars.return_value.all.return_value = [position]

        # 현재 가격: 10000 (급락하지만 개별 임계값(-90%)은 초과하지 않도록)
        price_result = MagicMock()
        price_result.fetchall.return_value = [(10000,), (70000,)]  # -85.7% → 임계값 -90% 이하 → 개별 알림 없음

        mock_session = AsyncMock()
        mock_session.execute = AsyncMock(side_effect=[acct_result, user_result, pos_result, price_result])
        mock_session.commit = AsyncMock()

        mock_cm = AsyncMock()
        mock_cm.__aenter__.return_value = mock_session
        mock_cm.__aexit__.return_value = None

        with patch("app.workers.anomaly_detector.async_session_factory", return_value=mock_cm):
            with patch("app.workers.anomaly_detector.SlackService") as mock_slack_cls:
                mock_slack_instance = MagicMock()
                mock_slack_cls.return_value = mock_slack_instance
                await check_anomalies()

        # 포트폴리오 알림 전송 확인
        mock_slack_instance.send_anomaly_alert.assert_called_once()
        call_args = mock_slack_instance.send_anomaly_alert.call_args
        assert call_args[0][0] == "PORTFOLIO"

    async def test_check_anomalies_no_price_for_position(self):
        """포지션 현재가 조회 결과 없을 때(None) 해당 포지션 건너뜀"""
        account = self._make_account(cash=9_800_000, initial=10_000_000)
        position = self._make_position(avg_price=70000)

        acct_result = MagicMock()
        acct_result.scalars.return_value.all.return_value = [account]

        user_result = MagicMock()
        user_result.fetchone.return_value = (
            {"anomaly_alert": True, "crash_threshold": -0.05, "portfolio_crash_threshold": -0.15},
            "https://hooks.slack.com/test"
        )

        pos_result = MagicMock()
        pos_result.scalars.return_value.all.return_value = [position]

        # 현재가 없음 → None 반환 → 포지션 건너뜀 (line 82 커버)
        price_result = MagicMock()
        price_result.fetchall.return_value = []

        mock_session = AsyncMock()
        mock_session.execute = AsyncMock(side_effect=[acct_result, user_result, pos_result, price_result])
        mock_session.commit = AsyncMock()

        mock_cm = AsyncMock()
        mock_cm.__aenter__.return_value = mock_session
        mock_cm.__aexit__.return_value = None

        with patch("app.workers.anomaly_detector.async_session_factory", return_value=mock_cm):
            with patch("app.workers.anomaly_detector.SlackService") as mock_slack_cls:
                await check_anomalies()

        # 가격 없음 → 알림 없음
        mock_slack_cls.assert_not_called()

    async def test_check_anomalies_auto_sell_exception(self):
        """auto_sell=True이나 place_sim_order 예외 발생 → action에 에러 메시지 포함"""
        account = self._make_account(cash=9_800_000, initial=10_000_000)
        position = self._make_position(avg_price=70000)

        acct_result = MagicMock()
        acct_result.scalars.return_value.all.return_value = [account]

        user_result = MagicMock()
        user_result.fetchone.return_value = (
            {"anomaly_alert": True, "crash_threshold": -0.05, "auto_sell_on_crash": True, "portfolio_crash_threshold": -0.50},
            "https://hooks.slack.com/test"
        )

        pos_result = MagicMock()
        pos_result.scalars.return_value.all.return_value = [position]

        # 현재가: 급락 (70000 → 63000, -10%)
        price_result = MagicMock()
        price_result.fetchall.return_value = [(63000,), (70000,)]

        mock_session = AsyncMock()
        mock_session.execute = AsyncMock(side_effect=[acct_result, user_result, pos_result, price_result])
        mock_session.commit = AsyncMock()

        mock_cm = AsyncMock()
        mock_cm.__aenter__.return_value = mock_session
        mock_cm.__aexit__.return_value = None

        with patch("app.workers.anomaly_detector.async_session_factory", return_value=mock_cm):
            with patch("app.workers.anomaly_detector.SlackService") as mock_slack_cls:
                with patch("app.workers.anomaly_detector.place_sim_order", new_callable=AsyncMock) as mock_place:
                    mock_place.side_effect = Exception("Insufficient funds")
                    mock_slack_instance = MagicMock()
                    mock_slack_cls.return_value = mock_slack_instance
                    await check_anomalies()

        # 자동 매도 실패해도 Slack 알림은 전송됨 (lines 106-107 커버)
        mock_slack_instance.send_anomaly_alert.assert_called_once()
        call_args = mock_slack_instance.send_anomaly_alert.call_args
        # action_taken 인자(3번째 위치)에 실패 메시지 포함
        action_arg = call_args[0][2] if len(call_args[0]) > 2 else call_args.kwargs.get("action_taken", "")
        assert "failed" in action_arg.lower() or "auto-sell" in action_arg.lower()

    async def test_check_anomalies_exception_handling(self):
        """계정 처리 중 예외 발생 시 다음 계정으로 계속 진행"""
        account1 = self._make_account(account_id=1)
        account2 = self._make_account(account_id=2)

        acct_result = MagicMock()
        acct_result.scalars.return_value.all.return_value = [account1, account2]

        # account1 처리 시 사용자 조회 에러 발생
        user_result_error = MagicMock()
        user_result_error.fetchone.side_effect = Exception("DB connection error")

        # account2는 사용자 없음 → 건너뜀
        user_result_ok = MagicMock()
        user_result_ok.fetchone.return_value = None

        mock_session = AsyncMock()
        mock_session.execute = AsyncMock(side_effect=[acct_result, user_result_error, user_result_ok])
        mock_session.commit = AsyncMock()

        mock_cm = AsyncMock()
        mock_cm.__aenter__.return_value = mock_session
        mock_cm.__aexit__.return_value = None

        with patch("app.workers.anomaly_detector.async_session_factory", return_value=mock_cm):
            # 예외가 전파되지 않아야 함 (try-except로 처리)
            await check_anomalies()

        mock_session.commit.assert_awaited_once()
