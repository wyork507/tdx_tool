# Dependency imports
from datetime import datetime
from functools import cached_property
from logging import Logger
from typing import Literal, TypeAlias, TypeVar
import msgspec, requests
import pandas as pd
import geopandas as gpd
# Local imports
from .bus_parsers import _bus_parsers
from .core import tdx_tool
from .utils import BusRegion
from .bus_models import RouteStops, Route, RouteShape, Station, Operator, Alert, Schedule, DailySchedule

RefreshableCacheProperty: TypeAlias = Literal[
    "routes",
    "stations",
    "routes_with_shape",
    "operators",
    "schedules",
    "daily_timetables",
]

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
    def __init__(self,
        client_id: str, client_key: str,
        region: BusRegion | None = None,
        together: bool = False,
        logger: Logger | None = None
    ):
        super().__init__(client_id=client_id, client_key=client_key, logger=logger)
        self.__region = region if region else BusRegion.Intercity
        self.logger.debug(f"tdx_bus initialized for region: {self.__region.value.en}")
        self._together = None
        if self.__region.ambiguous_case is not None:
            self._together = False if not together else True
            self.logger.warning(
                "Ambiguous region name detected: %s and %s. Set `together = True` to fetch both.",
                self.__region.value.en,
                self.__region.ambiguous_case.value.en,
            )
        self._parsers = _bus_parsers(self.logger)

    @classmethod
    def from_region_str(cls, client_id: str, client_key: str, region: str, logger: Logger | None = None) -> "tdx_bus":
        """
        Enter a name string, such as "Taipei" or "Hsinchu", to initialize the class with the corresponding region.
        ---
        Parameters:
        - `client_id`: Your TDx API client ID.
        - `client_key`: Your TDx API client key.
        - `region`: The name of the region you want to fetch data for.
        ---
        Returns:
            An instance of `tdx_bus` initialized for the specified region.
            Note that if the region name is ambiguous, default for together will be False.
        ---
        Raises:
            ValueError: If the input string does not match any known region.
        """
        from .utils import string_into_identity as convertor
        try:
            identity = convertor(region)
            return cls(
                client_id, client_key, BusRegion(identity), True, logger
            )
        except ValueError as e:
            raise e
        
    @classmethod
    def intercity(cls,
        client_id: str,
        client_key: str,
        logger: Logger | None = None
    ) -> "tdx_bus":
        """ 
        Returns:
            An instance of `tdx_bus` initialized for the Intercity region, which includes all intercity bus routes across Taiwan.
        """
        return cls(client_id=client_id, client_key=client_key, logger=logger)

    @property
    def together(self) -> bool | None:
        return self._together
    
    @together.setter
    def together(self, is_on: bool = True):
        self._together = True if self.__region.ambiguous_case is not None and is_on else None
    
    @property
    def region(self) -> BusRegion:
        return self.__region
    
    def _url_middle_part(self) -> list[str]:
        if self.__region == BusRegion.Intercity:
            return ["InterCity"]
        else:
            results = [f"City/{self.__region.api_tag}"]
            if self._together is True:
                others = self.__region.ambiguous_case
                if others is not None:
                    results.append(f"City/{others.api_tag}")
                else:
                    self.logger.warning(f"No ambiguous region found for {self.__region.value.en}, but `together` is set to True. Ignoring `together` setting.")
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
    def routes(self) -> list[Route]:
        def decoder(response: requests.Response) -> list[Route]:
            return msgspec.json.decode(response.content, type=list[Route])
        
        return self._fetch_combined_data(
            prefix="v2/Bus/Route",
            params={
                "$select": "RouteUID,Operators,BusRouteType,RouteName,DepartureStopNameZh,DepartureStopNameEn,DestinationStopNameZh,DestinationStopNameEn,UpdateTime,VersionID,SubRoutes"
            },
            decoder=decoder
        )
    
    @cached_property
    def routes_to_dataframe(self) -> pd.DataFrame:
        """
        Fetch bus routes for the specified region, then cache it.
        You can refresh the cache by `refresh_cache("routes")`.
        """
        return self._parsers.parse_routes(
            self.routes
        ).sort_values(by=["RouteNameEn", "SubRouteUID"]).reset_index(drop=True)
    
    @cached_property
    def routes_with_shape(self) -> list[RouteShape]:
        def decoder(response: requests.Response) -> list[RouteShape]:
            return msgspec.json.decode(response.content, type=list[RouteShape])
        # Main logic
        return self._fetch_combined_data(
            prefix="v2/Bus/Shape",
            params={
                "$select": "RouteUID,SubRouteUID,RouteName,Direction,Geometry,EncodedPolyline,UpdateTime"
            },
            decoder=decoder
        )

    @cached_property
    def routes_with_shape_to_dataframe(self) -> gpd.GeoDataFrame:
        """
        Fetch bus routes with shape information for the specified region, then cache it.
        You can refresh the cache by `refresh_cache("routes_with_shape")`.
        """
        data = self._parsers.parse_route_with_shape(
            self.routes_with_shape
        ).sort_values(by=["RouteNameEn", "SubRouteUID"]).reset_index(drop=True)
        data = data.join(
            self.routes_to_dataframe.set_index(["RouteUID", "SubRouteUID"]),
            on=["RouteUID", "SubRouteUID"],
            how="left",
            rsuffix="_route"
        )
        return gpd.GeoDataFrame(data, geometry="geometry", crs=self.default_coor)

    @cached_property
    def stations(self) -> list[Station]:
        """
        Fetch bus stations for the specified region.
        You can refresh the cache by `refresh_cache("stations")`.
        """
        from .bus_models import StationFraction
        def decoder(response: requests.Response) -> list[StationFraction]:
            return msgspec.json.decode(response.content, type=list[StationFraction])

        return list(self._parsers.parse_stations(
            self._route_stops,
            self._fetch_combined_data(
                prefix="v2/Bus/Station",
                params={
                    "$select": "StationUID,StationPosition,StationAddress,LocationCityCode,Bearing,UpdateTime"
                },
                decoder=decoder
            )
        ).values())
    
    @cached_property
    def stations_to_dataframe(self) -> pd.DataFrame:
        data = self._parsers.parse_stations_to_dataframe(self._route_stops)
        data = data.sort_values(by=["StationID", "SubRouteNameEn", "Sequence"]).reset_index(drop=True)
        coor = data[["PositionLon", "PositionLat"]]
        self.logger.debug(f"Creating GeoDataFrame with {len(data)} stations.")
        return gpd.GeoDataFrame(
            data.drop(columns=["PositionLon", "PositionLat"]),
            geometry = gpd.points_from_xy(coor["PositionLon"], coor["PositionLat"]),
            crs = self.default_coor
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
            parser=self._parsers.parse_operators
        )
    
    @cached_property
    def schedules(self) -> list[Schedule]:
        """
        Fetch bus stations timetable for the specified region.
        You can refresh the cache by `refresh_cache("stations_timetable")`.
        """
        def decoder(response: requests.Response) -> list[Schedule]:
            return msgspec.json.decode(response.content, type=list[Schedule])

        return self._fetch_combined_data(
            prefix="v2/Bus/Schedule",
            params={
                "$select": "RouteUID,SubRouteUID,Direction,OperatorID,Timetables,Frequencys,UpdateTime"
            },
            decoder=decoder
        )
    
    @cached_property
    def schedules_to_dataframe(self) -> pd.DataFrame:
        """
        Fetch bus stations timetable for the specified region, then cache it.
        You can refresh the cache by `refresh_cache("stations_timetable")`.
        """
        return self._parsers.parse_schedules(
            self.schedules
        ).sort_values(by=["RouteUID", "SubRouteUID", "Direction", "OperatorID"]).reset_index(drop=True)
            
    @cached_property
    def daily_timetables(self) -> list[DailySchedule]:
        """
        """
        def decoder(response: requests.Response) -> list[DailySchedule]:
            return msgspec.json.decode(response.content, type=list[DailySchedule])

        return self._fetch_combined_data(
            prefix="v2/Bus/DailyTimeTable",
            params={
                "$select": "BusDate,RouteUID,SubRouteUID,Direction,OperatorID,Timetables,UpdateTime"
            },
            decoder=decoder
        )
    
    @cached_property
    def daily_timetables_to_dataframe(self) -> pd.DataFrame:
        return self._parsers.parse_schedules(
            self.daily_timetables
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
        property_name: RefreshableCacheProperty | Literal["all"]  = "all"
        ) -> None:
        """
        Manually refresh the cached data for a specific property.
        This is useful if you want to ensure you have the most up-to-date information without waiting for the cache to expire.
        """
        refreshable_properties = {"routes", "stations", "routes_with_shape", "operators", "schedules", "daily_timetables"}
        refresh_targets: set[str]
        
        match property_name:
            case "all":
                refresh_targets = refreshable_properties
            case _ if property_name in refreshable_properties:
                refresh_targets = {property_name}
            case _:
                self.logger.warning(f"Invalid property name for cache refresh: {property_name}. Valid options are:\n\t {', '.join(refreshable_properties)}")
                raise
        
        if refresh_targets & {"stations", "routes_with_shape"}:
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