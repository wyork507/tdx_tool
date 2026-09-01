# Dependencies
from abc import ABC, abstractmethod
from typing import TypeVar
from logging import Logger
# Local imports
from .fetch import Fetch
from .parser import Parser
from .logger import get_logger
from .constants import DEFAULT_CRS

ParserT = TypeVar("ParserT", bound=Parser)

class Tool(ABC):
    def __init__(self,
        fetch: Fetch,
        logger: Logger | None = None
    ):
        self.fetch = fetch
        self.logger = logger if logger is not None else get_logger()
        self.__crs = DEFAULT_CRS

    @property
    @abstractmethod
    def _parsing(self) -> ParserT: # pyright: ignore[reportInvalidTypeVarUse]
        ...

    @property
    def crs(self) -> str:
        return self.__crs

    @crs.setter
    def crs(self, value: str):
        self.__crs = value

    @property
    @abstractmethod
    def cover_zones(self) -> list[str]:
        ...