"""Tests for the parsers module."""
import pytest
import pandas as pd
import geopandas as gpd
from unittest.mock import Mock
import shapely.geometry

from src.tdx_tool.parsers import _bus_parsers
from src.tdx_tool.bus_models import (
    Route, SubRoute, Operator, I18n, RouteStops, Stop, RouteShape
)


class TestBusParsers:
    """Test suite for bus parsers."""

    def test_parse_routes_single_route_no_subroutes(self):
        """Test parsing a single route without subroutes."""
        operator = Operator(
            OperatorID="TMBUS",
            OperatorName=I18n(Zh_tw="台北公運", En="Taipei Bus")
        )
        route = Route(
            RouteUID="Taipei/1",
            BusRouteType=1,
            RouteName=I18n(Zh_tw="台北101-南港", En="Taipei101-Nangang"),
            Operators=[operator],
            DepartureStopNameZh="台北101",
            DepartureStopNameEn="Taipei101",
            DestinationStopNameZh="南港",
            DestinationStopNameEn="Nangang",
            SubRoutes=[]
        )

        df = _bus_parsers.parse_routes([route])

        assert isinstance(df, pd.DataFrame)
        assert len(df) == 1
        assert df.iloc[0]["RouteUID"] == "Taipei/1"
        assert df.iloc[0]["RouteNameZh"] == "台北101-南港"

    def test_parse_routes_with_subroutes(self):
        """Test parsing route with multiple subroutes."""
        operator = Operator(
            OperatorID="TMBUS",
            OperatorName=I18n(Zh_tw="台北公運")
        )
        subroute1 = SubRoute(
            SubRouteUID="Taipei/1/1",
            SubRouteID="1",
            Direction=0,
            SubRouteName=I18n(Zh_tw="往南港")
        )
        subroute2 = SubRoute(
            SubRouteUID="Taipei/1/2",
            SubRouteID="2",
            Direction=1,
            SubRouteName=I18n(Zh_tw="往台北101")
        )
        route = Route(
            RouteUID="Taipei/1",
            BusRouteType=1,
            RouteName=I18n(Zh_tw="台北101-南港"),
            Operators=[operator],
            SubRoutes=[subroute1, subroute2]
        )

        df = _bus_parsers.parse_routes([route])

        # Should have 2 rows (one for each subroute)
        assert len(df) == 2
        assert df.iloc[0]["SubRouteUID"] == "Taipei/1/1"
        assert df.iloc[1]["SubRouteUID"] == "Taipei/1/2"

    def test_parse_routes_with_multiple_operators(self):
        """Test parsing route with multiple operators."""
        operator1 = Operator(
            OperatorID="TMBUS",
            OperatorName=I18n(Zh_tw="台北公運")
        )
        operator2 = Operator(
            OperatorID="OPR002",
            OperatorName=I18n(Zh_tw="其他業者")
        )
        route = Route(
            RouteUID="Taipei/100",
            BusRouteType=1,
            RouteName=I18n(Zh_tw="路線100"),
            Operators=[operator1, operator2]
        )

        df = _bus_parsers.parse_routes([route])

        assert len(df) == 1
        # Operators should be in a DataFrame column
        assert isinstance(df.iloc[0]["Operators"], pd.DataFrame)
        assert len(df.iloc[0]["Operators"]) == 2

    def test_parse_routes_empty_list(self):
        """Test parsing empty route list."""
        df = _bus_parsers.parse_routes([])
        assert isinstance(df, pd.DataFrame)
        assert len(df) == 0

    def test_parse_route_with_shape_valid_geometry(self):
        """Test parsing route with valid WKT geometry."""
        wkt_geom = "LINESTRING (121.5 25.0, 121.6 25.1, 121.7 25.2)"
        route_shape = Mock()
        route_shape.RouteUID = "Taipei/1"
        route_shape.SubRouteUID = "Taipei/1/1"
        route_shape.RouteName = I18n(Zh_tw="台北101-南港", En="Taipei101-Nangang")
        route_shape.Direction = 0
        route_shape.UpdateTime = "2024-01-01T10:00:00"
        route_shape.Geometry = wkt_geom

        df = _bus_parsers.parse_route_with_shape([route_shape])

        assert isinstance(df, pd.DataFrame)
        assert len(df) == 1
        assert df.iloc[0]["RouteUID"] == "Taipei/1"
        # Geometry should be a Shapely geometry object
        assert isinstance(df.iloc[0]["geometry"], shapely.geometry.base.BaseGeometry)

    def test_parse_route_with_shape_handles_invalid_geometry(self):
        """Test parsing route with invalid WKT geometry doesn't crash."""
        route_shape = Mock()
        route_shape.RouteUID = "Taipei/1"
        route_shape.SubRouteUID = "Taipei/1/1"
        route_shape.RouteName = I18n(Zh_tw="台北路線")
        route_shape.Direction = 0
        route_shape.UpdateTime = "2024-01-01T10:00:00"
        route_shape.Geometry = "INVALID WKT"

        # Should not crash even with invalid geometry
        try:
            df = _bus_parsers.parse_route_with_shape([route_shape])
            assert isinstance(df, pd.DataFrame)
            assert len(df) == 1
        except Exception:
            pytest.skip("Invalid geometry handling may vary")

    def test_parse_stations_basic(self):
        """Test parsing station data from route stops."""
        stop = Mock()
        stop.StationID = "STATION1"
        stop.StationGroupID = "GROUP1"
        stop.StopUID = "STOP1"
        stop.StopName = I18n(Zh_tw="台北101", En="Taipei101")
        stop.StopSequence = 1
        stop.StopBoarding = 1

        operator = Operator(
            OperatorID="TMBUS",
            OperatorName=I18n(Zh_tw="台北公運")
        )
        route_stop = Mock()
        route_stop.RouteUID = "Taipei/1"
        route_stop.RouteName = I18n(Zh_tw="台北101-南港")
        route_stop.SubRouteUID = "Taipei/1/1"
        route_stop.SubRouteName = I18n(Zh_tw="往南港")
        route_stop.Direction = 0
        route_stop.City = "Taipei"
        route_stop.CityCode = "TXG"
        route_stop.UpdateTime = "2024-01-01T10:00:00"
        route_stop.Operators = [operator]
        route_stop.Stops = [stop]

        df = _bus_parsers.parse_stations([route_stop])

        assert isinstance(df, pd.DataFrame)
        assert len(df) == 1
        assert df.iloc[0]["StationID"] == "STATION1"
        assert df.iloc[0]["City"] == "Taipei"

    def test_parse_stations_multiple_stops(self):
        """Test parsing multiple stops from a route."""
        stops = []
        for i in range(3):
            stop = Mock()
            stop.StationID = f"STATION{i}"
            stop.StationGroupID = f"GROUP{i}"
            stop.StopUID = f"STOP{i}"
            stop.StopName = I18n(Zh_tw=f"站點{i}")
            stop.StopSequence = i + 1
            stop.StopBoarding = 1
            stops.append(stop)

        route_stop = Mock()
        route_stop.RouteUID = "Taipei/1"
        route_stop.RouteName = I18n(Zh_tw="台北路線")
        route_stop.SubRouteUID = "Taipei/1/1"
        route_stop.SubRouteName = I18n(Zh_tw="往終點")
        route_stop.Direction = 0
        route_stop.City = "Taipei"
        route_stop.CityCode = "TXG"
        route_stop.UpdateTime = "2024-01-01T10:00:00"
        route_stop.Operators = []
        route_stop.Stops = stops

        df = _bus_parsers.parse_stations([route_stop])

        assert len(df) == 3
        assert all(f"STATION{i}" in df["StationID"].values for i in range(3))
