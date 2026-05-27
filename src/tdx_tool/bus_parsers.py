# Dependencies
from logging import Logger
import pandas as pd
import geopandas as gpd
from shapely import LineString
import polyline
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
    
    # ====================
    # MARK: Routes Parsers
    # ====================

    @with_tqdm(arg_names=["routes"], desc="Parsing routes", unit="route")
    def parse_routes(self, routes: list[Route]) -> pd.DataFrame:
        data = []
        for route in routes:
            base = self.flat_struct(route,
                skip_fields=["Operators", "SubRoutes"]
            )
            base["Operators"] = pd.DataFrame([
                self.flat_struct(operator) for operator in route.Operators
            ])
            if not route.SubRoutes:
                data.append(base)
            else:
                for subroute in route.SubRoutes:
                    data.append({
                        **base,
                        **self.flat_struct(subroute)
                    })
        return pd.DataFrame(data)
    
    # ====================
    # MARK: Shapes Parsers
    # ====================

    @with_tqdm(arg_names=["routes"], desc="Parsing routes with shapes", unit="route")
    def parse_route_with_shape(self, routes: list[RouteShape], coordinate: str) -> gpd.GeoDataFrame:
        """
        """
        def decode_line(p_str: str) -> LineString:
            return LineString([(lon, lat) for lat, lon in polyline.decode(p_str)])
        
        data = []
        for route in routes:
            data.append({
                **self.flat_struct(route, skip_fields=["EncodedPolyline"]),
                "geometry": decode_line(route.EncodedPolyline)
            })
        return gpd.GeoDataFrame(data, crs=coordinate)
    
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
                data.append({**base, **self.flat_struct(stop)})
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

    @with_tqdm(arg_names=["route_stops", "station_fractions"], desc="Parsing stations", unit="station")
    def parse_stations(self, route_stops: list[RouteStops], station_fractions: list[StationFraction]) -> dict[str, Station]:
        """
        """
        # XXX: oh my god, this is so hard to complete, later to do
        from .bus_models import Stop
        stops: dict[str, list[Stop]] = {}
        for route in route_stops:
            for s in route.Stops:
                geohash: str = s.StopPosition.GeoHash
                if geohash not in stops:
                    stops.setdefault(geohash, [])
                stops[geohash] += [s]
        
        data: dict[str, Station] = {}

        # FIXME: By inspecting, the geohash for a station is not unique, due to the different precision of original coor.
        # which means the logic of grouping station need to adjust to avoid the case that multiple stations share the same
        # geohash, but they are not the same station.
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
