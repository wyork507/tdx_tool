# Dependencies
from logging import Logger
import requests, shapely, msgspec
import pandas as pd
import geopandas as gpd
# Local imports
from .bus_models import *


class _bus_parsers:
    @staticmethod
    def parse_routes(routes: list[Route]) -> pd.DataFrame:
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
    def parse_route_with_shape(routes: list[RouteShape]) -> pd.DataFrame:
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
    def parse_stations(route_stops: list[RouteStops]) -> pd.DataFrame:
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
                    "OperatorIDs": ",".join([op.OperatorID for op in route.Operators]),
                    "City": route.City,
                    "CityCode": route.CityCode,
                    "UpdateTime": route.UpdateTime,
                    "PositionLon": s.StopPosition.PositionLon,
                    "PositionLat": s.StopPosition.PositionLat,
                    "GeoHash": s.StopPosition.GeoHash
                })
        return pd.DataFrame(data)
    
    @staticmethod
    def parse_operators(operators: list[Operator]) -> pd.DataFrame:
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
    
    @staticmethod
    def parse_alerts(alerts: list[Alert]) -> pd.DataFrame:
        data = []
        for a in alerts:
            base = pd.DataFrame()
            base["AlertID"] = a.AlertID
            base["TitleZh"] = a.Title
            base["Description"] = a.Description
            base["Department"] = a.Department
            base["Status"] = a.Status
            base["SrcUpdateTime"] = a.SrcUpdateTime
            base["UpdateTime"] = a.UpdateTime
            s: dict = a.Scope # type: ignore
            if a.Status == 1:
                data.append(base)
            else:
                base["Cause"] = a.Cause
                base["Effect"] = a.Effect
                base["PublishTime"] = a.PublishTime
                base["StartTime"] = a.StartTime
                base["EndTime"] = a.EndTime
                
                scope: pd.DataFrame = pd.json_normalize(
                    s, record_path = list(s.keys()), sep = ""
                    )
                for _, row in scope.iterrows():
                    base_copy = base.copy()
                    for key, value in row.items():
                        base_copy[key] = value
                    data.append(base_copy)

        return pd.concat(data, axis=0, ignore_index=True)


    @staticmethod
    def parse_schedules(schedules: list[Schedule]) -> pd.DataFrame:
        """
        """
        data = []
        for s in schedules:
            base_info = {
                "RouteUID": s.RouteUID,
                "RouteNameZh": s.RouteName.Zh_tw,
                "RouteNameEn": s.RouteName.En,
                "SubRouteUID": s.SubRouteUID,
                "SubRouteNameZh": s.SubRouteName.Zh_tw,
                "SubRouteNameEn": s.SubRouteName.En,
                "Direction": s.Direction,
                "OperatorID": s.OperatorID,
                "UpdateTime": s.UpdateTime
            }
            if s.has_timetable:
                for t in s.Timetables:
                    row = base_info.copy()
                    row.update({
                        "TripID": t.TripID,
                        "isLowFloor": t.isLowFloor,
                        "StopNameZh": t.StopName.Zh_tw,
                        "StopNameEn": t.StopName.En,
                        "ArrivalTime": t.ArrivalTime,
                        "DepartureTime": t.DepartureTime,
                        "StopSequence": t.StopSequence
                    })
                    data.append(row)
        return pd.DataFrame(data)