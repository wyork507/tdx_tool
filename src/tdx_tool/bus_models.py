# Dependencies
from dataclasses import dataclass, field
from enum import IntEnum, StrEnum
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

class Bearing(StrEnum):
    Eastward  = "E"
    Westward  = "W"
    Southward = "S"
    Northward = "N"
    Southeast = "SE"
    Northeast = "NE"
    Southwest = "SW"
    Northwest = "NW"


class ServiceStatus(StrEnum):
    Cancel = "停駛"
    Normal = "正常"
    Errors = "異常"
    Addion = "加班"

    @classmethod
    def from_alert(cls, alert_status: int) -> Optional["ServiceStatus"]:
        for status in cls:
            if status.alert_status == alert_status:
                return status
        return None
    
    @classmethod
    def from_timetable(cls, timetable_status: int) -> Optional["ServiceStatus"]:
        for status in cls:
            if status.timetable_status == timetable_status:
                return status
        return None
    
    @property
    def description(self) -> str:
        return self.value

    @property
    def alert_status(self) -> Optional[int]:
        match self:
            case ServiceStatus.Cancel:
                return 0
            case ServiceStatus.Normal:
                return 1
            case ServiceStatus.Errors:
                return 2
            case _:
                return None
    
    @property
    def timetable_status(self) -> Optional[int]:
        match self:
            case ServiceStatus.Normal:
                return 0
            case ServiceStatus.Addion:
                return 1
            case ServiceStatus.Cancel:
                return 2
            case _:
                return None

class ErrorCause(IntEnum):
    Accident        = 1 # 事故
    Maintain        = 2 # 維修
    Technical       = 3 # 技術問題
    Construction    = 4 # 施工
    MedicalEmergency = 5 # 醫療緊急狀況
    Weather         = 6 # 氣候
    Demonstration   = 7 # 示威遊行
    PoliceActivity  = 8 # 政治活動/維安
    Holiday         = 9 # 假日/節慶
    Strike          = 10 # 罷工
    Activity        = 11 # 活動(如：國慶活動/煙火活動/跨年活動/路跑活動/新北耶誕城活動等)
    OtherCause      = 254 # 其他
    UnknownCause    = 255 # 未知原因

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
    UpdateTime: str

class Stop(ms.Struct, kw_only=True):
    StopUID: str
    StopName: I18n
    StopBoarding: int
    StopSequence: int
    StopPosition: PointPosition
    StationID: str
    StationGroupID: Optional[str] = None

@dataclass(kw_only=True, slots=True)
class Station:
    StationUID: List[str]
    StationID: str
    StationPosition: PointPosition
    StationName: I18n
    StationAddress: Optional[str] = None
    StationGroupID: Optional[str] = None
    Stops: List[Stop] = field(default_factory=list)
    LocationCityCode: Optional[str] = None
    Bearing: Optional[str] = None
    UpdateTime: str

    @classmethod
    def from_fraction(cls, station: List["StationFraction"], stops: List[Stop]) -> "Station":
        return cls(
            StationUID=[s.StationUID for s in station],
            StationID=station[0].StationID,
            StationPosition=station[0].StationPosition,
            StationName=stops[0].StopName,
            StationAddress=station[0].StationAddress,
            StationGroupID=stops[0].StationGroupID,
            Stops=stops,
            LocationCityCode=station[0].LocationCityCode,
            Bearing=station[0].Bearing,
            UpdateTime=station[0].UpdateTime
        )

class StationFraction(ms.Struct, kw_only=True):
    StationUID: str
    StationID: str
    StationName: I18n
    StationPosition: PointPosition
    StationAddress: Optional[str] = None
    LocationCityCode: Optional[str] = None
    Bearing: Optional[str] = None
    UpdateTime: str
    

class RouteStops(ms.Struct, kw_only=True):
    RouteUID: str
    RouteName: I18n
    Operators: List[Operator] = []
    SubRouteUID: str
    SubRouteName: I18n
    Direction: int
    City: str
    CityCode: str
    Stops: List[Stop] = []
    UpdateTime: str

class RouteShape(ms.Struct, kw_only=True):
    RouteUID: str
    SubRouteUID: Optional[str] = None
    RouteName: I18n
    Direction: int
    EncodedPolyline: str
    UpdateTime: str

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

@dataclass(kw_only=True, slots=True)
class SpecialDay:
    Dates: List[str]
    DatePeriod: Optional[Period] = None
    ServiceStatus: int
    Description: Optional[str] = None

    @property
    def status(self) -> "ServiceStatus":
        return ServiceStatus.from_timetable(self.ServiceStatus) # type: ignore

@dataclass(kw_only=True, slots=True)
class ServiceDay:
    ServiceTag: Optional[str] = None
    Monday: int
    Tuesday: int
    Wednesday: int
    Thursday: int
    Friday: int
    Saturday: int
    Sunday: int
    NationalHolidays: Optional[int] = None

    def __item_for(self, boolean: bool, exclude: set[str] | None = None) -> list[str]:
        if exclude is None:
            exclude = set()
        fields = ServiceDay.__dataclass_fields__.keys()
        result = []
        for name in fields - exclude - {"ServiceTag"}:
            if getattr(self, name) == boolean:
                result.append(name)
        return result
    
    @property
    def has_service_on_holidays(self) -> bool | None:
        return self.NationalHolidays == 1 if self.NationalHolidays is not None else None
    
    @property
    def flat(self) -> dict[str, bool]:
        return {
            "Monday": self.Monday == 1,
            "Tuesday": self.Tuesday == 1,
            "Wednesday": self.Wednesday == 1,
            "Thursday": self.Thursday == 1,
            "Friday": self.Friday == 1,
            "Saturday": self.Saturday == 1,
            "Sunday": self.Sunday == 1,
        }
    
    @property
    def service_days(self) -> list[str]:
        return self.__item_for(True)

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

@dataclass(kw_only=True, slots=True)
class StopTimeDetail:
    StopUID: str
    StopSequence: int
    StopName: I18n
    ArrivalTime: Optional[str] = None
    DepartureTime: Optional[str] = None
    TimeType: Optional[int] = None

    @property
    def is_estimated_time(self) -> bool:
        return self.TimeType == 0


class DailyTimetable(ms.Struct, kw_only=True):
    TripID: str
    StopTimes: List[StopTimeDetail] = []
    
class Timetable(ms.Struct, kw_only=True):
    TripID: str
    IsLowFloor: bool
    StopTimes: List[StopTime] = []    
    ServiceDay: ServiceDay
    SpecialDays: List[SpecialDay] = []

class Schedule(ms.Struct, kw_only=True):
    RouteUID: str
    SubRouteUID: str
    Direction: int
    OperatorID: str
    Timetables: List[Timetable] = []
    Frequencys: List[Frequency] = []
    UpdateTime: str

class DailySchedule(ms.Struct, kw_only=True):
    BusDate: Optional[str] = None
    RouteUID: str
    SubRouteUID: str
    Direction: int
    OperatorID: str
    Timetables: List[DailyTimetable] = []
    UpdateTime: str