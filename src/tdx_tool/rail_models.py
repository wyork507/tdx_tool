# Dependencies
from dataclasses import dataclass, field
from enum import IntEnum
from typing import List, Optional
import msgspec as ms
# Local imports
from .common_models import I18n, PointPosition, ServiceDay, SpecialDay
from .utils import RailwayOperator

class RailDirection(IntEnum):
    SouthboundOrInner = 0  # 南下 / 內圈
    NorthboundOrOuter = 1  # 北上 / 外圈
    Unknown           = 255

class TrainTypeProperty(IntEnum):
    Normal    = 0  # 一般車次
    Holiday   = 1  # 節日/加班車
    Suspended = 2  # 停駛車次

# ======================
# MARK: Line and Station
# ======================
class StationOfLine(ms.Struct, kw_only=True):
    StationID: str
    Sequence: int

class LineBasic(ms.Struct, kw_only=True):
    LineID: str
    LineNo: Optional[int] = None 
    LineName: I18n
    LineSectionName: I18n
    LineColor: Optional[str] = None  # 十六進位色碼 (Hex color code)，如 "#FF0000" 表示紅色
    IsBranch: bool  # 是否為支線

class LineV2(LineBasic, kw_only=True):
    SrcUpdateTime: str
    UpdateTime: str

    @staticmethod
    def HSR() -> "LineV2":
        return LineV2(
                LineID="HSR",
                LineName=I18n("臺灣高鐵"),
                LineSectionName=I18n("南港-左營"),
                IsBranch=False,
                SrcUpdateTime="2026-06-21T16:44:06+08:00",
                UpdateTime="2026-06-21T16:44:06+08:00"
        )

class LineV3(ms.Struct, kw_only=True):
    SrcUpdateTime: str
    UpdateTime: str
    Items: List[LineBasic]

class StationBasic(ms.Struct, kw_only=True):
    StationUID: str
    StationID: str
    StationClass: Optional[str] = None
    StationName: I18n
    StationAddress: Optional[str] = None
    StationPosition: PointPosition

class StationV2(StationBasic, kw_only=True):
    BikeAllowOnHoliday: Optional[bool] = None
    SrcUpdateTime: str
    UpdateTime: str

class StationV3(ms.Struct, kw_only=True):
    SrcUpdateTime: str
    UpdateTime: str
    Stations: List[StationBasic]

class RailRoute(ms.Struct, kw_only=True):
    RouteID: str
    LineID: str
    Direction: int  # RailDirection
    RouteName: I18n
    StartStationID: str
    EndStationID: str
    UpdateTime: str

class StationFacility(ms.Struct, kw_only=True):
    FacilityType: str
    Description: str

@dataclass(kw_only=True, slots=True)
class RailStation:
    StationUID: str
    StationID: str
    StationCode: Optional[str] = None
    StationName: I18n
    StationPosition: PointPosition
    StationAddress: Optional[str] = None
    OperatorID: str
    Lines: List[str] = field(default_factory=list)  # 該車站所屬的 LineID 清單
    Facilities: List[StationFacility] = field(default_factory=list)
    UpdateTime: str

# ========================
# MARK: - Timetable & Fare
# ========================
class RailStopTime(ms.Struct, kw_only=True):
    """列車停靠站點與時間 (StopTime)"""
    StopSequence: int
    StationID: str
    StationName: I18n
    ArrivalTime: Optional[str] = None    # 保持 str，容忍 "24:12" 這種跨夜時間
    DepartureTime: Optional[str] = None
    Suspended: int = 0  # 該站是否臨時不停靠 (0: 否, 1: 是)

class TrainInfo(ms.Struct, kw_only=True):
    """車次屬性基本資料 (TrainInfo)"""
    TrainNo: str      # 台鐵/高鐵的核心 Key
    RouteID: str
    Direction: int    # RailDirection
    TrainTypeID: str  # 車種代碼 (如台鐵的 1100 自強號)
    TrainTypeName: I18n
    StartingStationID: str
    EndingStationID: str
    OverNightStationID: Optional[str] = None  # 跨夜基準站
    Note: Optional[I18n] = None

class RailTimetable(ms.Struct, kw_only=True):
    """定期車次時刻表 (TimeTableList)"""
    TrainInfo: TrainInfo
    StopTimes: List[RailStopTime]
    ServiceDay: ServiceDay
    SpecialDays: List[SpecialDay] = field(default_factory=list)

class DailyTrainTimetable(ms.Struct, kw_only=True):
    """每日車次時刻表 (與定期表分開，通常由特定日期 API 回傳)"""
    TrainDate: str
    TrainInfo: TrainInfo
    StopTimes: List[RailStopTime]
    TrainProperty: int = 0  # TrainTypeProperty
    UpdateTime: str

class ODFare(ms.Struct, kw_only=True):
    """起迄站票價資料 (ODFareList)"""
    OriginStationID: str
    DestinationStationID: str
    TicketType: str       # 如 "全票", "敬老票"
    FareClass: str        # 如 "標準車廂", "商務車廂", "自由座"
    Price: int

# ===========================
# MARK: - Live Board Dynamics
# ===========================
class TrainLiveBoard(ms.Struct, kw_only=True):
    """列車即時位置看板 (TrainLiveBoardList)"""
    TrainNo: str
    RailType: int
    StationID: str        # 當前/最新通過之車站ID
    TrainStatus: int      # 0:在站上, 1:即將進站, 2:已離站
    DelayTime: int        # 誤點時間 (分鐘，0為準點)
    UpdateTime: str

class StationLiveBoard(ms.Struct, kw_only=True):
    """車站即時到離站動態看板 (StationLiveBoardList)"""
    StationID: str
    TrainNo: str
    Direction: int
    TrainTypeName: I18n
    EndingStationName: I18n
    ScheduledArrivalTime: Optional[str] = None
    ScheduledDepartureTime: Optional[str] = None
    EstimatedArrivalTime: Optional[str] = None
    EstimatedDepartureTime: Optional[str] = None
    DelayTime: int        # 誤點時間 (分鐘)
    TripStatus: int = 0   # 0: 正常, 1: 停駛
    SrcUpdateTime: str