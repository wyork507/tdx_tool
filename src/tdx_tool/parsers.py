# Dependencies
from logging import Logger
import requests, shapely, msgspec
import pandas as pd
import geopandas as gpd
# Local imports
import bus_models as bus
from .utils import I18n


class _bus_parsers:
    @staticmethod
    def parse_routes(routes: list[bus.Route]) -> pd.DataFrame:
        """
        """
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
    
    @staticmethod
    def parse_route_with_shape(routes: list[bus.RouteShape]) -> pd.DataFrame:
        """
        """
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
    
    @staticmethod
    def parse_stations(route_stops: list[bus.RouteStops]) -> pd.DataFrame:
        """
        """
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
    
    @staticmethod
    def parse_operators(operators: list[bus.Operator]) -> pd.DataFrame:
        """
        """
        data = []
        for op in operators:
            data.append({
                "OperatorID": op.OperatorID,
                "OperatorNameZh": op.OperatorName.Zh_tw,
                "OperatorNameEn": op.OperatorName.En
            })
        return pd.DataFrame(data)