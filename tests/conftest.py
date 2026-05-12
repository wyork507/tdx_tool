"""Pytest configuration and shared fixtures."""
import logging
import pytest
from unittest.mock import Mock, MagicMock, patch
from datetime import datetime, timedelta


@pytest.fixture
def mock_logger():
    """Create a mock logger for testing."""
    return Mock(spec=logging.Logger)


@pytest.fixture
def test_credentials():
    """Provide test API credentials."""
    return {
        "client_id": "test_client_id",
        "client_key": "test_client_key"
    }


@pytest.fixture
def mock_token():
    """Mock token response from TDX API."""
    return {
        "access_token": "mock_token_abc123xyz",
        "expires_in": 3600,
        "token_type": "Bearer",
        "scope": "read"
    }


@pytest.fixture
def mock_bus_response():
    """Mock API response for bus routes."""
    return {
        "data": [
            {
                "RouteUID": "Taipei/1",
                "BusRouteType": 1,
                "RouteName": {
                    "Zh_tw": "台北101-南港",
                    "En": "Taipei101-Nangang"
                },
                "Operators": [
                    {
                        "OperatorID": "TMBUS",
                        "OperatorName": {
                            "Zh_tw": "台北公運",
                            "En": "Taipei Bus"
                        }
                    }
                ],
                "DepartureStopNameZh": "台北101",
                "DepartureStopNameEn": "Taipei101",
                "DestinationStopNameZh": "南港", 
                "DestinationStopNameEn": "Nangang",
                "SubRoutes": [
                    {
                        "SubRouteUID": "Taipei/1/1",
                        "SubRouteID": "1",
                        "Direction": 0,
                        "SubRouteName": {
                            "Zh_tw": "往南港",
                            "En": "To Nangang"
                        },
                        "DepartureStopNameZh": "台北101",
                        "DepartureStopNameEn": "Taipei101",
                        "DestinationStopNameZh": "南港",
                        "DestinationStopNameEn": "Nangang"
                    }
                ],
                "UpdateTime": "2024-01-01T10:00:00+08:00"
            }
        ]
    }
