# Dependencies
from functools import cached_property
from typing import Literal, TypeAlias, Self
import pandas as pd
import geopandas as gpd
# Local imports
from ...core import Fetch, Zone
from ...core.wrapper import Wrapper
from ...core.tool import Tool
from .bus_parsers import BusParsers
from .bus_models import RouteStops, Station, Alert

RefreshableCacheProperty: TypeAlias = Literal[
    "routes",
    "stations",
    "routes_with_shape",
    "operators",
    "schedules",
    "daily_timetables",
]

class BusTool(Tool):
    def __init__(
        self,
        fetch: Fetch,
        region: Zone = Zone.INTERZONES,
        *,
        together: bool = True
    ):
        if not isinstance(region, Zone):
            raise ValueError(f"The region must be an instance of Zone.")
        super().__init__(fetch)
        self._together = None
        self._region = region
        if region.isAmbiguous:
            self._together = together

    @classmethod
    def intercity(cls, fetch: Fetch) -> Self:
        return cls(fetch)

    @property
    def _parsing(self) -> BusParsers:
        return BusParsers(self.crs, self.logger)

    @property
    def together(self) -> bool | None:
        return self._together

    @property
    def _regions(self) -> list[Zone]:
        result = [self._region]
        if self.together is True:
            result.append(self._region.switch_to_ambiguous)
        return result
    
    @property
    def cover_zones(self) -> list[str]:
        return [region.to_id.name for region in self._regions]
    
    @property
    def __region_description(self) -> str:
        match self._region:
            case Zone.INTERZONES:
                return "Intercity Bus (Governed by MOTC)"
            case (Zone.TAIPEI
                 |Zone.NEW_TAIPEI
                 ) if self._together:
                return "Taipei Metropolitan Area (Taipei + New Taipei)"
            case _ if self._together:
                return f"Great {' '.join(self._region.name.split('_')[:-1])} (City + County)"
            case _:
                return self._region.name
    
    @property
    def __api_tag_cities(self) -> list[str]:
        if self._region == Zone.INTERZONES:
            return ["InterCity"]
        else:
            return [f"City/{region.api_tag_city}" for region in self._regions]

    def __api(self, url: str) -> list[str]:
        return [f"{url}/{city}" for city in self.__api_tag_cities]
    
    @cached_property
    def _route_stops(self) -> list[RouteStops]:
        return self.fetch.retrieve_datas(
            self.__api("v2/Bus/StopOfRoute"),
            RouteStops
        )
    
    @cached_property
    def routes(self) -> Wrapper:
        from .bus_models import Route
        return Wrapper(
            data=self.fetch.retrieve_datas(
                self.__api("v2/Bus/Route"),
                Route
            ),
            datatype=Route,
            parsers={
                pd.DataFrame: self._parsing.parse_routes
            },
            description=f"Bus Routes in {self.__region_description}"
        )

    @cached_property
    def routes_with_shape(self) -> Wrapper:
        from .bus_models import RouteShape
        return Wrapper(
            data=self.fetch.retrieve_datas(
                self.__api("v2/Bus/Shape"),
                RouteShape,
                params={"$orderby": "RouteID asc"}
            ),
            datatype=RouteShape,
            parsers={
                pd.DataFrame: self._parsing.parse_shapes_to_df,
                gpd.GeoDataFrame: self._parsing.parse_shapes_to_gdf
            },
            hasSpatial=True,
            description=f"Bus Routes with Shape in {self.__region_description}"
        )
    
    @cached_property
    def stations(self) -> Wrapper:
        # TODO: FIX LOGIC CONFUSING
        from .bus_models import StationFraction
        sta_frac = self.fetch.retrieve_datas(
            self.__api("v2/Bus/Station"),
            StationFraction
        )
        station_map = self._parsing.parse_stations(self._route_stops, sta_frac)
        stations = [s for station_list in station_map.values() for s in station_list]
        return Wrapper(
            data=stations,
            datatype=Station,
            parsers={
                pd.DataFrame: lambda _stations: self._parsing.parse_stations_to_df(self._route_stops)
            },
            hasSpatial=True,
            description=f"Bus Stations in {self.__region_description}"
        )

    @cached_property
    def operators(self) -> Wrapper:
        """all bus operators for the specified region(s)"""
        from .bus_models import Operator
        return Wrapper(
            data=self.fetch.retrieve_datas(
                self.__api("v2/Bus/Operator"),
                Operator
            ),
            datatype=Operator,
            parsers={
                pd.DataFrame: self._parsing.parse_operators
            },
            description=f"Bus Operators in {self.__region_description}"
        )
    
    @cached_property
    def schedules(self) -> Wrapper:
        """the common operating schedules for all bus routes in the specified region(s)"""
        from .bus_models import Schedule
        def to_dataframe(data: list[Schedule]) -> pd.DataFrame:
            return self._parsing.parse_schedules(
                data
            ).sort_values(by=["RouteUID", "SubRouteUID", "Direction", "OperatorID"]).reset_index(drop=True)

        return Wrapper(
            data = self.fetch.retrieve_datas(
                self.__api("v2/Bus/Schedule"),
                Schedule
            ),
            datatype = Schedule,
            parsers = {
                pd.DataFrame: to_dataframe
            },
            description=f"Bus Schedules in {self.__region_description}"
        )
            
    @cached_property
    def daily_timetables(self) -> Wrapper:
        """daily timetables for all bus routes for recently dates in the specified region(s)"""
        from .bus_models import DailySchedule
        def to_dataframe(data: list[DailySchedule]) -> pd.DataFrame:
            return self._parsing.parse_schedules(
                data
            ).sort_values(by=["RouteUID", "SubRouteUID", "Direction"]).reset_index(drop=True)

        return Wrapper(
            data = self.fetch.retrieve_datas(
                self.__api("v2/Bus/DailyTimeTable"),
                DailySchedule
            ),
            datatype = DailySchedule,
            parsers = {
                pd.DataFrame: to_dataframe
            },
            description=f"Daily Timetables in {self.__region_description}"
        )
    
    @property
    def alert(self) -> list[Alert]:
        """Same as operate_status, because TDx name it "Alert" but the content is more like "OperateStatus". We keep both names for better user experience."""
        return self.fetch.retrieve_datas(
            self.__api("v2/Bus/Alert"),
            Alert
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
            vars(self).pop("_route_stops", None)  # Clear the cached route stops if stations or routes_with_shape is being refreshed

        for target in refresh_targets:
            vars(self).pop(target, None)  # Remove the cached property if it exists
            self.logger.info(f"Cache for `{target}` has been refreshed.")