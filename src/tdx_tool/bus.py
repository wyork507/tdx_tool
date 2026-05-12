# Dependency imports
from datetime import datetime
from enum import Enum
from functools import cached_property, cache
from logging import Logger
from typing import Literal, Optional
import logging, msgspec
import pandas as pd
import geopandas as gpd
import shapely
import requests

# Local imports
from .parsers import _bus_parsers as parsers
from .core import tdx_tool
from .utils import BusRegion
from .bus_models import RouteStops, Route, RouteShape, Operator, Alert, Schedule

class tdx_bus(tdx_tool):
    """
    A tool for getting bus-related data from the TDx API.
    
    When initializing, you can specify the region you want to fetch data for using the `region` parameter.
    >>> bus_tool = tdx_bus(client_id="your_client_id", client_key="your_client_key", region=BusRegion.Taipei)
    Or you can use the `from_region_str` class method to initialize with a region name string:
    >>> bus_tool = tdx_bus.from_region_str(client_id="your_client_id", client_key="your_client_key", region="Taipei")

    Note that some regions have ambiguous names (e.g., "Hsinchu" and "HsinchuCounty"). If you want to fetch data for
    both regions, set the `together` property to True:
    >>> bus_tool.together = True
    
    ---
    Attributes:

    """
    def __init__(self, client_id: str, client_key: str, region: BusRegion | None = None, logger: Logger | None = None):
        super().__init__(client_id=client_id, client_key=client_key, logger=logger)
        self.region = region if region else BusRegion.Intercity
        self.logger.debug(f"tdx_bus initialized for region: {self.region.value.en}")
        self._together = None
        if self.region.ambiguous_case is not None:
            self._together = False
            self.logger.warning(
                "Ambiguous region name detected: %s and %s. Set `together = True` to fetch both.",
                self.region.value.en,
                self.region.ambiguous_case.value.en,
            )

    @classmethod
    def from_region_str(cls, client_id: str, client_key: str, region: str, logger: Logger | None = None):
        """
        Alternative constructor to initialize tdx_bus using a region name string instead of a BusRegion enum.
        Note that the region string is case-insensitive and can be either the city name or the county name (e.g., "Hsinchu" or "HsinchuCounty").
        """
        regions = set([r.name for r in BusRegion] + [r.value for r in BusRegion])
        target = region.replace("-", "").replace(" ", "")
        
        if target in regions:
            return cls(client_id=client_id, client_key=client_key, logger=logger, region=BusRegion[target])
        elif f"{target}County" in regions:
            return cls(client_id=client_id, client_key=client_key, logger=logger, region=BusRegion[f"{target}County"])
        else:
            raise ValueError(f"Invalid region name: {region}. Valid options are: {[r.name for r in BusRegion]}")

    @property
    def together(self) -> bool | None:
        return self._together
    
    @together.setter
    def together(self, is_on: bool = True):
        self._together = True if self.region.ambiguous_case is not None and is_on else None

    def _url_middle_part(self) -> list[str]:
        if self.region == BusRegion.Intercity:
            return ["InterCity"]
        else:
            results = [f"City/{self.region.value.api_tag}"]
            if self._together:
                results.append(f"City/{self.region.ambiguous_case.value.api_tag}") # type: ignore
            return results

    @cached_property
    def _route_stops(self) -> list[RouteStops]:
        def decode(response: requests.Response) -> list[RouteStops]:
            return msgspec.json.decode(response.content, type=list[RouteStops])
        
        return self._fetch_combined_data(
            prefix="v2/Bus/StopOfRoute",
            params={
                "$select": "RouteUID,SubRouteUID,RouteName,SubRouteName,Stops,Operators,Direction,City,CityCode,UpdateTime"
            },
            decoder=decode
        )
    
    @cached_property
    def routes(self) -> pd.DataFrame:
        """
        Fetch bus routes for the specified region, then cache it.
        You can refresh the cache by `refresh_cache("routes")`.
        """
        def decoder(response: requests.Response) -> list[Route]:
            return msgspec.json.decode(response.content, type=list[Route])
        # Main logic
        return self._fetch_combined_data(
            prefix="v2/Bus/Route",
            params={
                "$select": "RouteUID,Operators,BusRouteType,RouteName,DepartureStopNameZh,DepartureStopNameEn,DestinationStopNameZh,DestinationStopNameEn,UpdateTime,VersionID,SubRoutes"
            },
            decoder=decoder,
            parser=parsers.parse_routes
        ).sort_values(by=["RouteNameEn", "SubRouteUID"]).reset_index(drop=True)
    
    @cached_property
    def routes_with_shape(self) -> gpd.GeoDataFrame:
        """
        Fetch bus routes with shape information for the specified region, then cache it.
        You can refresh the cache by `refresh_cache("routes_with_shape")`.
        """
        def decoder(response: requests.Response) -> list[RouteShape]: # type: ignore
            return msgspec.json.decode(response.content, type=list[RouteShape])
        # Main logic
        data = self._fetch_combined_data(
            prefix="v2/Bus/Shape",
            params={
                "$select": "RouteUID,SubRouteUID,RouteName,Direction,Geometry,EncodedPolyline,UpdateTime"
            },
            decoder=decoder,
            parser=parsers.parse_route_with_shape
        ).sort_values(by=["RouteNameEn", "SubRouteUID"]).reset_index(drop=True)
        data = data.join(
            self.routes.set_index(["RouteUID", "SubRouteUID"]),
            on=["RouteUID", "SubRouteUID"],
            how="left",
            rsuffix="_route"
            )
        return gpd.GeoDataFrame(data, geometry="geometry", crs=self.default_coor)

    @cached_property
    def stations(self) -> gpd.GeoDataFrame:
        """
        Fetch bus stations for the specified region.
        You can refresh the cache by `refresh_cache("stations")`.
        """
        data = parsers.parse_stations(self._route_stops)
        data = data.sort_values(by=["StationID", "SubRouteNameEn", "Sequence"]).reset_index(drop=True)
        coor = data[["PositionLon", "PositionLat"]]
        self.logger.debug(f"Creating GeoDataFrame with {len(data)} stations.")
        return gpd.GeoDataFrame(
                data.drop(columns=["PositionLon", "PositionLat"]),
                geometry=gpd.points_from_xy(coor["PositionLon"], coor["PositionLat"]),
                crs=self.default_coor
            )
    
    @cached_property
    def operators(self) -> pd.DataFrame:
        """
        Fetch bus operators for the specified region.
        You can refresh the cache by `refresh_cache("operators")`.
        """
        def decoder(response: requests.Response) -> list[Operator]:
            return msgspec.json.decode(response.content, type=list[Operator])
        
        return self._fetch_combined_data(
            prefix="v2/Bus/Operator",
            params={
                "$select": "OperatorID,OperatorName"
            },
            decoder=decoder,
            parser=parsers.parse_operators
        )
    
    @cached_property
    def route_departure_info(self) -> pd.DataFrame:
        """
        Fetch bus departure information for the specified region.
        You can refresh the cache by `refresh_cache("route_departure_info")`.
        """
        def decoder(response: requests.Response) -> list[Schedule]:
            return msgspec.json.decode(response.content, type=list[Schedule])
        
        data = self._fetch_combined_data(
            prefix="v2/Bus/",
            params={
                "$select": "TripID,RouteUID,SubRouteUID,Direction,TripDepTime"
            },
            decoder=decoder
        )
        return pd.DataFrame(data)
    
    #@cached_property
    #def stations_timetable(self) -> pd.DataFrame:
        """
        Fetch bus stations timetable for the specified region.
        You can refresh the cache by `refresh_cache("stations_timetable")`.
        """
        """
        def decoder(response: requests.Response) -> list[RouteStops]: # type: ignore
            return msgspec.json.decode(response.content, type=list[RouteStops])

        data = parsers.parse_stations_timetable(self._route_stops)
        return pd.DataFrame(data)
        """

    @property
    def alert(self) -> list[Alert]:
        """
        Same as operate_status, because TDx name it "Alert" but the content is more like "OperateStatus".
        We keep both names for better user experience.
        """
        def decoder(response: requests.Response) -> list[Alert]: # type: ignore
            return msgspec.json.decode(response.content, type=list[Alert])
        
        return self._fetch_combined_data(
            prefix="v2/Bus/Alert",
            params={
                "$select": "AlertID,Title,Description,Department,Status,Cause,Effect,Scope,PublishTime,StartTime,EndTime,SrcUpdateTime,UpdateTime"
            },
            decoder=decoder
        )

    @property
    def operate_status(self) -> list[Alert]:
        """
        Fetch current alerts and warnings for bus services in the specified region.
        This may include weather-related disruptions, traffic incidents affecting bus routes, and other urgent notifications.
        """
        return self.alert
        
    def refresh_cache(
        self,
        property_name: Literal["routes", "stations", "routes_with_shape", "operators", "route_departure_info", "all"] = "all"
        ) -> None:
        """
        Manually refresh the cached data for a specific property.
        This is useful if you want to ensure you have the most up-to-date information without waiting for the cache to expire.
        """
        refreshable_properties = ["routes", "stations", "routes_with_shape", "operators", "route_departure_info"]
        refresh_targets = []
        
        match property_name:
            case "all":
                refresh_targets = refreshable_properties
            case _ if property_name in refreshable_properties:
                refresh_targets = [property_name]
            case _:
                self.logger.warning(f"Invalid property name for cache refresh: {property_name}. Valid options are:\n\t {', '.join(refreshable_properties)}")
        
        if refresh_targets in ["stations", "routes_with_shape"]:
            self.__dict__.pop("_route_stops", None)  # Clear the cached route stops if stations or routes_with_shape is being refreshed

        for target in refresh_targets:
            self.__dict__.pop(f"{target}", None)  # Remove the cached property if it exists
            self.logger.info(f"Cache for `{target}` has been refreshed.")
    

    # TODO
    def get_schedule_for_route(
        self,
        route_name: str,
        only_departures: bool = False,
        ) -> pd.DataFrame:
        """
        
        """
        pass

    # TODO
    def fetch_estimated_arrival_for_routes(self, route_name: str) -> pd.DataFrame:
        """
        Fetch real-time bus information for a specific route.
        This includes estimated arrival times, current bus locations, and occupancy status.
        """
        pass

    # TODO
    def fetch_estimated_arrival_for_stations(self, station_uid: str) -> pd.DataFrame:
        """
        Fetch real-time bus information for a specific station.
        This includes estimated arrival times for all routes serving the station, current bus locations, and occupancy status.
        """
        pass