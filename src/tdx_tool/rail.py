# Dependency imports
from datetime import datetime
from functools import cached_property
from logging import Logger
from typing import Callable, Literal, TypeVar, overload
import msgspec, requests
import pandas as pd
import geopandas as gpd

# Local imports
from .authority import tdx_auth
from .rail_parsers import _rail_parsers
from .core import tdx_tool
from .utils import (
    RailAPI,
    RailwayOperator as Operator
)
from .common_models import Datas

OperatorV2 = Literal[
    Operator.INTER_HSR,
    Operator.METRO_TPE,
    Operator.METRO_NTP,
    Operator.METRO_TAO,
    Operator.METRO_TXG,
    Operator.METRO_KNN
]

OperatorV3 = Literal[
    Operator.INTER_AFR,
    Operator.INTER_TRC,
]

class tdx_rail(tdx_tool):
    @overload
    def __new__(cls,
        client_id: str,
        client_key: str,
        operator: OperatorV2,
        logger: Logger | None = None
    ) -> "tdx_rail_v2": ...
    
    @overload
    def __new__(cls,
        client_id: str,
        client_key: str,
        operator: OperatorV3,
        logger: Logger | None = None
    ) -> "tdx_rail_v3": ...

    def __new__(cls,
        client_id: str,
        client_key: str,
        operator: OperatorV2 | OperatorV3,
        logger: Logger | None = None
    ):
        if not isinstance(operator, (OperatorV2, OperatorV3)):
            raise TypeError("Invalid operator type.")
        if operator in OperatorV2:
            return object.__new__(tdx_rail_v2)
        elif operator in OperatorV3:
            return object.__new__(tdx_rail_v3)
        else:
            raise ValueError("Invalid operator specified.")

    def __init__(self,
        client_id: str, client_key: str,
        operator: Operator | None = None,
        logger: Logger | None = None
    ):
        super().__init__(client_id=client_id, client_key=client_key, logger=logger)
        if operator is None:
            raise ValueError("Operator must be specified for `tdx_rail` enums.")
        self.__operator = operator
        self.logger.debug(f"tdx_rail initialized for operator(s): {self.__operator.value.en}")
    
    @classmethod
    def from_region(cls,
        client_id: str,
        client_key: str,
        regions: list[str],
        skip_invalid: bool = False,
        logger: Logger | None = None
    ) -> dict[Operator, "tdx_rail"]:
        """
        Factory method to create an instance of `tdx_rail` based on a region string.
        Args:
            client_id: TDX API client ID.
            client_key: TDX API client key.
            operator: The name of the operator to fetch rail data for. Must match one of the names in `RailwayOperator`.
            skip_invalid: Whether to skip invalid operator names.
            logger: Optional logger for debugging and information messages.
        """
        from .utils import strings_into_identities as convertor
        identities = []
        try:
            identities = convertor(regions, skip_invalid)
        except ValueError as e:
            raise e
        if skip_invalid and any(identity is None for identity in identities):
            record = list(zip(regions, identities))
            for operator, identity in record:
                if identity is not None:
                    record.remove((operator, identity))
            print(f"Warning: The following operator names were invalid and have been skipped:")
            print(f"\t\t{', '.join(operator for operator, _ in record)}")
        return {Operator(identity): cls(client_id, client_key, Operator(identity), logger=logger)
                for identity in identities if identity is not None}

    @classmethod
    def from_auth(cls, auth: tdx_auth, logger: Logger | None = None, operator: Operator | None = None) -> "tdx_rail":
        return cls(client_id=auth.client_id, client_key=auth.client_key, operator=operator, logger=logger or auth.logger)

    def _url_middle_part(self) -> list[str]:
        return [self.__operator.api()]
    
    @property
    def operator(self) -> Operator:
        """The railway operators that this instance of `tdx_rail` is configured to fetch data for."""
        return self.__operator

class tdx_rail_v2(tdx_rail):
    def __init__(self,
        client_id: str, client_key: str,
        operator: OperatorV2,
        logger: Logger | None = None
    ):
        super().__init__(client_id, client_key, operator, logger)

    @cached_property
    def lines(self):
        """all lines of the specified railway operators"""
        pass

    @cached_property
    def stations(self):
        pass

    @cached_property
    def station_of_line(self):
        pass
    
    @cached_property
    def shapes(self):
        pass

class tdx_rail_v3(tdx_rail):
    def __init__(self,
        client_id: str, client_key: str,
        operator: OperatorV3,
        logger: Logger | None = None
    ):
        super().__init__(client_id, client_key, operator, logger)
    
    @cached_property
    def lines(self):
        """all lines of the specified railway operators"""
        pass

    @cached_property
    def stations(self):
        pass

    @cached_property
    def station_of_line(self):
        pass
    
    @cached_property
    def shapes(self):
        pass