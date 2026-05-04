# Dependency imports
from functools import cached_property, cache
from logging import Logger
from typing import Literal
import logging, msgspec
import pandas as pd
import geopandas as gpd

# Local imports
from .core import tdx_tool
from .utils import BusRegion, I18n


class tdx_bus(tdx_tool):
    """

    """
    identity_type = Literal["RouteUID", "RouteID", "RouteName", "RouteNameEn"]
    class SubRoute(msgspec.Struct):
        SubRouteUID: str
        SubRouteID: str
        Direction: int
        SubRouteName: I18nName
        OperatorIDs: list[str] = []
        Headsign: str | None = None
        HeadsignEn: str | None = None
        DepartureStopNameZh: str | None = None
        DepartureStopNameEn: str | None = None
        DestinationStopNameZh: str | None = None
        DestinationStopNameEn: str | None = None
            
    class Route(msgspec.Struct):
        RouteUID: str
        BusRouteType: int
        RouteName: I18nName
        UpdateTime: str
        VersionID: int
        DepartureStopNameZh: str | None = None
        DepartureStopNameEn: str | None = None
        DestinationStopNameZh: str | None = None
        DestinationStopNameEn: str | None = None
        SubRoutes: list[SubRoute] = []
    
    class PointPosition(msgspec.Struct):
        PositionLon: float
        PositionLat: float
        GeoHash: str
    
    class Stop(msgspec.Struct):
        StopUID: str
        StopName: I18nName
        RouteUID: str
        RouteName: I18nName
    
    class Station(msgspec.Struct):
        StationUID: str
        StationName: I18nName
        StationPosition: PointPosition
        StationAddress: str = None
        StationGroupID: str = None
        Stops: list[Stop]
        LocationCityCode: str = None
        Bearing: str = None
        UpdateTime: str = None
    


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

    def _url_middle_part(self) -> [str]:
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
        import requests.Response
        def generate_url(middle_part: str) -> str:
            return f"v2/Bus/Route/{middle_part}?%24format=JSON"
        
        def fetch_routes(url: str) -> requests.Response:
            params = {
                "$select": "RouteUID,BusRouteType,RouteName,DepartureStopNameZh,DepartureStopNameEn,DestinationStopNameZh,DestinationStopNameEn,UpdateTime,VersionID,SubRoutes"
            }
            self.logger.debug(f"Fetching bus routes from URL: {url}")
            return self._get_data_from_suffix_url(url, params=params)
        
        def decode_routes(response: Response) -> pd.DataFrame:
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
        self.logger.debug(f"Fetching bus routes from URL: {url}")

        url = self._url_middle_part()
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
        import requests.Response
        def generate_url(middle_part: str) -> str:
            return f"v2/Bus//{middle_part}?%24format=JSON"
        
        def fetch_stations(url: str) -> requests.Response:
            params = {
                "$select": "StopUID,StopName,StopPosition,StopAddress,Bearing,StationID,StationGroupID,StopDescription,CityCode,LocationCityCode,UpdateTime"
            }
            self.logger.debug(f"Fetching bus stations from URL: {url}")
            return self._get_data_from_suffix_url(url, params=params)
        
        def decode_stations(response: Response) -> pd.DataFrame:
            
            
            
            stops = msgspec.json.decode(response.content, type=list[self.Stop])
            
            data = []
            for s in parsed_stops:
                data.append({
                    "StopUID": s.StopUID,
                    "StopName_Zh_tw": s.StopName.Zh_tw,
                    "StopName_En": s.StopName.En,
                    "PositionLon": s.StopPosition.PositionLon,
                    "PositionLat": s.StopPosition.PositionLat,
                    "GeoHash": s.StopPosition.GeoHash,
                    "StopAddress": s.StopAddress,
                    "Bearing": s.Bearing,
                    "StationID": s.StationID,
                    "StationGroupID": s.StationGroupID,
                    "StopDescription": s.StopDescription,
                    "CityCode": s.CityCode,
                    "LocationCityCode": s.LocationCityCode,
                    "UpdateTime": s.UpdateTime
                })

            return pd.DataFrame(data)
        
        # Main logic of get_stops
        self.logger.debug(f"Fetching bus stops from URL: {url}")

        url = self._url_middle_part()
        data = decode_stops(fetch_stops(url[0]))

        if self._together:
            self.logger.debug(f"Fetching stops for ambiguous region: {self.region.ambiguous_name}")
            ambiguous_data = decode_stops(fetch_stops(url[1]))
            data = pd.concat([data, ambiguous_data], ignore_index=True)

        return data