# Dependency imports
from functools import cached_property
from logging import Logger
from typing import Literal, TypeAlias
import msgspec, requests
import pandas as pd
import geopandas as gpd

from tdx_tool.authority import tdx_auth
# Local imports
from .bus_parsers import _bus_parsers
from .bus_models import RouteStops, Station, Operator, Alert, Schedule, DailySchedule
from .core import tdx_tool
from .common_models import Datas
from .utils import BusRegion

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
    
    Parameters
    ----------
    client_id: str
        TDX API Client ID (required)
    client_key: str
        TDX API Client Key (required)
    region: BusRegion, default=BusRegion.Intercity
        The region for which to fetch bus data.
    logger: Logger, optional
        Logger instance for logging. If not provided, a default logger that does not output anywhere will be used.
    
    Attributes
    ----------
    auth: tdx_auth
        an instance of `tdx_auth` for handling authentication, see `tdx_auth` class for details.
    logger: Logger
        a Logger instance for logging
    export_result: bool
        whether to export results
    default_coor: str, default="EPSG:4326"
        specifies the default coordinate reference system for geospatial data (default is WGS 84)
    output_path: str, default="output"
        the directory path where output files will be saved (default is "output")
    region: BusRegion (read-only)
        where the bus data is fetched for
    together: bool, default=False | None (adjustable)
        whether to fetch data for both regions with ambiguous name
        - `bool` for regions with ambiguous name
        - `None` for non-ambiguous region
    routes: Datas (cached)
        all bus routes for the region(s)
    routes_with_shape: Datas (cached)
        all bus routes with shape information for the region(s)
    stations: list[Station] (cached)
        all bus stations for the region(s)
    stations_to_dataframe: gpd.GeoDataFrame (cached)
        all bus stations for the region(s), in a tabular format with geometry
    operators: Dataframe (cached)
        all bus operators for the region(s)
    schedules: Datas (cached)
        all bus schedules for the region(s)
    daily_timetables: Datas (cached)
        all bus daily timetables for the region(s)
    alert: list[Alert] (immediately fetched, not cached)
        current alerts and warnings for bus services in the region(s)
    operate_status: list[Alert] (immediately fetched, not cached)
        Same as `alert` above
    
    Methods
    -------
    refresh_cache(property_name: RefreshableCacheProperty | Literal["all"]) -> None
        see `refresh_cache` method for details.
    get_schedule_for_route(route_name: str, only_departures: bool = False) -> pd.DataFrame
        see `get_schedule_for_route` method for details.
    fetch_estimated_arrival_for_routes(route_name: str) -> pd.DataFrame
        see `fetch_estimated_arrival_for_routes` method for details.
    fetch_estimated_arrival_for_stations(station_uid: str) -> pd.DataFrame
        see `fetch_estimated_arrival_for_stations` method for details.
    
    See Also
    --------
    - `tdx_auth`: for handling authentication with the TDx API.
    - `BusRegion`: for available bus regions and their details.
    - `Datas`: for understanding the data structure returned by the properties.    
    
    Examples
    --------
    When initializing, you can specify the region you want to fetch data for using the `region` parameter.
    >>> bus_tool = tdx_bus(client_id="your_client_id", client_key="your_client_key", region=BusRegion.Taipei)
    Or you can use the `from_region_str` class method to initialize with a region name string:
    >>> bus_tool = tdx_bus.from_region_str(client_id="your_client_id", client_key="your_client_key", region="Taipei")

    Note that some regions have ambiguous names (e.g., "Hsinchu" and "HsinchuCounty"). If you want to fetch data for
    both regions, set the `together` property to True:
    >>> bus_tool.together = True
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
        If the name is ambiguous (see `BusRegion` enum for details), the default will be the main city with it related
        county (or Taipei for New Taipei), 
        
        Parameters
        ----------
        client_id: str
            TDX API Client ID (required)
        client_key: str
            TDX API Client Key (required)
        region: str
            the name of the region you would like to fetch data for
        
        Returns
        -------
        tdx_bus
            An instance of `tdx_bus` initialized for the specified region.
            - Note that if the region name is ambiguous, default for together will be `True`.
        
        Raises
        ------
        ValueError
            the input string does not match any known region.
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
        Initialize the class for intercity bus data.

        Parameters
        ----------
        client_id: str
            TDX API Client ID (required)
        client_key: str
            TDX API Client Key (required)
        logger: Logger, optional
            Logger instance for logging. If not provided, a default logger that does not output anywhere will be used.

        Returns
        -------
        tdx_bus
            An instance of `tdx_bus` initialized for intercity bus data.
        """
        return cls(client_id=client_id, client_key=client_key, logger=logger)
    
    @classmethod
    def from_auth(cls,
        auth: tdx_auth,
        region: BusRegion,
        together: bool = False
    ) -> "tdx_bus":
        """
        Initialize the class with authentication information and a specific region.

        Parameters
        ----------
        auth: tdx_auth
            Authentication instance containing client ID and key.
        region: BusRegion
            The region for which to fetch data.
        together: bool, optional
            Whether to fetch data for both regions with ambiguous names. Default is False.

        Returns
        -------
        tdx_bus
            An instance of `tdx_bus` initialized with the provided authentication and region.
        """
        return cls(auth.client_id, auth.client_key, region, together, auth.logger)

    @property
    def together(self) -> bool | None:
        """
        whether to fetch data for both regions with ambiguous name
        - `bool` for regions with ambiguous name
        - `None` for non-ambiguous region
        """
        return self._together
    
    @together.setter
    def together(self, is_on: bool = True):
        self._together = True if self.__region.ambiguous_case is not None and is_on else None
    
    @property
    def region(self) -> BusRegion:
        """where this instance fetches data for"""
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
        def decoder(response: requests.Response) -> list[RouteStops]:
            return msgspec.json.decode(response.content, type=list[RouteStops])

        return self._fetch_combined_data(
            prefix="v2/Bus/StopOfRoute",
            params={
                "$select": ','.join(RouteStops.__struct_fields__)
            },
            decoder=decoder
        )
    
    @cached_property
    def routes(self) -> Datas:
        """all bus route for the specified region(s)"""
        from .bus_models import Route

        def decoder(response: requests.Response) -> list[Route]:
            return msgspec.json.decode(response.content, type=list[Route])
        
        def to_datafram(data: list[Route]) -> pd.DataFrame:
            return self._parsers.parse_routes(
                data
            ).sort_values(by=["RouteNameEn", "SubRouteUID"]).reset_index(drop=True)
        
        return Datas(
            data = self._fetch_combined_data(
                prefix="v2/Bus/Route",
                params={
                    "$select": ','.join(Route.__struct_fields__)
                },
                decoder=decoder),
            datatype = Route,
            parsers = {
                pd.DataFrame: to_datafram
            },
            description = f"All bus routes for region(s) {', '.join(self._url_middle_part())}."
        )
    
    @cached_property
    def routes_with_shape(self) -> Datas:
        """all bus route with shape information for the specified region(s)"""
        from .bus_models import RouteShape

        def decoder(response: requests.Response) -> list[RouteShape]:
            return msgspec.json.decode(response.content, type=list[RouteShape])
        
        def to_datafram(data: list[RouteShape]) -> pd.DataFrame:
            return self._parsers.parse_route_with_shape(
                data
            ).sort_values(by=["RouteNameEn", "SubRouteUID"]).reset_index(drop=True)
        
        def to_geodatafram(data: list[RouteShape]) -> gpd.GeoDataFrame:
            new_data = to_datafram(data).join(
                self.routes.to_dataframe.set_index(["RouteUID", "SubRouteUID"]),
                on=["RouteUID", "SubRouteUID"],
                how="left",
                rsuffix="_route"
            )
            return gpd.GeoDataFrame(new_data, geometry="geometry", crs=self.default_coor)

        return Datas(
            data = self._fetch_combined_data(
                prefix="v2/Bus/Shape",
                params={
                    "$select": ','.join(RouteShape.__struct_fields__)
                },
                decoder=decoder
            ),
            datatype = RouteShape,
            parsers = {
                pd.DataFrame: to_geodatafram,
                gpd.GeoDataFrame: to_geodatafram
            },
            description = f"All bus routes with shape information for region(s) {', '.join(self._url_middle_part())}."
        )

    @cached_property
    def stations(self) -> list[Station]:
        """all bus stations for the specified region(s)"""
        from .bus_models import StationFraction
        def decoder(response: requests.Response) -> list[StationFraction]:
            return msgspec.json.decode(response.content, type=list[StationFraction])

        return list(self._parsers.parse_stations(
            self._route_stops,
            self._fetch_combined_data(
                prefix="v2/Bus/Station",
                params={
                    "$select": ','.join(StationFraction.__struct_fields__)
                },
                decoder=decoder
            )
        ).values())
    
    @cached_property
    def stations_to_dataframe(self) -> pd.DataFrame:
        """all bus stations for the specified region(s), in a tabular format with geometry"""
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
        """all bus operators for the specified region(s)"""
        def decoder(response: requests.Response) -> list[Operator]:
            return msgspec.json.decode(response.content, type=list[Operator])
        
        return self._fetch_combined_data(
            prefix="v2/Bus/Operator",
            params={
                "$select": ','.join(Operator.__struct_fields__)
            },
            decoder=decoder,
            parser=self._parsers.parse_operators
        )
    
    @cached_property
    def schedules(self) -> Datas:
        """the common operating schedules for all bus routes in the specified region(s)"""
        def decoder(response: requests.Response) -> list[Schedule]:
            return msgspec.json.decode(response.content, type=list[Schedule])
        
        def to_dataframe(data: list[Schedule]) -> pd.DataFrame:
            return self._parsers.parse_schedules(
                data
            ).sort_values(by=["RouteUID", "SubRouteUID", "Direction", "OperatorID"]).reset_index(drop=True)

        return Datas(
            data = self._fetch_combined_data(
                prefix="v2/Bus/Schedule",
                params={
                    "$select": ','.join(Schedule.__struct_fields__)
                },
                decoder=decoder),
            datatype = Schedule,
            parsers = {
                pd.DataFrame: to_dataframe
            },
        )
            
    @cached_property
    def daily_timetables(self) -> Datas:
        """daily timetables for all bus routes for recently dates in the specified region(s)"""
        def decoder(response: requests.Response) -> list[DailySchedule]:
            return msgspec.json.decode(response.content, type=list[DailySchedule])
        
        def to_dataframe(data: list[DailySchedule]) -> pd.DataFrame:
            return self._parsers.parse_schedules(
                data
            ).sort_values(by=["RouteUID", "SubRouteUID", "Direction"]).reset_index(drop=True)

        return Datas(
            data = self._fetch_combined_data(
                prefix="v2/Bus/DailyTimeTable",
                params={
                    "$select": ','.join(DailySchedule.__struct_fields__)
                },
                decoder=decoder
            ),
            datatype = DailySchedule,
            parsers = {
                pd.DataFrame: to_dataframe
            }
        )

    @property
    def alert(self) -> list[Alert]:
        """Same as operate_status, because TDx name it "Alert" but the content is more like "OperateStatus". We keep both names for better user experience."""
        def decoder(response: requests.Response) -> list[Alert]: # type: ignore
            return msgspec.json.decode(response.content, type=list[Alert])
        
        return self._fetch_combined_data(
            prefix="v2/Bus/Alert",
            params={
                "$select": ','.join(Alert.__struct_fields__)
            },
            decoder=decoder
        )

    @property
    def operate_status(self) -> list[Alert]:
        """such as weather-related disruptions, traffic incidents affecting bus routes, and other urgent notifications."""
        return self.alert
    
    def refresh_cache(
        self,
        property_name: RefreshableCacheProperty | Literal["all"]  = "all"
        ) -> None:
        """
        Manually refresh the cached data for a specific property.
        This is useful if you want to ensure you have the most up-to-date information without waiting for the cache to expire.

        Parameters
        ----------
        property_name: RefreshableCacheProperty | Literal["all"], default="all"
            The name of the property to refresh. Valid options are:
            - `routes`: Refresh the cache for bus routes.
            - `stations`: Refresh the cache for bus stations.
            - `routes_with_shape`: Refresh the cache for bus routes with shape information.
            - `operators`: Refresh the cache for bus operators.
            - `schedules`: Refresh the cache for bus schedules.
            - `daily_timetables`: Refresh the cache for daily timetables.
            - `all`: Refresh the cache for all properties.
        
        Notes
        -----
        If the key for the specified property does not exist in the cache, it will simply
        be ignored and output a warning message into the logger.
        """
        refreshable_properties = {"routes", "stations", "routes_with_shape", "operators", "schedules", "daily_timetables"}
        refresh_targets: set[str] = set()
        
        match property_name:
            case "all":
                refresh_targets = refreshable_properties
            case _ if property_name in refreshable_properties:
                refresh_targets = {property_name}
            case _:
                self.logger.warning(f"Invalid property name for cache refresh: {property_name}. Valid options are:\n\t {', '.join(refreshable_properties)}")
                return
        
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