# Dependencies
from datetime import datetime, time, date
from logging import Logger
import pandas as pd
import geopandas as gpd
import shapely
# Local imports
from .bus_models import DailySchedule, Route, RouteShape, RouteStops, Alert, Schedule, Operator
from .bike_models import Station, Availability
from .common_models import I18n

class _parsers:
    def __init__(self, logger: Logger):
        self.logger = logger

    def decoding_datetime(self, dt_str: str) -> pd.Timestamp:
        return pd.to_datetime(
            dt_str
        )
    
    def decode_time(self, t_str: str | None) -> time | None:
        return pd.to_datetime(
            t_str,
            format = "%H:%M"
        ).time() if t_str else None
    
    def decode_date(self, date_str: str | None) -> date | None:
        return pd.to_datetime(
            date_str
        ).date() if date_str else None

class _bus_parsers(_parsers):
    def __init__(self, logger: Logger):
        super().__init__(logger)
    
    def __parse_direction(self, direction: int) -> str | None:
        from .bus_models import Direction
        try: return Direction(direction).name
        except Exception:
            return None
    
    def parse_routes(self, routes: list[Route]) -> pd.DataFrame:
        """
        """
        data = []
        for r in routes:
            operators = pd.DataFrame([{
                "OperatorID": op.OperatorID,
                **op.OperatorName.flat("OperatorName")
            } for op in r.Operators])
            route_base = {
                "RouteUID": r.RouteUID,
                **r.RouteName.flat("RouteName"),
                "BusRouteType": r.BusRouteType,
                "Operators": operators,
                "UpdateTime": self.decoding_datetime(r.UpdateTime),
                "RouteDepartureZh": r.DepartureStopNameZh,
                "RouteDepartureEn": r.DepartureStopNameEn,
                "RouteDestinationZh": r.DestinationStopNameZh,
                "RouteDestinationEn": r.DestinationStopNameEn,
            }
            if not r.SubRoutes:
                data.append(route_base)
                continue
            for sub in r.SubRoutes:
                row = {
                    **route_base,
                    "SubRouteUID": sub.SubRouteUID,
                    **sub.SubRouteName.flat("SubRouteName"),
                    "Direction": self.__parse_direction(sub.Direction),
                    "Headsign": sub.Headsign,
                    "SubDepartureZh": sub.DepartureStopNameZh,
                    "SubDepartureEn": sub.DepartureStopNameEn,
                    "SubDestinationZh": sub.DestinationStopNameZh,
                    "SubDestinationEn": sub.DestinationStopNameEn
                }
                data.append(row)
        return pd.DataFrame(data)
    
    def parse_route_with_shape(self, routes: list[RouteShape]) -> pd.DataFrame:
        """
        """
        def decode_geometry(geom_str: str | None) -> shapely.geometry.base.BaseGeometry | None:
            try:
                return shapely.wkt.loads(geom_str) # type: ignore
            except Exception as e:
                self.logger.warning(f"Failed to parse geometry: {e}")
                return None
        data = []
        for r in routes:
            data.append({
                "RouteUID": r.RouteUID,
                "SubRouteUID": r.SubRouteUID,
                **r.RouteName.flat("RouteName"),
                "Direction": self.__parse_direction(r.Direction),
                "UpdateTime": self.decoding_datetime(r.UpdateTime),
                "geometry": decode_geometry(r.Geometry)
            })
        return pd.DataFrame(data)
    
    def parse_stations(self, route_stops: list[RouteStops]) -> pd.DataFrame:
        """
        """
        data = []
        for route in route_stops:
            for s in route.Stops:
                data.append({
                    "StationID": s.StationID,
                    "StationGroupID": s.StationGroupID,
                    "StopUID": s.StopUID,
                    **s.StopName.flat("StopName"),
                    "RouteUID": route.RouteUID,
                    **route.RouteName.flat("RouteName"),
                    "SubRouteUID": route.SubRouteUID,
                    **route.SubRouteName.flat("SubRouteName"),
                    "Direction": self.__parse_direction(route.Direction),
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
    
    def parse_operators(self, operators: list[Operator]) -> pd.DataFrame:
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
    
    def parse_alerts(self,alerts: list[Alert]) -> pd.DataFrame:
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
                base["UpdateTime"] = self.decoding_datetime(a.UpdateTime)
                scope: pd.DataFrame = pd.json_normalize(
                    s, record_path = list(s.keys()), sep = ""
                    )
                for _, row in scope.iterrows():
                    base_copy = base.copy()
                    for key, value in row.items():
                        base_copy[key] = value
                    data.append(base_copy)

        return pd.concat(data, axis=0, ignore_index=True)
    
    def __flat_route_info(self, schedule: Schedule | DailySchedule) -> dict:
        return {
            "RouteUID": schedule.RouteUID,
            "SubRouteUID": schedule.SubRouteUID,
            "Direction": self.__parse_direction(schedule.Direction),
            "OperatorID": schedule.OperatorID,
            "UpdateTime": self.decoding_datetime(schedule.UpdateTime)
        }
    
    def __parse_timtable(self, schedule: Schedule | DailySchedule, only_departure_station: bool = False) -> list:
        from .bus_models import Timetable
        data = []
        route_base = self.__flat_route_info(schedule)
        for trip in schedule.Timetables:
            trip_base: dict = {
                "TripID": trip.TripID
            }
            if isinstance(trip, Timetable):
                trip_base["IsLowFloor"] = trip.IsLowFloor
                for stop in trip.StopTimes:
                    if stop.StopSequence != 1 and only_departure_station:
                        break
                    for day in trip.ServiceDay.service_days:
                        row = {
                            **route_base,
                            **trip_base,
                            "StopSequence": stop.StopSequence,
                            "ServiceDay": day,
                            **stop.StopName.flat("StopName"),
                            "ArrivalTime": self.decode_time(stop.ArrivalTime),
                            "DepartureTime": self.decode_time(stop.DepartureTime)
                        }
                        data.append(row)
            else:
                for stop in trip.StopTimes:
                    if stop.StopSequence != 1 and only_departure_station:
                        break
                    row = {
                        **route_base,
                        **trip_base,
                        "StopSequence": stop.StopSequence,
                        "ServiceDate": self.decode_date(schedule.BusDate),
                        **stop.StopName.flat("StopName"),
                        "ArrivalTime": self.decode_time(stop.ArrivalTime),
                        "DepartureTime": self.decode_time(stop.DepartureTime),
                        "IsEstimatedTime": stop.is_estimated_time
                    }
                    data.append(row)
                    if only_departure_station:
                        break
        return data
    
    def __parse_frequency(self, schedule: Schedule) -> list:
        data = []
        route_base = self.__flat_route_info(schedule)
        for period in schedule.Frequencys:
            for day in period.ServiceDay.service_days:
                row = {
                    **route_base,
                    "ServiceDay": day,
                    "StartTime": self.decode_time(period.StartTime),
                    "EndTime": self.decode_time(period.EndTime),
                    "MinHeadwayMins": period.MinHeadwayMins,
                    "MaxHeadwayMins": period.MaxHeadwayMins
                }
                data.append(row)
        return data
    
    def parse_schedules_for_departures(self, schedules: list[Schedule | DailySchedule]) -> pd.DataFrame:
        """
        """
        data = []
        for s in schedules:
            if len(s.Timetables) > 0:
                data.extend(self.__parse_timtable(s, only_departure_station=True))
            if isinstance(s, Schedule) and len(s.Frequencys) > 0:
                data.extend(self.__parse_frequency(s))
        return pd.DataFrame(data)

    def parse_schedules(self, schedules: list[Schedule | DailySchedule]) -> pd.DataFrame:
        """
        """
        from .bus_models import Timetable
        data = []
        for s in schedules:
            if len(s.Timetables) > 0:
                data.extend(self.__parse_timtable(s))
            if isinstance(s, Schedule) and len(s.Frequencys) > 0:
                data.extend(self.__parse_frequency(s))
        return pd.DataFrame(data)
    
class _bike_parsers(_parsers):
    def __init__(self, logger: Logger):
        super().__init__(logger)
    
    def parse_stations(self, stations: list[Station]) -> pd.DataFrame:
        """
        """
        data = []
        for s in stations:
            data.append({
                "StationUID": s.StationUID,
                **s.StationName.flat("StationName"),
                "StationPosition": s.StationPosition,
                **s.StationAddress.flat("StationAddress"),
                "StopDescription": s.StopDescription,
                "BikesCapacity": s.BikesCapacity,
                "ServiceType": s.ServiceType,
                "UpdateTime": self.decoding_datetime(s.UpdateTime),
                **s.StationPosition.flat_without_prefix
            })
        return pd.DataFrame(data)
    
    def parse_availability(self, availability: list[Availability]) -> pd.DataFrame:
        """
        """
        data = []
        for a in availability:
            base = {
                "StationUID": a.StationUID,
                "ServiceStatus": a.ServiceStatus,
                "AvailableRentBikes": a.AvailableRentBikes,
                "AvailableReturnBikes": a.AvailableReturnBikes,
                "UpdateTime": self.decoding_datetime(a.UpdateTime)
            }
            if a.AvailableRentBikesDetail is not None:
                base["AvailableGeneralBikes"] = a.AvailableRentBikesDetail.GeneralBikes
                base["AvailableElectricBikes"] = a.AvailableRentBikesDetail.ElectricBikes
            data.append(base)
        return pd.DataFrame(data)

class _rail_parsers(_parsers):
    def __init__(self, logger: Logger):
        super().__init__(logger)
        