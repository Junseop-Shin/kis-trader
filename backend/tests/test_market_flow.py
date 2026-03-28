"""
시장 데이터 흐름 통합 테스트
종목 조회, 스크리닝, 가격/지표 데이터 API 검증
SQLite에서는 Lateral Join 등 PostgreSQL 전용 문법이 동작하지 않으므로,
기본 종목 목록 조회 및 인증 관련 로직 위주로 테스트
"""
import pytest
from datetime import date

from sqlalchemy import text
from app.models.market import Stock, PriceDaily
from tests.conftest import user_auth_header


class TestMarketFlow:
    """시장 데이터 조회 흐름 통합 테스트"""

    @pytest.fixture(autouse=True)
    async def seed_market_data(self, db_session):
        """테스트용 종목 및 가격 데이터 시드"""
        # 종목 등록
        stock1 = Stock(
            ticker="005930", name="Samsung Electronics",
            market="KOSPI", sector="Electronics", is_active=True
        )
        stock2 = Stock(
            ticker="000660", name="SK Hynix",
            market="KOSPI", sector="Semiconductors", is_active=True
        )
        stock3 = Stock(
            ticker="035720", name="Kakao",
            market="KOSPI", sector="IT", is_active=True
        )
        db_session.add_all([stock1, stock2, stock3])
        await db_session.flush()

        # 가격 데이터 시드 (60 거래일 — 고유 날짜)
        # SQLite에서 BigInteger PK는 autoincrement가 안 되므로 id를 직접 지정
        import random
        from datetime import timedelta
        random.seed(42)
        base_price = 70000
        current_date = date(2023, 1, 2)
        for i in range(60):
            price = base_price + random.randint(-2000, 2000)
            pd_entry = PriceDaily(
                id=i + 1,
                ticker="005930",
                date=current_date,
                open=price - 500,
                high=price + 1000,
                low=price - 1000,
                close=price,
                volume=random.randint(1000000, 5000000),
                change_pct=random.uniform(-3.0, 3.0),
            )
            db_session.add(pd_entry)
            current_date += timedelta(days=1)

        await db_session.commit()

    async def test_unauthenticated_stock_list(self, client):
        """인증 없이 종목 목록 조회 시 401 에러"""
        r = await client.get("/market/stocks")
        assert r.status_code == 401

    async def test_list_stocks_basic(self, client, test_user, user_token):
        """기본 종목 목록 조회 - 인증 필요"""
        r = await client.get(
            "/market/stocks",
            headers=user_auth_header(user_token),
        )
        assert r.status_code == 200
        data = r.json()
        assert "items" in data
        assert "total" in data
        assert data["total"] >= 3

    async def test_list_stocks_with_market_filter(self, client, test_user, user_token):
        """마켓(KOSPI/KOSDAQ) 필터 적용 종목 조회"""
        r = await client.get(
            "/market/stocks?market=KOSPI",
            headers=user_auth_header(user_token),
        )
        assert r.status_code == 200
        data = r.json()
        for item in data["items"]:
            assert item["market"] == "KOSPI"

    async def test_list_stocks_with_search(self, client, test_user, user_token):
        """종목명/코드 검색 필터"""
        r = await client.get(
            "/market/stocks?search=Samsung",
            headers=user_auth_header(user_token),
        )
        assert r.status_code == 200
        data = r.json()
        assert data["total"] >= 1

    async def test_list_stocks_pagination(self, client, test_user, user_token):
        """종목 목록 페이지네이션"""
        r = await client.get(
            "/market/stocks?limit=2&offset=0",
            headers=user_auth_header(user_token),
        )
        assert r.status_code == 200
        data = r.json()
        assert len(data["items"]) <= 2

    async def test_get_stock_price_1d(self, client, test_user, user_token):
        """일봉 가격 데이터 조회"""
        r = await client.get(
            "/market/stocks/005930/price?timeframe=1D",
            headers=user_auth_header(user_token),
        )
        assert r.status_code == 200
        prices = r.json()
        assert len(prices) > 0
        # 각 항목에 OHLCV 필드가 있어야 함
        first = prices[0]
        assert "open" in first
        assert "high" in first
        assert "low" in first
        assert "close" in first
        assert "volume" in first

    async def test_get_stock_price_nonexistent_ticker(self, client, test_user, user_token):
        """존재하지 않는 종목 가격 조회 시 404 에러"""
        r = await client.get(
            "/market/stocks/999999/price",
            headers=user_auth_header(user_token),
        )
        assert r.status_code == 404

    async def test_get_indicators_ma(self, client, test_user, user_token):
        """이동평균(MA) 기술 지표 조회"""
        r = await client.get(
            "/market/stocks/005930/indicators?indicators=ma&ma_periods=5,20",
            headers=user_auth_header(user_token),
        )
        assert r.status_code == 200
        data = r.json()
        assert "dates" in data
        assert "sma_5" in data
        assert "sma_20" in data

    async def test_get_indicators_no_data(self, client, test_user, user_token):
        """데이터가 없는 종목의 지표 요청 시 404 에러"""
        r = await client.get(
            "/market/stocks/999999/indicators",
            headers=user_auth_header(user_token),
        )
        assert r.status_code == 404

    async def test_list_sectors(self, client, test_user, user_token):
        """섹터 목록 조회"""
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
