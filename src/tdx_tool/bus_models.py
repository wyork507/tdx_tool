from typing import Optional
from msgspec import Struct

class Operator(Struct):
    OperatorID: str
    OperatorName: I18n

class SubRoute(Struct):
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
        
class Route(Struct):
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

class Trips(Struct):
    TripID: str
    RouteUID: str
    SubRouteUID: str
    Direction: int
    TripDepTime: str

class PointPosition(Struct):
    PositionLon: float
    PositionLat: float
    GeoHash: str

class Stop(Struct):
    StopUID: str
    StopName: I18n
    StopBoarding: int
    StopSequence: int
    StopPosition: PointPosition # type: ignore
    RouteUID: str
    RouteName: I18n
    StationID: str
    StationGroupID: str

class Station(Struct):
    StationUID: str
    StationName: Optional[I18n] = None
    StationPosition: PointPosition # type: ignore
    StationAddress: Optional[str] = None
    StationGroupID: Optional[str] = None
    Stops: list[Stop] # type: ignore
    LocationCityCode: Optional[str] = None
    Bearing: Optional[str] = None
    UpdateTime: Optional[str] = None

class RouteStops(Struct):
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

class RouteShape(Struct):
    RouteUID: str
    SubRouteUID: str
    RouteName: I18n
    Direction: int
    Geometry: Optional[str] = None
    EncodedPolyline: str
    UpdateTime: Optional[str] = None

class Scope(Struct):
    Operators: list[Operator] = []
    Stops: list[Stop] = []
    Stations: list[Station] = []
    Routes: list[Route] = []
    SubRoutes: list[SubRoute] = []
    Trips: list[Trips] = []

class Alert(Struct):
    AlertID: str
    Title: str
    Description: str
    Department: str
    Status: int
    Cause: int
    Effect: int
    Scope: Scope
    AlertURL: str
    PublishTime: str
    StartTime: str
    EndTime: str
    SrcUpdateTime: str
    UpdateTime: str

class Period(Struct):
    StartDate: str
    EndDate: str

class SpecialDay(Struct):
    Dates: list[str]
    DatePeriod: Period
    ServiceStatus: int
    Description: str 

class ServiceDay(Struct):
    Monday: int
    Tuesday: int
    Wednesday: int
    Thursday: int
    Friday: int
    Saturday: int
    Sunday: int
    NationalHolidays: int
    ServiceTag: Optional[str] = None

    @property
    def regular(self) -> list[bool]:
        return [
            self.Monday == 1,
            self.Tuesday == 1,
            self.Wednesday == 1,
            self.Thursday == 1,
            self.Friday == 1,
            self.Saturday == 1,
            self.Sunday == 1
        ]
    
    @property
    def holidays(self) -> bool:
        return self.NationalHolidays == 1

class Frequency(Struct):
    StartTime: str
    EndTime: str
    MinHeadwayMins: int
    MaxHeadwayMins: int
    ServiceDay: ServiceDay
    SpecialDays: list[SpecialDay] = []

class StopTime(Struct):
    StopUID: str
    StopSequence: int
    StopName: I18n
    ArrivalTime: Optional[str] = None
    DepartureTime: Optional[str] = None

class Timetable(Struct):
    TripID: str
    IsLowFloor: bool
    ServiceDay: ServiceDay
    SpecialDays: list[SpecialDay] = []
    StopTimes: list[StopTime] = []

class Schedule(Struct):
    RouteUID: str
    RouteName: I18n
    SubRouteUID: str
    SubRouteName: I18n
    Direction: int
    OperatorID: str
    Timetable: list[Timetable] = []
    Frequency: list[Frequency] = []
    UpdateTime: Optional[str] = None
    