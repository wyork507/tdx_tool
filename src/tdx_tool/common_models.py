from dataclasses import dataclass
from _typeshed import DataclassInstance
from functools import cached_property
from typing import Optional, Callable, Dict, Type, Union, cast, TypeVar, List, overload
from pandas import DataFrame
from geopandas import GeoDataFrame
from xarray import DataArray
from msgspec import Struct

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

class Datas:
    """
    A wrapper class for data list that provides some useful methods.

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
    DataType = TypeVar("DataType", bound=Union[Struct, DataclassInstance])
    ParsersType = Callable[[list[DataType]], OutputType]
    def __init__(self,
        data: List[DataType],
        datatype: Type[DataType],
        parsers: Dict[Type, ParsersType],
        description: str = "",
        hasSpatial: bool = False
    ) -> None:
        self.__datas = data
        self.datatype = datatype
        self.__parsers = parsers
        self.__description = description
        self.hasSpatial = hasSpatial
    
    @property
    def data(self) -> list[Struct | DataclassInstance]:
        return self.__datas
    
    @cached_property
    def to_dataframe(self) -> DataFrame:
        """available for all data types"""
        return cast(DataFrame, self.__parsers[DataFrame](self.__datas))
    
    @cached_property
    def to_geodataframe(self) -> GeoDataFrame | None:
        """only available for spatial data types (e.g., those with PointPosition)"""
        try:
            parser = self.__parsers[GeoDataFrame]
            if parser is None:
                return None
            else:
                return cast(GeoDataFrame, parser(self.__datas))
        except KeyError:
            return None

    @cached_property
    def to_xarray(self) -> DataArray | None:
        """for spatial or multi-dimensional data, may not be implemented for all data types"""
        try:
            parser = self.__parsers[DataArray]
            if parser is None:
                return None
            else:
                return cast(DataArray, parser(self.__datas))
        except KeyError:
            return None
    
    @overload
    def __getitem__(self, key: int) -> Struct | DataclassInstance: ...
    @overload
    def __getitem__(self, key: slice) -> list[Struct | DataclassInstance]: ...
    
    def __getitem__(self, key) -> DataType | list[DataType]:
        return self.__datas[key]
    
    def __call__(self) -> list[Struct | DataclassInstance]:
        return self.__datas

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
    
    def _repr_markdown_(self) -> str:
        return f"""{self.__str__()}
        ---
        Available Attributes:
        - to_dataframe: DataFrame
        {"- to_geodataframe: GeoDataFrame" if self.__parsers.get(GeoDataFrame) is not None and self.hasSpatial is True else ""}
        {"- to_xarray: DataArray" if self.__parsers.get(DataArray) is not None else ""}
        ---
        You can access the data by these following ways:
        - Indexing: `datas[0]` or `datas[0:10]`
        - Iteration: `for item in datas: ...`
        - Call: `datas()`
        """