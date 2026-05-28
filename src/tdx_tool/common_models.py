from dataclasses import dataclass
from typing import (
    Optional, Callable, Dict, Type, Protocol, Any,
    Union, TypeVar, List, overload, ClassVar, TYPE_CHECKING,
    ParamSpec,
    Concatenate as C
)
from pandas import DataFrame
from geopandas import GeoDataFrame
from xarray import DataArray
from msgspec import Struct

class DataclassInstance(Protocol):
    __dataclass_fields__: ClassVar[Dict[str, Any]]

DataType = TypeVar("DataType", bound=Union[DataclassInstance, Struct])

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

@dataclass(frozen=True, slots=True)
class Identity:
    code: str
    zh: str
    en: str
    api_tag: str

class Datas:
    """
    A immutable wrapper class for data list that provides some useful methods.

    Attributes
    ----------
    datas: list[Struct | DataclassInstance]
        list of data objects (e.g., list of dataclass-like instances)
    datatype: Type
        the type of the data objects in the list (e.g., a dataclass type)
    to_dataframe: DataFrame | GeoDataFrame (cached)
        dataframe coverted from the data list, if spatial data included, it will be a GeoDataFrame
    to_geodataframe: GeoDataFrame (cached, only available if spatial data included)
        geodataframe converted from the data list, only available if spatial data included
    to_xarray: DataArray (cached, may not be implemented for all data types)
        xarray DataArray converted from the data list, suitable for multi-dimensional data
    """
    OutputType = Union[DataFrame, GeoDataFrame, DataArray]
    P = ParamSpec("P")
    ParsersType = Callable[C[list[DataType], P], OutputType]
    datatype: Type[Struct | DataclassInstance]
    hasSpatial: bool
    __datas: list[Struct | DataclassInstance]
    __parsers: dict[Type[OutputType], ParsersType]
    __description: str
    __cache: dict[Type[OutputType], OutputType]
    
    if TYPE_CHECKING:
        @property
        def df(self) -> DataFrame:
            """alias of `to_dataframe` for convenience"""
            ...
        @property
        def to_dataframe(self) -> DataFrame: ...
        @property
        def gdf(self) -> GeoDataFrame | None:
            """alias of `to_geodataframe` for convenience"""
            ...
        @property
        def to_geodataframe(self) -> GeoDataFrame | None: ...
        @property
        def xr(self) -> DataArray | None:
            """alias of `to_xarray` for convenience"""
            ...
        @property
        def to_xarray(self) -> DataArray | None: ...
    
    def __init__(self,
        data: List[DataType],
        datatype: Type[DataType],
        parsers: Dict[Type[OutputType], ParsersType],
        description: str = "",
        hasSpatial: bool = False
    ) -> None:
        super().__setattr__("datatype", datatype)
        super().__setattr__("hasSpatial", hasSpatial)
        super().__setattr__("_Datas__datas", data)
        super().__setattr__("_Datas__parsers", parsers)
        super().__setattr__("_Datas__description", description)
        super().__setattr__("_Datas__cache", {})
    
    @property
    def data(self) -> list[Struct | DataclassInstance]:
        return self.__datas.copy()
    
    @property
    def available_formats(self) -> list[Type[OutputType]]:
        """to know which output formats are available for this data type"""
        return [dtype for dtype in [DataFrame, GeoDataFrame, DataArray] if dtype in self.__parsers]
    
    def __get_or_parse(self, output_type: Type[OutputType]) -> OutputType | None:
        if output_type in self.__cache: # already parsed, return cached result
            return self.__cache[output_type].copy()
        if output_type not in self.__parsers: # not supported
            return None
        # First time parsing, then cache the result
        result = self.__parsers[output_type](self.__datas)
        self.__cache[output_type] = result
        return result

    def __getattr__(self, name: str) -> OutputType | None:
        match name:
            case "to_dataframe" |  "df":
                return self.__get_or_parse(DataFrame)
            case "to_geodataframe" | "gdf":
                return self.__get_or_parse(GeoDataFrame)
            case "to_xarray" | "xr":
                return self.__get_or_parse(DataArray)
            case _:
                raise AttributeError(f"{self.__class__.__name__} object has no attribute '{name}'")
    
    @overload
    def __getitem__(self, key: int) -> Struct | DataclassInstance: ...
    @overload
    def __getitem__(self, key: slice) -> list[Struct | DataclassInstance]: ...
    
    def __getitem__(self, key: int | slice):
        return self.__datas[key]
    
    def __len__(self):
        return len(self.__datas)
    
    def __iter__(self):
        return iter(self.__datas)
        
    def __repr__(self) -> str:
        return f"""[{{"spatial" if self.hasSpatial else "regular"}}] {self.datatype.__name__} ({len(self.__datas)} items)"""
    
    def __str__(self) -> str:
        return f"""{self.__repr__()}\n
        > {self.__description}
        """
    
    def __setattr__(self, name: str, value: Any) -> None:
        raise AttributeError("This is immutable")
    
    def __delattr__(self, name: str) -> None:
        raise AttributeError("This is immutable")
    
    def _repr_html_(self) -> str:
        spatial_badge = (
            '<span style="background:#4CAF50;color:white;padding:2px 6px;border-radius:4px;font-size:11px">spatial</span>'
            if self.hasSpatial else
            '<span style="background:#2196F3;color:white;padding:2px 6px;border-radius:4px;font-size:11px">regular</span>'
        )
        formats = self.available_formats

        attrs = ['<li><code>to_dataframe</code> → DataFrame</li>']
        if GeoDataFrame in formats:
            attrs.append('<li><code>to_geodataframe</code> → GeoDataFrame</li>')
        if DataArray in formats:
            attrs.append('<li><code>to_xarray</code> → DataArray</li>')

        return f"""
        <div style="border:1px solid #ddd;border-radius:6px;padding:12px;font-family:monospace;max-width:480px">
            <div style="margin-bottom:6px">
                {spatial_badge}
                <strong style="margin-left:8px">{self.datatype.__name__}</strong>
                <span style="color:#888;margin-left:8px">({len(self.__datas)} items)</span>
            </div>
            <div style="color:#555;font-size:12px;margin-bottom:8px">{self.__description}</div>
            <hr style="margin:6px 0;border:none;border-top:1px solid #eee">
            <div style="font-size:12px">
                <strong>Available conversions:</strong>
                <ul style="margin:4px 0;padding-left:16px">{''.join(attrs)}</ul>
                <strong>Access patterns:</strong>
                <ul style="margin:4px 0;padding-left:16px">
                    <li>Index: <code>datas[0]</code> or <code>datas[0:10]</code></li>
                    <li>Iter: <code>for item in datas</code></li>
                    <li>Raw list: <code>list(datas)</code></li>
                </ul>
            </div>
        </div>
        """

    def _repr_markdown_(self) -> str:
        tag = "spatial" if self.hasSpatial else "regular"
        formats = self.available_formats

        lines = [
            f"**[{tag}] {self.datatype.__name__}** ({len(self.__datas)} items)",
            f"> {self.__description}",
            "",
            "**Available conversions:**",
            "- `to_dataframe` → DataFrame",
        ]
        if GeoDataFrame in formats:
            lines.append("- `to_geodataframe` → GeoDataFrame")
        if DataArray in formats:
            lines.append("- `to_xarray` → DataArray")
        lines += [
            "",
            "**Access patterns:** `datas[0]` · `datas[0:10]` · `for item in datas` · `list(datas)`"
        ]
        return "\n".join(lines)