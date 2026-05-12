"""Tests for the core tdx_tool module."""
import pytest
from unittest.mock import Mock, patch, MagicMock
import logging
import requests
import time

from src.tdx_tool.core import tdx_tool
from src.tdx_tool.authority import tdx_auth


class TestTdxTool:
    """Test suite for tdx_tool base class."""

    @pytest.fixture
    def tdx_instance(self, test_credentials, mock_token, mock_logger):
        """Create a tdx_tool instance with mocked auth."""
        with patch('src.tdx_tool.core.tdx_auth') as MockAuth:
            mock_auth = Mock(spec=tdx_auth)
            mock_auth.token = mock_token["access_token"]
            MockAuth.return_value = mock_auth

            instance = tdx_tool(
                client_id=test_credentials["client_id"],
                client_key=test_credentials["client_key"],
                logger=mock_logger
            )
            instance.auth = mock_auth
            return instance

    def test_initialization(self, tdx_instance, mock_logger):
        """Test tdx_tool initialization."""
        assert tdx_instance.logger is not None
        assert tdx_instance.default_coor == "EPSG:4326"
        assert tdx_instance.output_path == "output"
        assert tdx_instance.export_result is False

    def test_export_result_setter_valid(self, tdx_instance):
        """Test export_result property setter with valid boolean."""
        tdx_instance.export_result = True
        assert tdx_instance.export_result is True

        tdx_instance.export_result = False
        assert tdx_instance.export_result is False

    def test_export_result_setter_invalid(self, tdx_instance):
        """Test export_result property setter with invalid input."""
        with pytest.raises(ValueError, match="must be a boolean"):
            tdx_instance.export_result = "true"

        with pytest.raises(ValueError, match="must be a boolean"):
            tdx_instance.export_result = 1

    def test_default_coor_setter_valid(self, tdx_instance):
        """Test default_coor property setter with valid EPSG codes."""
        tdx_instance.default_coor = "EPSG:3826"  # Taiwan Zone
        assert tdx_instance.default_coor == "EPSG:3826"

    def test_default_coor_setter_invalid(self, tdx_instance):
        """Test default_coor property setter with invalid CRS."""
        with pytest.raises(ValueError, match="Invalid coordinate reference system"):
            tdx_instance.default_coor = "INVALID:9999"

    def test_output_path_setter_valid(self, tdx_instance):
        """Test output_path property setter with valid path."""
        tdx_instance.output_path = "/tmp/results"
        assert tdx_instance.output_path == "/tmp/results"

    def test_output_path_setter_invalid(self, tdx_instance):
        """Test output_path property setter with invalid input."""
        with pytest.raises(ValueError, match="must be a string"):
            tdx_instance.output_path = 123

    def test_auth_header_property(self, tdx_instance, mock_token):
        """Test auth_header property generation."""
        auth_header = tdx_instance.auth_header
        assert auth_header["Authorization"] == f"Bearer {mock_token['access_token']}"
        assert auth_header["Accept"] == "gzip"

    def test_get_data_from_suffix_url_success(self, tdx_instance):
        """Test successful data retrieval from API."""
        with patch('src.tdx_tool.core.requests.get') as mock_get:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = {"data": [{"id": 1}]}
            mock_response.raise_for_status.return_value = None
            mock_get.return_value = mock_response

            response = tdx_instance._get_data_from_suffix_url("v3/Bus/Route/City/Taipei")

            assert response.status_code == 200
            mock_get.assert_called_once()

    def test_get_data_retry_on_401_unauthorized(self, tdx_instance):
        """Test automatic token refresh and retry on 401 error."""
        with patch('src.tdx_tool.core.requests.get') as mock_get, \
             patch.object(tdx_instance.auth, 'update_token') as mock_refresh:

            # First call returns 401, second call should succeed
            error_response = Mock()
            error_response.status_code = 401
            error_response.raise_for_status.side_effect = requests.HTTPError(response=error_response)

            success_response = Mock()
            success_response.status_code = 200
            success_response.json.return_value = {"data": []}
            success_response.raise_for_status.return_value = None

            mock_get.side_effect = [
                requests.HTTPError(response=error_response),
                success_response
            ]
            mock_refresh.return_value = "new_token"

            response = tdx_instance._get_data_from_suffix_url("test/url")

            assert response.status_code == 200
            mock_refresh.assert_called_once()

    def test_get_data_retry_on_429_rate_limit(self, tdx_instance):
        """Test exponential backoff retry on 429 rate limit error."""
        with patch('src.tdx_tool.core.requests.get') as mock_get, \
             patch('src.tdx_tool.core.time.sleep') as mock_sleep:

            error_response = Mock()
            error_response.status_code = 429
            error_response.raise_for_status.side_effect = requests.HTTPError(response=error_response)

            success_response = Mock()
            success_response.status_code = 200
            success_response.json.return_value = {"data": []}
            success_response.raise_for_status.return_value = None

            mock_get.side_effect = [
                requests.HTTPError(response=error_response),
                requests.HTTPError(response=error_response),
                success_response
            ]

            response = tdx_instance._get_data_from_suffix_url("test/url", counter=2)

            assert response.status_code == 200
            # Should have exponential backoff calls
            assert mock_sleep.call_count >= 1

    def test_get_data_max_retries_exceeded(self, tdx_instance):
        """Test that request fails after max retries."""
        with patch('src.tdx_tool.core.requests.get') as mock_get:
            error_response = Mock()
            error_response.status_code = 429
            error_response.raise_for_status.side_effect = requests.HTTPError(response=error_response)

            mock_get.side_effect = requests.HTTPError(response=error_response)

            with pytest.raises(requests.HTTPError):
                tdx_instance._get_data_from_suffix_url("test/url", counter=0)

    def test_url_middle_part_not_implemented(self, tdx_instance):
        """Test that _url_middle_part raises NotImplementedError in base class."""
        with pytest.raises(NotImplementedError):
            tdx_instance._url_middle_part()
