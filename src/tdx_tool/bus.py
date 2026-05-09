# Dependency imports
from datetime import datetime
from functools import cached_property, cache
from logging import Logger
from typing import Literal, Optional
from requests import Response
import logging, msgspec
import pandas as pd
import geopandas as gpd
import shapely
import requests

# Local imports
from .parsers import _bus_parsers as parsers
from .core import tdx_tool
from .utils import BusRegion, I18n
from .bus_models import *

class tdx_bus(tdx_tool):
    """

    """
    def __init__(self, client_id: str, client_key: str, region: BusRegion | None = None, logger: Logger | None = None):
        super().__init__(client_id=client_id, client_key=client_key, logger=logger)
        self.region = region if region else BusRegion.Intercity
        self.logger.debug(f"tdx_bus initialized for region: {self.region.value}")
        self._together = None
        if self.region.ambiguous_name is not None:
            self._together = False
            self.logger.warning(
                "Ambiguous region name detected: %s and %s. Set `together = True` to fetch both.",
                self.region.value,
                self.region.ambiguous_name,
            )

    @classmethod
    def from_region_str(cls, client_id: str, client_key: str, region: str, logger: Logger | None = None):
        normalized = region.replace("-", "_").replace(" ", "_")
        regions = [r.name for r in BusRegion]

        if region.capitalize() in regions:
            return cls(client_id=client_id, client_key=client_key, logger=logger, region=BusRegion[region.capitalize()])
        elif f"{region.capitalize()}County" in regions:
            return cls(client_id=client_id, client_key=client_key, logger=logger, region=BusRegion[f"{region.capitalize()}County"])
        else:
            raise ValueError(f"Invalid region name: {region}. Valid options are: {[r.name for r in BusRegion]}")

    @property
    def together(self) -> bool | None:
        return self._together
    
    @together.setter
    def together(self, is_on: bool = True):
        self._together = True if self.region.ambiguous_name is not None and is_on else None

    def _url_middle_part(self) -> list[str]:
        if self.region == BusRegion.Intercity:
            return ["InterCity"]
        else:
            results = [f"City/{self.region.value}"]
            if self._together:
                results.append(f"City/{self.region.ambiguous_name}")
            return results

    @cached_property
    def _route_stops(self) -> list[RouteStops]:
        def decode(response: Response) -> list[RouteStops]: # type: ignore
            return msgspec.json.decode(response.content, type=list[RouteStops])
        
        return self._fetch_combined_data(
            prefix="v2/Bus/StopOfRoute",
            params={
                "$select": "RouteUID,SubRouteUID,RouteName,SubRouteName,Stops,OperatorIDs,Direction,City,CityCode,UpdateTime"
            },
            decoder=decode
        )
    
    @cached_property
    def routes(self) -> pd.DataFrame:
        """
        Fetch bus routes for the specified region.
        If the region has an ambiguous name, it will fetch routes for both regions if `together` is set to True.
        """
        def decoder(response: requests.Response) -> list[Route]: # type: ignore
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
        return gpd.GeoDataFrame(data, geometry="geometry", crs=self._default_coor)

    @cached_property
    def stations(self) -> gpd.GeoDataFrame:
        """
        Fetch bus stations for the specified region.
        If the region has an ambiguous name, it will fetch stations for both regions if `together` is set to True.
        """
        data = parsers.parse_stations(self._route_stops)
        data = data.sort_values(by=["StationID", "SubRouteNameEn", "Sequence"]).reset_index(drop=True)
        coor = data[["PositionLon", "PositionLat"]]
        self.logger.debug(f"Creating GeoDataFrame with {len(data)} stations.")
        return gpd.GeoDataFrame(
                data.drop(columns=["PositionLon", "PositionLat"]),
                geometry=gpd.points_from_xy(coor["PositionLon"], coor["PositionLat"]),
                crs=self._default_coor
            )
    
    @cached_property
    def operators(self) -> pd.DataFrame:
        """
        Fetch bus operators for the specified region.
        """
        def decoder(response: requests.Response) -> list[Operator]: # type: ignore
            return msgspec.json.decode(response.content, type=list[Operator])
        
        return self._fetch_combined_data(
            prefix="v2/Bus/Operator",
            params={
                "$select": "OperatorID,OperatorName"
            },
            decoder=decoder,
            parser=parsers.parse_operators
        )
    
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
                "$select": "AlertID,Title,Description,Department,Status,Cause,Effect,Scope,AlertURL,PublishTime,StartTime,EndTime,SrcUpdateTime,UpdateTime"
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
        
    def refresh_cache(self, property_name: Literal["routes", "stations", "shape", "operators", "all"] = "all") -> None:
        """
        Manually refresh the cached data for a specific property.
        This is useful if you want to ensure you have the most up-to-date information without waiting for the cache to expire.
        """
        refreshable_properties = ["routes", "stations", "shape", "operators"]
        refresh_targets = []
        match property_name:
            case "all":
                refresh_targets = refreshable_properties
            case _ if property_name in refreshable_properties:
                refresh_targets = [property_name]
            case _:
                self.logger.warning(f"Invalid property name for cache refresh: {property_name}. Valid options are:\n\t {', '.join(refreshable_properties)}")
        
        for target in refresh_targets:
            self.__dict__.pop(f"{target}", None)  # Remove the cached property if it exists
            self.logger.info(f"Cache for `{target}` has been refreshed.")

    # TODO
    def fetch_schedule_for_route(
        self,
        route_name: str,
        only_departures: bool = False,
        ) -> pd.DataFrame:
        """
        Fetch the schedule for a specific route.
        This includes departure times from the starting point, arrival times at the destination, and frequency of service throughout the day.
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