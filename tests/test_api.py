# ============================================================================
# API Endpoint Tests
# ============================================================================
import pytest
from httpx import AsyncClient

class TestHealthEndpoint:
    """Tests for health check endpoint"""
    
    @pytest.mark.asyncio
    async def test_health_check(self, client: AsyncClient):
        """Test health check returns OK"""
        response = await client.get("/health")
        
        assert response.status_code == 200
        assert response.json()["status"] == "healthy"

class TestAuthEndpoints:
    """Tests for authentication endpoints"""
    
    @pytest.mark.asyncio
    async def test_request_otp(self, client: AsyncClient):
        """Test OTP request"""
        response = await client.post(
            "/api/v1/auth/phone/request-otp",
            json={"phone_number": "+263771234567"}
        )
        
        assert response.status_code == 200
        assert "message" in response.json()
    
    @pytest.mark.asyncio
    async def test_invalid_phone_number(self, client: AsyncClient):
        """Test OTP request with invalid phone"""
        response = await client.post(
            "/api/v1/auth/phone/request-otp",
            json={"phone_number": "invalid"}
        )
        
        assert response.status_code == 422  # Validation error

class TestPracticeEndpoints:
    """Tests for practice endpoints"""
    
    @pytest.mark.asyncio
    async def test_start_session_unauthorized(self, client: AsyncClient):
        """Test starting session without auth"""
        response = await client.post(
            "/api/v1/practice/start",
            json={"num_questions": 5}
        )
        
        # Should require authentication
        assert response.status_code == 401 or response.status_code == 403
