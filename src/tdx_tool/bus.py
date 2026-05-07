# Dependency imports
from functools import cached_property, cache
from logging import Logger
from typing import Literal, Optional
import logging, msgspec
import pandas as pd
import geopandas as gpd

# Local imports
from .core import tdx_tool
from .utils import BusRegion, I18n


class tdx_bus(tdx_tool):
    """

    """
    class SubRoute(msgspec.Struct):
        SubRouteUID: str
        SubRouteID: str
        Direction: int
        SubRouteName: I18n
        OperatorIDs: list[str] = []
        Headsign: Optional[str] = None
        HeadsignEn: Optional[str] = None
        DepartureStopNameZh: Optional[str] = None
        DepartureStopNameEn: Optional[str] = None
        DestinationStopNameZh: Optional[str] = None
        DestinationStopNameEn: Optional[str] = None
            
    class Route(msgspec.Struct):
        RouteUID: str
        BusRouteType: int
        RouteName: I18n
        UpdateTime: str
        VersionID: int
        DepartureStopNameZh: Optional[str] = None
        DepartureStopNameEn: Optional[str] = None
        DestinationStopNameZh: Optional[str] = None
        DestinationStopNameEn: Optional[str] = None
        SubRoutes: list[SubRoute] = [] # type: ignore
    
    class PointPosition(msgspec.Struct):
        PositionLon: float
        PositionLat: float
        GeoHash: str
    
    class Stop(msgspec.Struct):
        StopUID: str
        StopName: I18n
        StopBoarding: int
        StopSequence: int
        StopPosition: PointPosition # type: ignore
        RouteUID: str
        RouteName: I18n
        StationID: str
        StationGroupID: str
    
    class Station(msgspec.Struct):
        StationUID: str
        StationName: Optional[I18n] = None
        StationPosition: PointPosition # type: ignore
        StationAddress: Optional[str] = None
        StationGroupID: Optional[str] = None
        Stops: list[Stop] # type: ignore
        LocationCityCode: Optional[str] = None
        Bearing: Optional[str] = None
        UpdateTime: Optional[str] = None
    
    class Operator(msgspec.Struct):
        OperatorID: str
        OperatorName: I18n

    class RouteStops(msgspec.Struct):
        RouteUID: str
        SubRouteUID: str
        RouteName: I18n
        SubRouteName: I18n
        Stops: list[Stop] # type: ignore
        OpratiorIDs: list[Operator] # type: ignore
        Direction: int
        City: str
        CityCode: str
        UpdateTime: str

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
    def get_routes(self) -> pd.DataFrame:
        """
        Fetch bus routes for the specified region.
        If the region has an ambiguous name, it will fetch routes for both regions if `together` is set to True.
        """
        import requests.Response # type: ignore
        def generate_url(middle_part: str) -> str:
            return f"v2/Bus/Route/{middle_part}?%24format=JSON"
        
        def fetch_routes(url: str) -> requests.Response: # type: ignore
            params = {
                "$select": "RouteUID,BusRouteType,RouteName,DepartureStopNameZh,DepartureStopNameEn,DestinationStopNameZh,DestinationStopNameEn,UpdateTime,VersionID,SubRoutes"
            }
            self.logger.debug(f"Fetching bus routes from URL: {url}")
            return self._get_data_from_suffix_url(url, params=params)
        
        def decode_routes(response: Response) -> pd.DataFrame: # type: ignore
            routes = msgspec.json.decode(response.content, type=list[self.Route])
            
            data = []
            for r in routes:
                route_base = {
                    "RouteUID": r.RouteUID,
                    "RouteNameZh": r.RouteName.Zh_tw,
                    "RouteNameEn": r.RouteName.En,
                    "BusRouteType": r.BusRouteType,
                    "UpdateTime": r.UpdateTime,
                    "Route_Departure_Zh": r.DepartureStopNameZh,
                    "Route_Departure_En": r.DepartureStopNameEn,
                    "Route_Destination_Zh": r.DestinationStopNameZh,
                    "Route_Destination_En": r.DestinationStopNameEn,
                }
                
                if not r.SubRoutes:
                    data.append(route_base)
                    continue
                
                for sub in r.SubRoutes:
                    row = route_base.copy() 
                    row.update({
                        "SubRouteUID": sub.SubRouteUID,
                        "SubRouteNameZh": sub.SubRouteName.Zh_tw,
                        "SubRouteNameEn": sub.SubRouteName.En,
                        "Direction": sub.Direction,
                        "Headsign": sub.Headsign,
                        "Sub_DepartureZh": sub.DepartureStopNameZh,
                        "Sub_DepartureEn": sub.DepartureStopNameEn,
                        "Sub_DestinationZh": sub.DestinationStopNameZh,
                        "Sub_DestinationEn": sub.DestinationStopNameEn
                    })
                    data.append(row)
            
            return pd.DataFrame(data)
        
        # Main logic of get_routes
        url = self._url_middle_part()
        self.logger.debug(f"Fetching bus routes from URL: {url}")
        data = decode_routes(fetch_routes(url[0]))

        if self._together:
            self.logger.debug(f"Fetching routes for ambiguous region: {self.region.ambiguous_name}")
            ambiguous_data = decode_routes(fetch_routes(url[1]))
            data = pd.concat([data, ambiguous_data], ignore_index=True)

        return data
        
    @cached_property
    def get_stations(self) -> gpd.GeoDataFrame:
        """
        Fetch bus stations for the specified region.
        If the region has an ambiguous name, it will fetch stations for both regions if `together` is set to True.
        """
        import requests.Response # type: ignore
        def generate_url(middle_part: str) -> str:
            return f"v2/Bus/StopOfRoute/{middle_part}?%24format=JSON"
        
        def fetch_stop_of_route(url: str) -> requests.Response:
            params = {
                "$select": "RouteUID,SubRouteUID,RouteName,SubRouteName,Stops,OpratiorIDs,Direction,City,CityCode,UpdateTime"
            }
            self.logger.debug(f"Fetching bus stations from URL: {url}")
            return self._get_data_from_suffix_url(url, params=params)
        
        def decode_stations(response: Response) -> pd.DataFrame: # type: ignore
            route_stops = msgspec.json.decode(response.content, type=list[self.RouteStops])

            data = []
            for route in route_stops:
                for s in route.Stops:
                    data.append({
                        "StationID": s.StationID,
                        "StationGroupID": s.StationGroupID,
                        "StopUID": s.StopUID,
                        "StopNameZh": s.StopName.Zh_tw,
                        "StopNameEn": s.StopName.En,
                        "RouteUID": route.RouteUID,
                        "RouteNameZh": route.RouteName.Zh_tw,
                        "RouteNameEn": route.RouteName.En,
                        "SubRouteUID": route.SubRouteUID,
                        "SubRouteNameZh": route.SubRouteName.Zh_tw,
                        "SubRouteNameEn": route.SubRouteName.En,
                        "Direction": route.Direction,
                        "Sequence": s.StopSequence,
                        "Boarding": s.StopBoarding,
                        "OperatorIDs": ",".join([op.OperatorID for op in route.OpratiorIDs]),
                        "City": route.City,
                        "CityCode": route.CityCode,
                        "UpdateTime": route.UpdateTime,
                        "StopNameZh": s.StopName.Zh_tw,
                        "StopNameEn": s.StopName.En,
                        "PositionLon": s.StopPosition.PositionLon,
                        "PositionLat": s.StopPosition.PositionLat,
                        "GeoHash": s.StopPosition.GeoHash
                    })
            
            return pd.DataFrame(data)
        
        # Main logic of get_stops
        url_parts = self._url_middle_part()
        self.logger.debug(f"Fetching bus stations from URL: {url_parts[0]}")
        data = decode_stations(fetch_stop_of_route(url_parts[0]))

        
        if self._together:
            self.logger.debug(f"Fetching stops for ambiguous region: {self.region.ambiguous_name}")
            ambiguous_data = decode_stations(fetch_stop_of_route(url_parts[1]))
            data = pd.concat([data, ambiguous_data], ignore_index=True)

        return gpd.GeoDataFrame(
                data.sort_values(by=["StationID", "SubRouteUID", "Sequence"]).reset_index(drop=True),
                geometry=gpd.points_from_xy(data["PositionLon"], data["PositionLat"]),
                crs=self._default_coor
            )
    
    @cached_property
    def news(self) -> pd.DataFrame:
        """
        Fetch the latest news and updates related to bus services in the specified region.
        This may include service disruptions, new route launches, and other important announcements.
        """
        pass

    @cached_property
    def alert(self) -> pd.DataFrame:
        """
        Fetch current alerts and warnings for bus services in the specified region.
        This may include weather-related disruptions, traffic incidents affecting bus routes, and other urgent notifications.
        """
        pass
    
    def get_route_details(
            self,
            route_name: str,
            output_format: Optional[tdx_tool.GEOG_OUTPUT_TYPE] = None
            ) -> gpd.GeoDataFrame:
        """
        Route details include operator information, its subroutes, and
        all stops along the route with their sequence and boarding information.
        """
        import requests.Response # type: ignore
        def generate_url(middle_part: str) -> dict[str, str]:
            return {
                "stop_of_route": f"v2/Bus/StopOfRoute/{middle_part}/{route_name}?%24format=JSON",
                "route": f"v2/Bus/Route{middle_part}/{route_name}?%24format=JSON"
            }
        
        # TODO: Implement the fetch_route_details function
        def fetch_route_details(url: str) -> requests.Response: # type: ignore
            params = {
                "$select": ""
            }
            self.logger.debug(f"Fetching route details from URL: {url}")
            return self._get_data_from_suffix_url(url, params=params)
        
        pass

    # TODO
    def get_estimated_arrival_for_route(self, route_name: str) -> pd.DataFrame:
        """
        Fetch real-time bus information for a specific route.
        This includes estimated arrival times, current bus locations, and occupancy status.
        """
        pass

    # TODO
    def get_estimated_arrival_for_station(self, station_uid: str) -> pd.DataFrame:
        """
        Fetch real-time bus information for a specific station.
        This includes estimated arrival times for all routes serving the station, current bus locations, and occupancy status.
        """
        pass

    # TODO
    def get_schedule_for_route(self, route_name: str, ) -> pd.DataFrame:
        """
        Fetch the schedule for a specific route.
        This includes departure times from the starting point, arrival times at the destination, and frequency of service throughout the day.
        """
        pass
