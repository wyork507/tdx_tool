# Dependencies
from collections import defaultdict
from logging import Logger
from typing import Literal
import pandas as pd
import geopandas as gpd
from shapely import LineString
import polyline
# Local imports
from .common_parsers import _parsers, with_tqdm
from .bus_models import (
    Route, RouteShape,
    Station, StationFraction,
    RouteStops, Stop,
    Operator,
    Alert,
    DailySchedule, Schedule
)


class _bus_parsers(_parsers):
    def __init__(self, logger: Logger):
        super().__init__(logger)
    
    def __decode_direction(self, direction: int) -> str | None:
        from .bus_models import Direction
        try: return Direction(direction).name
        except Exception: return None
    
    def __decode_route_type(self, route_type: int) -> str | None:
        from .bus_models import BusRouteType as RouteType
        try: return RouteType(route_type).name
        except Exception: return None
    
    def __decode_bearing(self, bearing: str) -> str | None:
        from .bus_models import Bearing
        try: return Bearing(bearing).name
        except Exception: return None
    
    def __decode_status(self, status: int, source: Literal["Alert", "ServiceStatus"]) -> str | None:
        from .bus_models import ServiceStatus
        status_case: ServiceStatus | None
        match source:
            case "Alert":
                status_case = ServiceStatus.from_alert(status)
            case "ServiceStatus":
                status_case = ServiceStatus.from_timetable(status)
            case _:
                return None
        if status_case is None:
            return None
        else:
            return status_case.value
    
    def __decode_error_cause(self, error_cause: int) -> str | None:
        from .bus_models import ServiceStatus
        try: return ServiceStatus(error_cause).name
        except Exception: return None
    
    def __stract_operators(self, operators: list[Operator]) -> list[str]:
        return [operator.OperatorID for operator in operators]
    

    
    # ====================
    # MARK: Routes Parsers
    # ====================
    @with_tqdm(arg_names=["routes"], desc="Parsing routes", unit="route")
    def parse_routes(self, routes: list[Route]) -> pd.DataFrame:
        data = []
        for route in routes:
            base = self.flat_struct(route,
                skip_fields=["SubRoutes"],
                rename_fields={"Operators": "RouteOperatorIDs"},
                convertors={"Operators": self.__stract_operators}
            )
            if len(route.SubRoutes) == 0:
                data.append({
                    **base,
                    "SubRouteUID": route.RouteUID
                })
            else:
                for subroute in route.SubRoutes:
                    data.append({
                        **base,
                        **self.flat_struct(subroute,
                            rename_fields={"OperatorIDs": "SubRouteOperatorIDs"},
                            convertors={
                                "Direction": self.__decode_direction,
                                "OperatorIDs": self.__stract_operators
                            }
                        )
                    })
        return pd.DataFrame(
            data
        ).sort_values(by=["RouteNameEn", "SubRouteUID"]
        ).reset_index(drop=True)
    
    # ====================
    # MARK: Shapes Parsers
    # ====================
    def __decode_polyline(self, p_str: str) -> LineString:
        return LineString([(lon, lat) for lat, lon in polyline.decode(p_str)])
    
    @with_tqdm(arg_names=["route_shapes"], desc="Parsing route shapes", unit="route")
    def __parse_route_shape(self, routes: list[RouteShape]) -> list[dict]:
        return [{
        "SubRouteUID": route.SubRouteUID if route.SubRouteUID is not None else route.RouteUID,
        **self.flat_struct(route,
            skip_fields=["SubRouteUID"],
            rename_fields={"EncodedPolyline": "geometry"},
            convertors={
                "Direction": self.__decode_direction,
                "EncodedPolyline": self.__decode_polyline
            })
        } for route in routes]
    
    def parse_shapes_to_df(self, routes: list[RouteShape]) -> pd.DataFrame:
        return pd.DataFrame(
            self.__parse_route_shape(routes)
        ).sort_values(by=["RouteNameEn", "SubRouteUID"]
        ).reset_index(drop=True)
    
    def parse_shapes_to_gdf(self, routes: list[RouteShape]) -> gpd.GeoDataFrame:
        return gpd.GeoDataFrame(
            self.__parse_route_shape(routes),
            crs="EPSG:4326" # WGS 84
        ).sort_values(by=["RouteNameEn", "SubRouteUID"]
        ).reset_index(drop=True)
    
    # ===================
    # MARK: Stops Parsers
    # ===================
    @with_tqdm(arg_names=["route_stops"], desc="Parsing stops", unit="stop")
    def parse_stops(self, route_stops: list[RouteStops], coordinate: str) -> gpd.GeoDataFrame:
        """
        """
        data = []
        for route in route_stops:
            base = self.flat_struct(route, skip_fields=["Stops"])
            for stop in route.Stops:
                data.append({
                    **base,
                    **self.flat_struct(stop)
                })
        return gpd.GeoDataFrame(data, crs=coordinate)
    
    # TODO: This is so hard to complete, later to do
    @with_tqdm(arg_names=["route_stops"], desc="Parsing stops", unit="route")
    def stops_joined_shape(self, route_stops: list[RouteStops], route_shapes: list[RouteShape], coordinate: str) -> gpd.GeoDataFrame | None:
        """
        """
        pass

    # ======================
    # MARK: Stations Parsers
    # ======================
    @with_tqdm(arg_names=["route_stops"], desc="Extracting station from routes", unit="route")
    def __extract_stations(self, route_stops: list[RouteStops]) -> dict[str, list[Stop]]:
        """
        Returns
        -------
        dict[str, list[Stop]]
            StationID -> list of Station object
        """
        stations: dict[str, list[Stop]] = defaultdict(list)
        for route in route_stops:
            for stop in route.Stops:
                stations[stop.StationID].append(stop)
        return stations

    @with_tqdm(arg_names=["station_info"], desc="Extracting station info...", unit="stations")
    def __extract_station_info(self, station_info: list[StationFraction]) -> dict[str, list[StationFraction]]:
        """
        Returns
        -------
        dict[str, list[StationFraction]]
            StationID -> list of StationFraction objects
        """
        station_info_map: dict[str, list[StationFraction]] = defaultdict(list)
        for station in station_info:
            station_info_map[station.StationID].append(station)
        return station_info_map

    def parse_stations(self, route_stops: list[RouteStops], station_fractions: list[StationFraction]) -> dict[str, list[Station]]:
        """
        """
        data: dict[str, list[Station]] = defaultdict(list)
        stations = self.__extract_stations(route_stops)
        for station_id, station_info in self.__extract_station_info(station_fractions).items():
            data[station_id].append(Station.from_fraction(station_info, stations[station_id]))
        return data
    
    @with_tqdm(arg_names=["route_stops"], desc="Parsing stations to DataFrame", unit="station")
    def parse_stations_to_df(self, route_stops: list[RouteStops]) -> pd.DataFrame:
        """
        """
        data = []
        for route in route_stops:
            base = self.flat_struct(route, skip_fields=["Stops"])
            for stop in route.Stops:
                data.append({
                    **base,
                    "Direction": self.__parse_direction(route.Direction),
                    "OperatorIDs": ",".join([op.OperatorID for op in route.Operators]),
                    **self.flat_struct(stop, skip_fields=["Direction", "OperatorIDs"])    
                })
        return pd.DataFrame(data)
    
    # =======================
    # MARK: Operators Parsers
    # =======================

    @with_tqdm(arg_names=["operators"], desc="Parsing operators", unit="operator")
    def parse_operators(self, operators: list[Operator]) -> pd.DataFrame:
        """
        """
        data = []
        for operator in operators:
            data.append(self.flat_struct(operator))
        return pd.DataFrame(data)
    
    # ====================
    # MARK: Alerts Parsers
    # ====================

    @with_tqdm(arg_names=["alerts"], desc="Parsing alerts", unit="alert")
    def parse_alerts(self, alerts: list[Alert]) -> pd.DataFrame:
        data: list[dict] = []
        for alert in alerts:
            base = self.flat_struct(alert, skip_fields=["Scope"])
            # Keep backward-compatible column naming.

            scope = alert.Scope
            if alert.Status == 1 or not scope:
                data.append(base)
                continue

            scope_df = pd.json_normalize(scope, record_path=list(scope.keys()), sep="")
            if scope_df.empty:
                data.append(base)
                continue
            for row in scope_df.to_dict(orient="records"):
                data.append({**base, **row})
                
        return pd.DataFrame(data)
    
    # =======================
    # MARK: Schedules Parsers
    # =======================
    
    def __flat_route_info(self, schedule: Schedule | DailySchedule) -> dict:
        return {
            **self.flat_struct(schedule, skip_fields=["Timetables", "Frequencys", "Direction"]),
            "Direction": self.__parse_direction(schedule.Direction)
        }

    def __parse_timtable(self, schedule: Schedule | DailySchedule, only_departure_station: bool = False) -> list:
        from .bus_models import DailyTimetable
        data = []
        route_base = self.__flat_route_info(schedule)
        for trip in schedule.Timetables:
            trip_base = self.flat_struct(trip, skip_fields=["StopTimes", "ServiceDay", "SpecialDays"])
            for stop in trip.StopTimes:
                if stop.StopSequence != 1 and only_departure_station:
                    break
                stop_base = {
                    **route_base,
                    **trip_base,
                    **self.flat_struct(stop, time_fields=["ArrivalTime", "DepartureTime"], skip_fields=["TimeType"])
                }
                if isinstance(trip, DailyTimetable):
                    data.append({
                        "IsEstimatedTime": stop.is_estimated_time, # type: ignore[union-attr]
                        **stop_base
                    })
                for day in trip.ServiceDay.service_days: # type: ignore[union-attr]
                    data.append({
                        "ServiceDay": day,
                        **stop_base
                    })
        return data
    
    def __parse_frequency(self, schedule: Schedule) -> list:
        data = []
        route_base = self.__flat_route_info(schedule)
        for period in schedule.Frequencys:
            period_base = self.flat_struct(period, time_fields=["StartTime", "EndTime"], skip_fields=["ServiceDay"])
            for day in period.ServiceDay.service_days:
                data.append({
                    **route_base,
                    **period_base,
                    "ServiceDay": day,
                })
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
