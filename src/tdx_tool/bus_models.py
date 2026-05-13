# Dependencies
from enum import IntEnum
from typing import List, Optional
import msgspec as ms
# Local imports
from .common_models import I18n, PointPosition

class Direction(IntEnum):
    Forward  = 0    # 往程
    Backward = 1    # 返程
    Loop     = 2    # 循環
    Circular = 10   # 環狀
    Unknown  = 255  # 未知

class BusRouteType(IntEnum):
    LocalCity  = 1  # 市區公車
    InterCity  = 12 # 公路客運
    Highway    = 13 # 國道客運
    Shuttle    = 14 # 接駁車

class ServiceStatus(IntEnum):
    Cancel = 0   # 全部營運停駛
    Normal = 1   # 全部營運正常
    Errors = 2   # 有異常狀況

class ErrorCause(IntEnum):
    Accident = 1 # 事故
    Maintain = 2 # 維修
    Technical = 3 # 技術問題
    Construction = 4 # 施工
    MedicalEmergency = 5 # 醫療緊急狀況
    Weather = 6 # 氣候
    Demonstration = 7 # 示威遊行
    PoliceActivity = 8 # 政治活動/維安
    Holiday = 9 # 假日/節慶
    Strike = 10 # 罷工
    Activity = 11 # 活動(如：國慶活動/煙火活動/跨年活動/路跑活動/新北耶誕城活動等)
    OtherCause = 254 # 其他
    UnknownCause = 255 # 未知原因

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

class Trip(ms.Struct, kw_only=True):
    TripID: str
    RouteUID: str
    SubRouteUID: str
    Direction: int
    TripDepTime: str

class Stop(ms.Struct, kw_only=True):
    StopUID: str
    StopName: I18n
    StopBoarding: int
    StopSequence: int
    StopPosition: PointPosition
    StationID: str
    StationGroupID: Optional[str] = None

class Station(ms.Struct, kw_only=True):
    StationUID: str
    StationPosition: PointPosition
    StationName: Optional[I18n] = None
    StationAddress: Optional[str] = None
    StationGroupID: Optional[str] = None
    Stops: List[Stop] = [] # type: ignore
    LocationCityCode: Optional[str] = None
    Bearing: Optional[str] = None
    UpdateTime: Optional[str] = None

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

class Alert(ms.Struct, kw_only=True):
    AlertID: str
    Title: str
    Description: str
    Department: str
    Status: int
    Cause: Optional[int] = None
    Effect: Optional[int] = None
    Scope: Optional[dict[str, object]] = None
    PublishTime: Optional[str] = None
    StartTime: Optional[str] = None
    EndTime: Optional[str] = None
    SrcUpdateTime: str
    UpdateTime: str
        
class Period(ms.Struct, kw_only=True):
    StartDate: str
    EndDate: str

class SpecialDay(ms.Struct, kw_only=True):
    Dates: List[str]
    DatePeriod: Optional[Period] = None
    ServiceStatus: int
    Description: Optional[str] = None

class ServiceDay(ms.Struct, kw_only=True):
    ServiceTag: Optional[str] = None
    Monday: int
    Tuesday: int
    Wednesday: int
    Thursday: int
    Friday: int
    Saturday: int
    Sunday: int
    NationalHolidays: int

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