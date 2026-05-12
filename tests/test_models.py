"""Tests for the bus_models module."""
import pytest
from datetime import datetime

from src.tdx_tool.bus_models import (
    Direction, BusRouteType, ServiceStatus, ErrorCause,
    I18n, Operator, SubRoute, Route
)


class TestEnums:
    """Test suite for enum classes."""

    def test_direction_enum_values(self):
        """Test Direction enum values."""
        assert Direction.Forward == 0
        assert Direction.Backward == 1
        assert Direction.Loop == 2
        assert Direction.Circular == 10
        assert Direction.Unknown == 255

    def test_bus_route_type_enum_values(self):
        """Test BusRouteType enum values."""
        assert BusRouteType.LocalCity == 1
        assert BusRouteType.InterCity == 12
        assert BusRouteType.Highway == 13
        assert BusRouteType.Shuttle == 14

    def test_service_status_enum_values(self):
        """Test ServiceStatus enum values."""
        assert ServiceStatus.Cancel == 0
        assert ServiceStatus.Normal == 1
        assert ServiceStatus.Errors == 2

    def test_error_cause_enum_values(self):
        """Test ErrorCause enum values."""
        assert ErrorCause.Accident == 1
        assert ErrorCause.Weather == 6
        assert ErrorCause.Strike == 10


class TestI18n:
    """Test suite for I18n multilingual struct."""

    def test_i18n_creation_with_both_languages(self):
        """Test creating I18n with both Chinese and English."""
        name = I18n(Zh_tw="台北101", En="Taipei101")
        assert name.Zh_tw == "台北101"
        assert name.En == "Taipei101"

    def test_i18n_creation_with_chinese_only(self):
        """Test creating I18n with only Chinese."""
        name = I18n(Zh_tw="台北公運")
        assert name.Zh_tw == "台北公運"
        assert name.En is None

    def test_i18n_default_english_none(self):
        """Test that English field defaults to None."""
        name = I18n(Zh_tw="南港")
        assert name.En is None


class TestOperator:
    """Test suite for Operator struct."""

    def test_operator_creation(self):
        """Test creating an Operator instance."""
        operator = Operator(
            OperatorID="TMBUS",
            OperatorName=I18n(Zh_tw="台北公運", En="Taipei Bus")
        )
        assert operator.OperatorID == "TMBUS"
        assert operator.OperatorName.Zh_tw == "台北公運"
        assert operator.OperatorName.En == "Taipei Bus"

    def test_operator_with_chinese_only_name(self):
        """Test Operator with Chinese-only name."""
        operator = Operator(
            OperatorID="OPR001",
            OperatorName=I18n(Zh_tw="公路客運")
        )
        assert operator.OperatorID == "OPR001"
        assert operator.OperatorName.En is None


class TestSubRoute:
    """Test suite for SubRoute struct."""

    def test_subroute_creation_minimal(self):
        """Test creating SubRoute with minimal required fields."""
        subroute = SubRoute(
            SubRouteUID="Taipei/1/1",
            SubRouteID="1",
            Direction=0,
            SubRouteName=I18n(Zh_tw="往南港", En="To Nangang")
        )
        assert subroute.SubRouteUID == "Taipei/1/1"
        assert subroute.Direction == Direction.Forward
        assert subroute.OperatorIDs == []

    def test_subroute_creation_full(self):
        """Test creating SubRoute with all fields."""
        subroute = SubRoute(
            SubRouteUID="Taipei/1/1",
            SubRouteID="1",
            Direction=0,
            SubRouteName=I18n(Zh_tw="往南港", En="To Nangang"),
            OperatorIDs=["TMBUS"],
            Headsign="南港",
            HeadsignEn="Nangang",
            DepartureStopNameZh="台北101",
            DepartureStopNameEn="Taipei101",
            DestinationStopNameZh="南港",
            DestinationStopNameEn="Nangang"
        )
        assert subroute.SubRouteUID == "Taipei/1/1"
        assert subroute.OperatorIDs == ["TMBUS"]
        assert subroute.Headsign == "南港"
        assert subroute.DepartureStopNameZh == "台北101"


class TestRoute:
    """Test suite for Route struct."""

    def test_route_creation_minimal(self):
        """Test creating Route with minimal required fields."""
        operator = Operator(
            OperatorID="TMBUS",
            OperatorName=I18n(Zh_tw="台北公運", En="Taipei Bus")
        )
        route = Route(
            RouteUID="Taipei/1",
            BusRouteType=1,
            RouteName=I18n(Zh_tw="台北101-南港", En="Taipei101-Nangang"),
            Operators=[operator]
        )
        assert route.RouteUID == "Taipei/1"
        assert route.BusRouteType == BusRouteType.LocalCity
        assert len(route.Operators) == 1
        assert route.SubRoutes == []

    def test_route_creation_with_subroutes(self):
        """Test creating Route with SubRoutes."""
        operator = Operator(
            OperatorID="TMBUS",
            OperatorName=I18n(Zh_tw="台北公運")
        )
        subroute = SubRoute(
            SubRouteUID="Taipei/1/1",
            SubRouteID="1",
            Direction=0,
            SubRouteName=I18n(Zh_tw="往南港")
        )
        route = Route(
            RouteUID="Taipei/1",
            BusRouteType=1,
            RouteName=I18n(Zh_tw="台北101-南港"),
            Operators=[operator],
            SubRoutes=[subroute]
        )
        assert len(route.SubRoutes) == 1
        assert route.SubRoutes[0].SubRouteUID == "Taipei/1/1"

    def test_route_with_multiple_operators(self):
        """Test Route with multiple operators."""
        operators = [
            Operator(OperatorID="TMBUS", OperatorName=I18n(Zh_tw="台北公運")),
            Operator(OperatorID="OPR002", OperatorName=I18n(Zh_tw="其他業者"))
        ]
        route = Route(
            RouteUID="Taipei/100",
            BusRouteType=1,
            RouteName=I18n(Zh_tw="台北路線"),
            Operators=operators
        )
        assert len(route.Operators) == 2
