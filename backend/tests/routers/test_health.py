import pytest


class TestHealth:
    async def test_health_endpoint(self, client):
        r = await client.get("/health")
        assert r.status_code == 200
        data = r.json()
        assert data["status"] == "ok"
        assert data["version"] == "3.0.0"
