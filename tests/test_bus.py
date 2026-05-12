"""Tests for the tdx_bus module."""
import pytest
from unittest.mock import Mock, patch, MagicMock
import pandas as pd
import geopandas as gpd

from src.tdx_tool.bus import tdx_bus
from src.tdx_tool.utils import BusRegion
from src.tdx_tool.bus_models import Route, Operator, I18n


class TestTdxBus:
    """Test suite for tdx_bus class."""

    @pytest.fixture
    def bus_instance(self, test_credentials, mock_token, mock_logger):
        """Create a tdx_bus instance with mocked auth."""
        with patch('src.tdx_tool.bus.tdx_tool.__init__', return_value=None):
            bus = tdx_bus(
                client_id=test_credentials["client_id"],
                client_key=test_credentials["client_key"],
                region=BusRegion.Taipei,
                logger=mock_logger
            )
            # Manually set attributes that would be set by parent __init__
            bus.logger = mock_logger
            bus.auth = Mock()
            bus.auth.token = mock_token["access_token"]
            bus._tdx_tool__export_result = False
            bus._tdx_tool__default_coor = "EPSG:4326"
            bus._tdx_tool__output_path = "output"
            bus._together = False
            return bus
    @pytest.fixture
    def bus_instance(self, test_credentials, mock_token, mock_logger):
        """Create a tdx_bus instance with mocked auth."""
        with patch('src.tdx_tool.core.tdx_auth'):
            # Patch __init__ to call parent __init__ and then set logger
            original_init = tdx_bus.__init__
            def mocked_init(self, client_id, client_key, region=None, logger=None):
                # Call parent init
                self.logger = logger or mock_logger
                self.auth = Mock()
                self.auth.token = mock_token["access_token"]
                self._tdx_tool__export_result = False
                self._tdx_tool__default_coor = "EPSG:4326"
                self._tdx_tool__output_path = "output"
                # Now complete tdx_bus init
                self.region = region if region else BusRegion.Intercity
                self._together = None
                if self.region.ambiguous_name is not None:
                    self._together = False
            
            with patch.object(tdx_bus, '__init__', mocked_init):
                bus = tdx_bus(
                    client_id=test_credentials["client_id"],
                    client_key=test_credentials["client_key"],
                    region=BusRegion.Taipei,
                    logger=mock_logger
                )
                return bus

    def test_initialization_with_region(self, bus_instance):
        """Test tdx_bus initialization with specific region."""
        assert bus_instance.region == BusRegion.Taipei

    def test_intercity_is_default_region(self):
        """Test that Intercity is the default region."""
        # Create instance with None region
        with patch('src.tdx_tool.core.tdx_auth'):
            bus = tdx_bus(
                client_id="test_id",
                client_key="test_key",
                region=None  # Should default to Intercity
            )
            assert bus.region == BusRegion.Intercity

    def test_ambiguous_region_has_alternate(self):
        """Test that ambiguous regions have an alternate name."""
        assert BusRegion.Hsinchu.ambiguous_name is not None
        assert BusRegion.Chiayi.ambiguous_name is not None

    def test_from_region_str_valid_region(self, test_credentials, mock_logger):
        """Test from_region_str class method with valid region name."""
        with patch('src.tdx_tool.bus.tdx_tool.__init__', return_value=None):
            bus = tdx_bus.from_region_str(
                client_id=test_credentials["client_id"],
                client_key=test_credentials["client_key"],
                region="Taipei",
                logger=mock_logger
            )
            assert bus.region == BusRegion.Taipei

    def test_from_region_str_case_insensitive(self):
        """Test from_region_str handles case variations."""
        with patch('src.tdx_tool.core.tdx_auth'):
            # Test with lowercase
            bus = tdx_bus.from_region_str(
                client_id="test_id",
                client_key="test_key",
                region="taipei"
            )
            assert bus.region == BusRegion.Taipei

    def test_from_region_str_invalid_region(self, test_credentials, mock_logger):
        """Test from_region_str with invalid region name."""
        with patch('src.tdx_tool.bus.tdx_tool.__init__', return_value=None):
            with pytest.raises(ValueError, match="Invalid region name"):
                tdx_bus.from_region_str(
                    client_id=test_credentials["client_id"],
                    client_key=test_credentials["client_key"],
                    region="InvalidCity",
                    logger=mock_logger
                )

    def test_together_property_getter(self, bus_instance):
        """Test together property getter."""
        bus_instance._together = True
        assert bus_instance.together is True

    def test_together_property_setter(self, bus_instance):
        """Test together property setter."""
        bus_instance.together = False
        assert bus_instance._together is False

    def test_url_middle_part_single_region(self, bus_instance):
        """Test _url_middle_part returns correct URL components for single region."""
        url_parts = bus_instance._url_middle_part()
        assert isinstance(url_parts, list)
        assert len(url_parts) >= 1
        assert "Taipei" in url_parts[0]

    def test_url_middle_part_ambiguous_region_together_false(self, test_credentials, mock_logger):
        """Test _url_middle_part for ambiguous region with together=False."""
        with patch('src.tdx_tool.bus.tdx_tool.__init__', return_value=None):
            bus = tdx_bus(
                client_id=test_credentials["client_id"],
                client_key=test_credentials["client_key"],
                region=BusRegion.Hsinchu,
                logger=mock_logger
            )
            bus._together = False
            url_parts = bus._url_middle_part()
            assert isinstance(url_parts, list)


class TestBusRegion:
    """Test suite for BusRegion enum."""

    def test_bus_region_taipei(self):
        """Test Taipei region enum."""
        assert BusRegion.Taipei.value == "Taipei"

    def test_bus_region_intercity(self):
        """Test Intercity region enum."""
        assert BusRegion.Intercity.value == "Intercity"

    def test_is_county_for_county_regions(self):
        """Test isCounty property for county regions."""
        assert BusRegion.Hsinchu.isCounty is True
        assert BusRegion.Changhua.isCounty is True

    def test_is_county_for_non_county_regions(self):
        """Test isCounty property for non-county regions."""
        assert BusRegion.Taipei.isCounty is False
        assert BusRegion.Intercity.isCounty is False

    def test_ambiguous_name_for_hsinchu(self):
        """Test ambiguous_name property for Hsinchu region."""
        hsinchu = BusRegion.Hsinchu
        assert hsinchu.ambiguous_name is not None
        assert "HsinchuCity" in hsinchu.ambiguous_name or "Hsinchu" in hsinchu.ambiguous_name

    def test_non_ambiguous_region_returns_none(self):
        """Test that non-ambiguous regions return None for ambiguous_name."""
        # Keelung and Intercity have no ambiguous names
        assert BusRegion.Keelung.ambiguous_name is None
        assert BusRegion.Intercity.ambiguous_name is None
        assert BusRegion.Taichung.ambiguous_name is None
