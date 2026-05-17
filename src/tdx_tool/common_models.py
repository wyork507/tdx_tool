from dataclasses import dataclass
from typing import Optional

@dataclass(frozen=True)
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

@dataclass(frozen=True)
class PointPosition:
    PositionLon: float
    PositionLat: float
    GeoHash: str

    def flat(self, prefix: str | None = None) -> dict[str, float | str]:
        if prefix is None:
            prefix = ""
        return {
            f"{prefix}PositionLon": self.PositionLon,
            f"{prefix}PositionLat": self.PositionLat,
            f"{prefix}GeoHash": self.GeoHash
        }
    
    @property
    def flat_without_prefix(self) -> dict[str, float | str]:
        return self.flat(prefix="")

@dataclass(frozen=True)
class Identity:
    code: str
    zh: str
    en: str
    api_tag: str