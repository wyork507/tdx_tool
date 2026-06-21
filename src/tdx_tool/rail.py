# Dependency imports
from datetime import datetime
from functools import cached_property
from logging import Logger
from typing import Callable, Literal, TypeVar
import msgspec, requests
import pandas as pd
import geopandas as gpd

# Local imports
from .authority import tdx_auth
from .rail_parsers import _rail_parsers
from .core import tdx_tool
from .utils import RailAPI, RailwayOperator, T
from .common_models import Datas

class tdx_rail(tdx_tool):
    def __init__(self,
        client_id: str, client_key: str,
        operators: list[RailwayOperator] | None = None,
        logger: Logger | None = None
    ):
        super().__init__(client_id=client_id, client_key=client_key, logger=logger)
        if operators is None:
            raise ValueError("Operators must be specified for `tdx_rail` enums.")
        self.__operators = operators
        self.logger.debug(f"tdx_rail initialized for operator(s): {', '.join(op.name for op in self.__operators)}")
    
    @classmethod
    def from_region(cls,
        client_id: str,
        client_key: str,
        regions: list[str],
        skip_invalid: bool = False,
        logger: Logger | None = None
    ) -> "tdx_rail":
        """
        Factory method to create an instance of `tdx_rail` based on a region string.
        Args:
            client_id: TDX API client ID.
            client_key: TDX API client key.
            operators: The name of the operators to fetch rail data for. Must match one of the names in `RailwayOperator`.
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
        return cls(
            client_id, client_key, [RailwayOperator(identity) for identity in identities if identity is not None], logger=logger
        )

    @classmethod
    def from_auth(cls, auth: tdx_auth, logger: Logger | None = None, operators: list[RailwayOperator] | None = None) -> "tdx_rail":
        return cls(client_id=auth.client_id, client_key=auth.client_key, operators=operators, logger=logger or auth.logger)
    
    def _url_middle_part(self) -> list[str]:
        return [operator.api() for operator in self.__operators]
    
    def _fetch_multi_operator_data(
        self,
        prefix: str,
        params: dict,
        decoder: dict[RailAPI, Callable[[requests.Response], list[T]]],
        disable: set[RailwayOperator] | None = None
    ) -> dict[RailAPI, list[T]]:
        """
        Cross-operator combined data fetching method. This method will fetch data for all operators configured in this instance
        of `tdx_rail`, unless some operators are specified in the `disable` set.
        """
        results: dict[RailAPI, list[T]] = {}
        operators = set(self.__operators.copy())
        if disable is not None:
            operators -= disable
            self.logger.debug(f"Disabled operator(s) for this fetch: {', '.join(op.name for op in disable)}")
        for operator in operators:
            result: list[T] = []
            if operator.api not in decoder:
                self.logger.warning(f"No decoder found for operator {operator.name} (API: {operator.api}). Skipping data fetch for this operator.")
                continue
            for tag in operator.api_tags_including_sub:
                result.extend(self._fetch_combined_data(
                    prefix=f"{operator.api()}/{tag}/{prefix}",
                    params={**params},
                    decoder=decoder[operator.api]
                ))
            self.logger.debug(f"Fetched {len(result)} records for operator {operator.name} with params: {params}")
            results[operator.api] = result
        return results
    
    @property
    def operators(self) -> list[RailwayOperator]:
        """The railway operators that this instance of `tdx_rail` is configured to fetch data for."""
        return self.__operators
    
    @cached_property
    def lines(self) -> Datas:
        """all lines of the specified railway operators"""
        from .rail_models import LineV2 as Line
        from .common_models import I18n
        results: list[Line] = []
        operatros = self.__operators.copy()
        if RailwayOperator.INTER_HSR in operatros:
            operatros.remove(RailwayOperator.INTER_HSR)
            results.append(Line(
                LineID="HSR",
                LineName=I18n("臺灣高鐵"),
                LineSectionName=I18n("南港-左營"),
                IsBranch=False,
                SrcUpdateTime="2026-06-21T16:44:06+08:00",
                UpdateTime="2026-06-21T16:44:06+08:00"
            ))
        for operator in operatros:
            operator_results = self._fetch_combined_data(
                prefix=f"{operator.api_tags_including_sub}",
                
            )
            

    @cached_property
    def stations(self):
        pass

    @cached_property
    def station_of_line(self):
        pass
    
    @cached_property
    def shapes(self):
        pass