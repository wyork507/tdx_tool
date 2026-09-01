# Dependencies
from dataclasses import dataclass
from enum import Enum, StrEnum
from typing import Self, ClassVar, Dict, Any, Protocol, Optional, NamedTuple, Type, Union, TypeVar
from msgspec import Struct

class ID(NamedTuple):
    code: str
    name: str

class DataclassInstance(Protocol):
    __dataclass_fields__: ClassVar[Dict[str, Any]]

DataType = TypeVar("DataType", bound=Union[Struct, DataclassInstance])

class IdEnum(Enum):
    def __new__(cls, code: str, name: str):
        obj = object.__new__(cls)
        obj._value_ = name
        return obj
    
    def __init__(self, code: str, name: str):
        self.code = code

    @classmethod
    def all_cases(cls) -> list[Self]:
        return list(cls)

    @property
    def to_id(self) -> ID:
        return ID(self.code, self.value)

    @classmethod
    def from_id(cls, id: ID) -> Self:
        for case in cls:
            if case.code == id.code and case.value == id.name:
                return case
        raise ValueError(f"{id} is not a valid {cls.__name__} ID.")

@dataclass(frozen=True, slots=True)
class I18n:
    Zh_tw: str
    En: Optional[str] = None
    Ja: Optional[str] = None
    Ko: Optional[str] = None
    
    def flat(self, prefix: str | None = None) -> dict[str, str]:
        if prefix is None:
            prefix = ""
        data: dict[str, str] = {}
        for lang in I18n.__dataclass_fields__.keys():
            if (value := getattr(self, lang)) is not None:
                data[f"{prefix}{lang}"] = value
        return data

@dataclass(frozen=True, slots=True)
class PointPosition:
    PositionLon: float
    PositionLat: float
    GeoHash: Optional[str] = None

    def flat(self, prefix: str | None = None) -> dict[str, float | str]:
        if prefix is None:
            prefix = ""
        return {
            f"{prefix}PositionLon": self.PositionLon,
            f"{prefix}PositionLat": self.PositionLat,
            f"{prefix}GeoHash": self.GeoHash or ""
        }
    
    @property
    def flat_without_prefix(self) -> dict[str, float | str]:
        return self.flat(prefix="")

class ServiceStatus(StrEnum):
    Cancel = "停駛"
    Normal = "正常"
    Errors = "異常"
    Extras = "加班"

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
            case ServiceStatus.Extras:
                return 1
            case ServiceStatus.Cancel:
                return 2
            case _:
                return None

class Operator(Struct, kw_only=True):
    OperatorID: str
    OperatorName: I18n

class Period(Struct, kw_only=True):
    StartDate: str
    EndDate: str

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

@dataclass(kw_only=True, slots=True)
class SpecialDay:
    Dates: list[str]
    DatePeriod: Optional[Period] = None
    ServiceStatus: int
    Description: Optional[str] = None

    @property
    def status(self) -> "ServiceStatus":
        return ServiceStatus.from_timetable(self.ServiceStatus) # type: ignore
