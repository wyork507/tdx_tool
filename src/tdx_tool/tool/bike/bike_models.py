# Dependencies
from enum import IntEnum
from typing import Optional
import msgspec as ms
# Local imports
from ...core import I18n, PointPosition

class ServiceType(IntEnum):
    YouBike1 = 1 # YouBike1.0 (已退役)
    YouBike2 = 2
    Moovo    = 3

class ServiceStatus(IntEnum):
    Stoping = 0
    Operate = 1
    Suspend = 2

class Station(ms.Struct, kw_only=True):
    StationUID: str
    StationName: I18n
    StationPosition: PointPosition
    StationAddress: I18n
    StopDescription: Optional[str] = None
    BikesCapacity: int
    ServiceType: int
    UpdateTime: str

class AbleBikeDetail(ms.Struct, kw_only=True):
    GeneralBikes: int
    ElectricBikes: int

class Availability(ms.Struct, kw_only=True):
    StationUID: str
    ServiceStatus: int
    AvailableRentBikes: int
    AvailableReturnBikes: int
    UpdateTime: str
    AvailableRentBikesDetail: Optional[AbleBikeDetail] = None