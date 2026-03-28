"""
시장 데이터 확장 통합 테스트
RSI/MACD/볼린저밴드 지표, 주간/월간 가격 리샘플링, 섹터 필터 등
"""
import pytest
from datetime import date, timedelta
import random

from app.models.market import Stock, PriceDaily
from tests.conftest import user_auth_header


@pytest.fixture(autouse=True)
async def seed_extended_market_data(db_session):
    """충분한 가격 데이터(120거래일)로 기술 지표 계산 가능하도록 시드"""
    stocks = [
        Stock(ticker="005930", name="Samsung Electronics", market="KOSPI", sector="Electronics", is_active=True),
        Stock(ticker="000660", name="SK Hynix", market="KOSPI", sector="Semiconductors", is_active=True),
        Stock(ticker="035720", name="Kakao", market="KOSDAQ", sector="IT", is_active=True),
    ]
    db_session.add_all(stocks)
    await db_session.flush()

    # 120거래일치 가격 시드 — RSI(14), MACD(26), BB(20) 계산에 충분
    random.seed(99)
    base = 70000
    current_date = date(2023, 1, 2)
    price_id = 1001
    for i in range(120):
        price = base + random.randint(-3000, 3000)
        entry = PriceDaily(
            id=price_id,
            ticker="005930",
            date=current_date,
            open=price - 500,
            high=price + 1000,
            low=price - 1000,
            close=price,
            volume=random.randint(1_000_000, 5_000_000),
            change_pct=random.uniform(-3.0, 3.0),
        )
        db_session.add(entry)
        current_date += timedelta(days=1)
        price_id += 1

    await db_session.commit()


class TestIndicatorTypes:
    """RSI, MACD, 볼린저밴드 기술 지표 API 테스트"""

    async def test_rsi_indicator(self, client, test_user, user_token):
        """RSI(14) 지표 계산 후 응답 구조 검증"""
        r = await client.get(
            "/market/stocks/005930/indicators?indicators=rsi",
            headers=user_auth_header(user_token),
        )
        assert r.status_code == 200
        data = r.json()
        assert "dates" in data
        assert "rsi_14" in data
        # 앞부분은 None (lookback 기간), 이후엔 숫자 값
        non_null = [v for v in data["rsi_14"] if v is not None]
        assert len(non_null) > 0

    async def test_macd_indicator(self, client, test_user, user_token):
        """MACD(12,26,9) 지표 계산 후 macd/signal/hist 모두 반환"""
        r = await client.get(
            "/market/stocks/005930/indicators?indicators=macd",
            headers=user_auth_header(user_token),
        )
        assert r.status_code == 200
        data = r.json()
        assert "macd" in data
        assert "macd_signal" in data
        assert "macd_hist" in data
        assert "dates" in data

    async def test_bbands_indicator(self, client, test_user, user_token):
        """볼린저밴드(20, 2.0) 지표 — 상/중/하 밴드 반환 검증"""
        r = await client.get(
            "/market/stocks/005930/indicators?indicators=bbands",
            headers=user_auth_header(user_token),
        )
        assert r.status_code == 200
        data = r.json()
        assert "bb_upper" in data
        assert "bb_middle" in data
        assert "bb_lower" in data

    async def test_multiple_indicators(self, client, test_user, user_token):
        """ma,rsi,macd,bbands 복합 지표 조회 시 모두 포함되어야 함"""
        r = await client.get(
            "/market/stocks/005930/indicators?indicators=ma,rsi,macd,bbands&ma_periods=5,20",
            headers=user_auth_header(user_token),
        )
        assert r.status_code == 200
        data = r.json()
        assert "sma_5" in data
        assert "sma_20" in data
        assert "rsi_14" in data
        assert "macd" in data
        assert "bb_upper" in data

    async def test_indicators_with_date_range(self, client, test_user, user_token):
        """날짜 범위 필터와 함께 지표 조회"""
        r = await client.get(
            "/market/stocks/005930/indicators?indicators=ma&start=2023-02-01&end=2023-03-31",
            headers=user_auth_header(user_token),
        )
        assert r.status_code == 200
        data = r.json()
        assert "dates" in data
        assert "sma_5" in data

    async def test_indicators_unknown_not_included(self, client, test_user, user_token):
        """알 수 없는 지표 요청 시 dates만 반환되고 에러 없음"""
        r = await client.get(
            "/market/stocks/005930/indicators?indicators=unknown_indicator",
            headers=user_auth_header(user_token),
        )
        assert r.status_code == 200
        data = r.json()
        assert "dates" in data


class TestPriceTimeframes:
    """주간/월간 가격 리샘플링 테스트"""

    async def test_weekly_price_resampling(self, client, test_user, user_token):
        """주간(1W) 가격 리샘플링 — 일봉 데이터보다 레코드 수 적어야 함"""
        r_daily = await client.get(
            "/market/stocks/005930/price?timeframe=1D",
            headers=user_auth_header(user_token),
        )
        r_weekly = await client.get(
            "/market/stocks/005930/price?timeframe=1W",
            headers=user_auth_header(user_token),
        )
        assert r_daily.status_code == 200
        assert r_weekly.status_code == 200
        daily_prices = r_daily.json()
        weekly_prices = r_weekly.json()
        # 주간 집계 → 레코드 수가 일봉보다 적어야 함
        assert len(weekly_prices) < len(daily_prices)
        # OHLCV 필드 구조 검증
        if weekly_prices:
            first = weekly_prices[0]
            assert all(k in first for k in ["open", "high", "low", "close", "volume"])

    async def test_monthly_price_resampling(self, client, test_user, user_token):
        """월간(1M) 가격 리샘플링 — 주간보다 레코드 수 적어야 함"""
        r_weekly = await client.get(
            "/market/stocks/005930/price?timeframe=1W",
            headers=user_auth_header(user_token),
        )
        r_monthly = await client.get(
            "/market/stocks/005930/price?timeframe=1M",
            headers=user_auth_header(user_token),
        )
        assert r_weekly.status_code == 200
        assert r_monthly.status_code == 200
        # 월봉 레코드 수 <= 주봉 레코드 수
        assert len(r_monthly.json()) <= len(r_weekly.json())

    async def test_price_with_date_filter(self, client, test_user, user_token):
        """날짜 범위 필터와 함께 가격 조회"""
        r = await client.get(
            "/market/stocks/005930/price?start=2023-02-01&end=2023-02-28",
            headers=user_auth_header(user_token),
        )
        assert r.status_code == 200
        prices = r.json()
        # 2월 데이터만 반환
        for p in prices:
            assert p["date"] >= "2023-02-01"
            assert p["date"] <= "2023-02-28"

    async def test_price_nonexistent_returns_404(self, client, test_user, user_token):
        """데이터 없는 종목 가격 요청 → 404"""
        r = await client.get(
            "/market/stocks/999999/price",
            headers=user_auth_header(user_token),
        )
        assert r.status_code == 404

    async def test_price_unauthenticated(self, client):
        """인증 없이 가격 요청 → 401"""
        r = await client.get("/market/stocks/005930/price")
        assert r.status_code == 401


class TestStockFilters:
    """종목 검색 및 섹터 필터 테스트"""

    async def test_sector_filter(self, client, test_user, user_token):
        """섹터 필터 — 해당 섹터 종목만 반환"""
        r = await client.get(
            "/market/stocks?sector=Electronics",
            headers=user_auth_header(user_token),
        )
        assert r.status_code == 200
        data = r.json()
        assert data["total"] >= 1
        for item in data["items"]:
            assert item["sector"] == "Electronics"

    async def test_stock_list_with_sector_filter_no_match(self, client, test_user, user_token):
        """존재하지 않는 섹터 조회 → 빈 목록"""
        r = await client.get(
            "/market/stocks?sector=NonExistentSector",
            headers=user_auth_header(user_token),
        )
        assert r.status_code == 200
        data = r.json()
        assert data["total"] == 0

    async def test_sectors_list(self, client, test_user, user_token):
        """섹터 목록 조회 — stock_count 포함"""
        r = await client.get(
            "/market/sectors",
            headers=user_auth_header(user_token),
        )
        assert r.status_code == 200
        sectors = r.json()
        assert len(sectors) >= 1
        for s in sectors:
            assert "sector" in s
            assert "stock_count" in s
            assert s["stock_count"] > 0
