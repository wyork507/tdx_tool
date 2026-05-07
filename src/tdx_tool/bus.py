# Dependency imports
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
from .core import tdx_tool
from .utils import BusRegion, I18n


class tdx_bus(tdx_tool):
    """

    """
    class Operator(msgspec.Struct):
        OperatorID: str
        OperatorName: I18n

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
        Operators: list[Operator] = []
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

    class RouteStops(msgspec.Struct):
        RouteUID: str
        SubRouteUID: str
        RouteName: I18n
        SubRouteName: I18n
        Stops: list[Stop] # type: ignore
        OperatorIDs: list[Operator] # type: ignore
        Direction: int
        City: str
        CityCode: str
        UpdateTime: Optional[str] = None
    
    class RouteShape(msgspec.Struct):
        RouteUID: str
        SubRouteUID: str
        RouteName: I18n
        Direction: int
        Geometry: Optional[str] = None
        EncodedPolyline: str
        UpdateTime: Optional[str] = None

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
    def _route_stops(self) -> list[self.RouteStops]:
        def decode(response: Response) -> list[self.RouteStops]: # type: ignore
            return msgspec.json.decode(response.content, type=list[self.RouteStops])
        
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
        def decoder(response: requests.Response) -> list[self.Route]: # type: ignore
            return msgspec.json.decode(response.content, type=list[self.Route])

        def parser(routes: list[self.Route]) -> pd.DataFrame: # type: ignore
            data = []
            for r in routes:
                operators = pd.DataFrame([{
                    "OperatorID": op.OperatorID,
                    "OperatorNameZh": op.OperatorName.Zh_tw,
                    "OperatorNameEn": op.OperatorName.En
                } for op in r.Operators])

                route_base = {
                    "RouteUID": r.RouteUID,
                    "RouteNameZh": r.RouteName.Zh_tw,
                    "RouteNameEn": r.RouteName.En,
                    "BusRouteType": r.BusRouteType,
                    "Operators": operators,
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
        # Main logic
        return self._fetch_combined_data(
            prefix="v2/Bus/Route",
            params={
                "$select": "RouteUID,Operators,BusRouteType,RouteName,DepartureStopNameZh,DepartureStopNameEn,DestinationStopNameZh,DestinationStopNameEn,UpdateTime,VersionID,SubRoutes"
            },
            decoder=decoder,
            parser=parser
        ).sort_values(by=["RouteNameEn", "SubRouteUID"]).reset_index(drop=True)
    
    @cached_property
    def routes_with_shape(self) -> gpd.GeoDataFrame:
        """
        """
        def decoder(response: requests.Response) -> list[self.RouteShape]: # type: ignore
            return msgspec.json.decode(response.content, type=list[self.RouteShape])
        
        def parser(routes: list[self.RouteShape]) -> pd.DataFrame: # type: ignore
            data = []
            for r in routes:
                try:
                    geometry = shapely.wkt.loads(r.Geometry)
                except Exception as e:
                    self.logger.error(f"Error loading geometry for route {r.RouteUID}: {e}")
                    geometry = None

                data.append({
                    "RouteUID": r.RouteUID,
                    "SubRouteUID": r.SubRouteUID,
                    "RouteNameZh": r.RouteName.Zh_tw,
                    "RouteNameEn": r.RouteName.En,
                    "Direction": r.Direction,
                    "UpdateTime": r.UpdateTime,
                    "geometry": geometry
                })
            return pd.DataFrame(data)
        # Main logic
        data = self._fetch_combined_data(
            prefix="v2/Bus/Shape",
            params={
                "$select": "RouteUID,SubRouteUID,RouteName,Direction,Geometry,EncodedPolyline,UpdateTime"
            },
            decoder=decoder,
            parser=parser
        )
        data.sort_values(by=["RouteNameEn", "SubRouteUID"], inplace=True)
        data.reset_index(drop=True, inplace=True)
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
        def parser(route_stops: list[self.RouteStops]) -> pd.DataFrame: # type: ignore
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
                        "OperatorIDs": ",".join([op.OperatorID for op in route.OperatorIDs]),
                        "City": route.City,
                        "CityCode": route.CityCode,
                        "UpdateTime": route.UpdateTime,
                        "PositionLon": s.StopPosition.PositionLon,
                        "PositionLat": s.StopPosition.PositionLat,
                        "GeoHash": s.StopPosition.GeoHash
                    })
            
            return pd.DataFrame(data)
        # Main logic
        data = parser(self._route_stops)
        data.sort_values(by=["StationID", "SubRouteNameEn", "Sequence"], inplace=True)
        data.reset_index(drop=True, inplace=True)
        coor = data[["PositionLon", "PositionLat"]]
        self.logger.debug(f"Creating GeoDataFrame with {len(data)} stations.")
        return gpd.GeoDataFrame(
                data.drop(columns=["PositionLon", "PositionLat"]),
                geometry=gpd.points_from_xy(coor["PositionLon"], coor["PositionLat"]),
                crs=self._default_coor
            )
    
    @property
    def operate_status(self) -> pd.DataFrame:
        """
        Fetch current alerts and warnings for bus services in the specified region.
        This may include weather-related disruptions, traffic incidents affecting bus routes, and other urgent notifications.
        """
        pass

    @property
    def alert(self) -> pd.DataFrame:
        """
        Same as operate_status, because TDx name it "Alert" but the content is more like "OperateStatus".
        We keep both names for better user experience.
        """
        return self.operate_status

    def refresh_cache(self, property_name: Literal["routes", "stations", "shape", "all"] = None) -> None:
        """
        Manually refresh the cached data for a specific property.
        This is useful if you want to ensure you have the most up-to-date information without waiting for the cache to expire.
        """
        match property_name:
            case "routes":
                self.__dict__.pop("routes", None)
                self.logger.info("Cache for routes has been refreshed.")
            case "stations":
                self.__dict__.pop("stations", None)
                self.logger.info("Cache for stations has been refreshed.")
            case "shape":
                self.__dict__.pop("routes_with_shape", None)
                self.logger.info("Cache for shape has been refreshed.")
            case "all":
                self.__dict__.pop("routes", None)
                self.__dict__.pop("stations", None)
                self.__dict__.pop("routes_with_shape", None)
                self.logger.info("Cache for all has been refreshed.")
            case _:
                self.logger.warning("Invalid name, please specify a valid cache name.")


    def get_route_details(
            self,
            route_name: str,
            output_format: Optional[tdx_tool.GEOG_OUTPUT_TYPE] = None
            ) -> gpd.GeoDataFrame:
        """
        Route details include operator information, its subroutes, and
        all stops along the route with their sequence and boarding information.
        """
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
    def get_schedule_for_route(self, route_name: str, only_departures: bool = False) -> pd.DataFrame:
        """
        Fetch the schedule for a specific route.
        This includes departure times from the starting point, arrival times at the destination, and frequency of service throughout the day.
        """
        pass
