# Dependencies
from logging import Logger
import pandas as pd
import geopandas as gpd
import shapely
# Local imports
from .common_parsers import _parsers, with_tqdm
from .bus_models import DailySchedule, Route, RouteShape, RouteStops, Alert, Schedule, Operator, StationFraction, Station


class _bus_parsers(_parsers):
    def __init__(self, logger: Logger):
        super().__init__(logger)
    
    def __parse_direction(self, direction: int) -> str | None:
        from .bus_models import Direction
        try: return Direction(direction).name
        except Exception: return None
    
    # MARK: Routes Parsers
    @with_tqdm(arg_names=["routes"], desc="Parsing routes", unit="route")
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
    
    @with_tqdm(arg_names=["routes"], desc="Parsing routes with shapes", unit="route")
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
    
    # MARK: Stations Parsers
    @with_tqdm(arg_names=["route_stops", "station_fractions"], desc="Parsing stations", unit="station")
    def parse_stations(self, route_stops: list[RouteStops], station_fractions: list[StationFraction]) -> dict[str, Station]:
        """
        """
        from threading import Lock
        from .bus_models import Stop, StationFraction

        stops: dict[str, list[Stop]] = {}
        for route in route_stops:
            for s in route.Stops:
                geohash: str = s.StopPosition.GeoHash
                if geohash not in stops:
                    stops.setdefault(geohash, [])
                stops[geohash] += [s]
        
        data: dict[str, Station] = {}
        hash_map: dict[str, set[str]] = {} # geohash -> StationUID
        for station in station_fractions:
            geohash = station.StationPosition.GeoHash
            if geohash not in stops:
                stops.setdefault(geohash, [])
            if geohash not in hash_map:
                hash_map.setdefault(geohash, set())
                data[station.StationUID] = Station.from_fraction(
                    station,
                    stops[geohash]
                )
            else:
                hash_map[geohash].add(station.StationUID)
                self.logger.debug(f"Station {station.StationUID} shares geohash {geohash} with station(s) {hash_map[geohash]}")
                data[station.StationUID].StationUID = list(hash_map[geohash])
        return data
    
    @with_tqdm(arg_names=["route_stops"], desc="Parsing stations to DataFrame", unit="station")
    def parse_stations_to_dataframe(self, route_stops: list[RouteStops]) -> pd.DataFrame:
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
    
    # MARK: Operators Parsers
    @with_tqdm(arg_names=["operators"], desc="Parsing operators", unit="operator")
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
    
    # MARK: Alerts Parsers
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
    
    # MARK: Schedules Parsers
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
                        "ServiceDate": self.decode_date(schedule.BusDate), # type: ignore
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

    def parse_schedules(self, schedules: list[Schedule] | list[DailySchedule]) -> pd.DataFrame:
        """
        """
        data = []
        for s in schedules:
            if len(s.Timetables) > 0:
                data.extend(self.__parse_timtable(s))
            if isinstance(s, Schedule) and len(s.Frequencys) > 0:
                data.extend(self.__parse_frequency(s))
        return pd.DataFrame(data)
