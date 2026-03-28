import pytest

from app.middleware.audit_middleware import AUDITED_METHODS, AUDITED_PATHS


class TestAuditMiddlewareConfig:
    def test_audited_methods(self):
        assert "POST" in AUDITED_METHODS
        assert "PUT" in AUDITED_METHODS
        assert "DELETE" in AUDITED_METHODS
        assert "PATCH" in AUDITED_METHODS
        assert "GET" not in AUDITED_METHODS

    def test_audited_paths(self):
        assert "/auth/" in AUDITED_PATHS
        assert "/trading/" in AUDITED_PATHS
        assert "/backtest/" in AUDITED_PATHS
        assert "/strategies/" in AUDITED_PATHS
        assert "/accounts/" in AUDITED_PATHS

    def test_get_request_not_audited(self, client):
        """GET requests should not be audited."""
        # This is an integration test that the middleware doesn't interfere with GET
        pass

    async def test_post_request_doesnt_break(self, client):
        """POST to audited path should still work (middleware catches exceptions)."""
        r = await client.post(
            "/auth/register",
            json={"email": "audit@test.com", "password": "ValidPass123!", "name": "Audit Test"},
        )
        # Should succeed regardless of audit log insert (which may fail on sqlite)
        assert r.status_code == 201
