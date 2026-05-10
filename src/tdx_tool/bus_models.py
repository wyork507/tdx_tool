# Dependencies
import msgspec as ms
from typing import List, Optional

class I18n(ms.Struct, kw_only=True):
    Zh_tw: str
    En: str = None

class Operator(ms.Struct, kw_only=True):
    OperatorID: str
    OperatorName: I18n

class SubRoute(ms.Struct, kw_only=True):
    SubRouteUID: str
    SubRouteID: str
    Direction: int
    SubRouteName: I18n
    OperatorIDs: List[str] = []
    Headsign: Optional[str] = None
    HeadsignEn: Optional[str] = None
    DepartureStopNameZh: Optional[str] = None
    DepartureStopNameEn: Optional[str] = None
    DestinationStopNameZh: Optional[str] = None
    DestinationStopNameEn: Optional[str] = None
        
class Route(ms.Struct, kw_only=True):
    RouteUID: str
    BusRouteType: int
    RouteName: I18n
    Operators: List[Operator]
    DepartureStopNameZh: Optional[str] = None
    DepartureStopNameEn: Optional[str] = None
    DestinationStopNameZh: Optional[str] = None
    DestinationStopNameEn: Optional[str] = None
    SubRoutes: List[SubRoute] = []
    UpdateTime: Optional[str] = None

class Trips(ms.Struct, kw_only=True):
    TripID: str
    RouteUID: str
    SubRouteUID: str
    Direction: int
    TripDepTime: str

class PointPosition(ms.Struct, kw_only=True):
    PositionLon: float
    PositionLat: float
    GeoHash: str

class Stop(ms.Struct, kw_only=True):
    StopUID: str
    StopName: I18n
    StopBoarding: int
    StopSequence: int
    StopPosition: PointPosition
    StationID: str
    StationGroupID: str

class StopDetail(Stop):
    RouteUID: str
    RouteName: I18n

class Station(ms.Struct, kw_only=True):
    StationUID: str
    StationPosition: PointPosition
    StationName: I18n = None
    StationAddress: str = None
    StationGroupID: str = None
    Stops: List[Stop] = [] # type: ignore
    LocationCityCode: str = None
    Bearing: str = None
    UpdateTime: str = None

class RouteStops(ms.Struct, kw_only=True):
    RouteUID: str
    RouteName: I18n
    Operators: List[Operator] = [] # type: ignore
    SubRouteUID: str
    SubRouteName: I18n
    Direction: int
    City: str
    CityCode: str
    Stops: List[Stop] = [] # type: ignore
    UpdateTime: Optional[str] = None

class RouteShape(ms.Struct, kw_only=True):
    RouteUID: str
    SubRouteUID: str
    RouteName: I18n
    Direction: int
    EncodedPolyline: str
    Geometry: Optional[str] = None
    UpdateTime: Optional[str] = None

class Scope(ms.Struct, kw_only=True):
    Operators: List[Operator] = []
    Stops: List[Stop] = []
    Stations: List[Station] = []
    Routes: List[Route] = []
    SubRoutes: List[SubRoute] = []
    Trips: List[Trips] = []

class Alert(ms.Struct, kw_only=True):
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

class Period(ms.Struct, kw_only=True):
    StartDate: str
    EndDate: str

class SpecialDay(ms.Struct, kw_only=True):
    Dates: List[str]
    DatePeriod: Period
    ServiceStatus: int
    Description: Optional[str] = None

class ServiceDay(ms.Struct, kw_only=True):
    Monday: int
    Tuesday: int
    Wednesday: int
    Thursday: int
    Friday: int
    Saturday: int
    Sunday: int
    NationalHolidays: int
    ServiceTag: Optional[str] = None

class Frequency(ms.Struct, kw_only=True):
    StartTime: str
    EndTime: str
    MinHeadwayMins: int
    MaxHeadwayMins: int
    ServiceDay: ServiceDay
    SpecialDays: List[SpecialDay] = []

class StopTime(ms.Struct, kw_only=True):
    StopUID: str
    StopSequence: int
    StopName: I18n
    ArrivalTime: Optional[str] = None
    DepartureTime: Optional[str] = None

class Timetable(ms.Struct, kw_only=True):
    TripID: str
    IsLowFloor: bool
    ServiceDay: ServiceDay
    SpecialDays: List[SpecialDay] = []
    StopTimes: List[StopTime] = []

class Schedule(ms.Struct, kw_only=True):
    RouteUID: str
    RouteName: I18n
    SubRouteUID: str
    SubRouteName: I18n
    Direction: int
    OperatorID: str
    Timetables: List[Timetable] = []
    Frequencys: List[Frequency] = []
    UpdateTime: Optional[str] = None
