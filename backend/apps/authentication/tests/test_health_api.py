import pytest
from rest_framework import status
from rest_framework.test import APIClient


@pytest.mark.django_db
class TestHealthCheckAPI:
    """Verifies production container healthcheck probes for container orchestrators."""

    def test_health_check_api_endpoint(self):
        client = APIClient()
        res = client.get('/api/v1/health/')
        assert res.status_code == status.HTTP_200_OK
        data = res.json()
        assert data['status'] == 'healthy'
        assert data['version'] == '1.0.0'
        assert 'services' in data
        assert data['services']['database']['status'] == 'connected'

    def test_health_check_root_endpoint(self):
        client = APIClient()
        res = client.get('/health/')
        assert res.status_code == status.HTTP_200_OK
        data = res.json()
        assert data['status'] == 'healthy'
        assert data['services']['database']['status'] == 'connected'
