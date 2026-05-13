from dataclasses import dataclass
from typing import Optional

@dataclass
class I18n:
    Zh_tw: str
    En: Optional[str] = None

@dataclass
class PointPosition:
    PositionLon: float
    PositionLat: float
    GeoHash: str

@dataclass(frozen=True)
class Identity:
    code: str
    zh: str
    en: str
    api_tag: str