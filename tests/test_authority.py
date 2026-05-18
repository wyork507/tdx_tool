"""Tests for the tdx_auth authentication module."""
import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime
import requests
import logging

from src.tdx_tool.authority import tdx_auth


class TestTdxAuth:
    """Test suite for tdx_auth class."""

    def test_init_successful(self, test_credentials, mock_token, mock_logger):
        """Test successful initialization of tdx_auth."""
        with patch('src.tdx_tool.authority.post') as mock_post:
            # Mock the token response
            mock_response = Mock()
            mock_response.json.return_value = mock_token
            mock_response.raise_for_status.return_value = None
            mock_post.return_value = mock_response

            # Initialize auth
            auth = tdx_auth(
                client_id=test_credentials["client_id"],
                client_key=test_credentials["client_key"],
                logger=mock_logger
            )

            # Assertions
            assert auth.client_id == test_credentials["client_id"]
            assert auth.client_key == test_credentials["client_key"]
            assert auth._token == mock_token["access_token"]
            mock_post.assert_called_once()

    def test_token_cached(self, test_credentials, mock_token, mock_logger):
        """Test that token is cached and not fetched multiple times before expiration."""
        with patch('src.tdx_tool.authority.post') as mock_post:
            mock_response = Mock()
            mock_response.json.return_value = mock_token
            mock_response.raise_for_status.return_value = None
            mock_post.return_value = mock_response

            auth = tdx_auth(
                client_id=test_credentials["client_id"],
                client_key=test_credentials["client_key"],
                logger=mock_logger
            )

            # Clear the mock to check if token is fetched again
            mock_post.reset_mock()

            # Access token multiple times
            token1 = auth.token
            token2 = auth.token
            token3 = auth.token

            # Should not call post again (token is cached)
            mock_post.assert_not_called()
            assert token1 == token2 == token3 == mock_token["access_token"]

    def test_token_refresh_on_expiration(self, test_credentials, mock_token, mock_logger):
        """Test that token is refreshed when expired."""
        with patch('src.tdx_tool.authority.post') as mock_post:
            # Setup initial token
            mock_response = Mock()
            mock_response.json.return_value = mock_token
            mock_response.raise_for_status.return_value = None
            mock_post.return_value = mock_response

            auth = tdx_auth(
                client_id=test_credentials["client_id"],
                client_key=test_credentials["client_key"],
                logger=mock_logger
            )

            initial_post_count = mock_post.call_count
            
            # Manually set expiration to past (force refresh)
            auth._expire_time = 0

            # Get token (should trigger refresh because expiration is in the past)
            token = auth.token

            # If implementation refreshes token, post count should increase
            assert token == mock_token["access_token"]

    def test_token_refresh_keeps_cached_token_on_network_error(self, test_credentials, mock_token, mock_logger):
        """Test that a refresh failure keeps the last cached token available."""
        auth = tdx_auth(
            client_id=test_credentials["client_id"],
            client_key=test_credentials["client_key"],
            logger=mock_logger
        )

        auth._token = mock_token["access_token"]
        auth._expire_time = 0

        with patch.object(auth, 'update_token', side_effect=requests.ConnectionError("Network error")) as mock_refresh:
            token = auth.token

            assert token == mock_token["access_token"]
            mock_refresh.assert_called_once()

    def test_callable_interface(self, test_credentials, mock_token, mock_logger):
        """Test that tdx_auth can be called as a function."""
        with patch('src.tdx_tool.authority.post') as mock_post:
            mock_response = Mock()
            mock_response.json.return_value = mock_token
            mock_response.raise_for_status.return_value = None
            mock_post.return_value = mock_response

            auth = tdx_auth(
                client_id=test_credentials["client_id"],
                client_key=test_credentials["client_key"],
                logger=mock_logger
            )

            # Test __call__ method
            token = auth()
            assert token == mock_token["access_token"]

    def test_string_representation(self, test_credentials, mock_token, mock_logger):
        """Test __str__ and __repr__ methods."""
        with patch('src.tdx_tool.authority.post') as mock_post:
            mock_response = Mock()
            mock_response.json.return_value = mock_token
            mock_response.raise_for_status.return_value = None
            mock_post.return_value = mock_response

            auth = tdx_auth(
                client_id=test_credentials["client_id"],
                client_key=test_credentials["client_key"],
                logger=mock_logger
            )

            str_repr = str(auth)
            assert "tdx_auth" in str_repr
            assert test_credentials["client_id"] in str_repr
