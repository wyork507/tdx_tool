"""Tests for the tdx_bike module."""

from unittest.mock import Mock, patch

import logging

from src.tdx_tool.bike import tdx_bike, tdx_bike_taipei_city
from src.tdx_tool.utils import BikeRegion


def _mock_tdx_tool_init(self, client_id, client_key, logger=None):
    self.logger = logger or Mock(spec=logging.Logger)
    self.auth = Mock()
    self.auth.token = "mock_token"
    self._tdx_tool__export_result = False
    self._tdx_tool__default_coor = "EPSG:4326"
    self._tdx_tool__output_path = "output"


class TestTdxBike:
    def test_taipei_region_uses_specialized_subclass(self, mock_logger):
        with patch("src.tdx_tool.bike.tdx_tool.__init__", new=_mock_tdx_tool_init):
            bike = tdx_bike(
                client_id="test_id",
                client_key="test_key",
                regions=[BikeRegion.Taipei],
                logger=mock_logger,
            )

        assert isinstance(bike, tdx_bike_taipei_city)
        assert bike.regions == [BikeRegion.Taipei]

    def test_multiple_regions_stay_on_base_class(self, mock_logger):
        with patch("src.tdx_tool.bike.tdx_tool.__init__", new=_mock_tdx_tool_init):
            bike = tdx_bike(
                client_id="test_id",
                client_key="test_key",
                regions=[BikeRegion.Taipei, BikeRegion.Taoyuan],
                logger=mock_logger,
            )

        assert type(bike) is tdx_bike
        assert bike.regions == [BikeRegion.Taipei, BikeRegion.Taoyuan]
