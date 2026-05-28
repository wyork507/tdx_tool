# Dependency imports
from datetime import datetime
from functools import cached_property
from logging import Logger
from typing import Literal
import msgspec, requests
import pandas as pd
import geopandas as gpd

from tdx_tool.authority import tdx_auth
# Local imports
from .rail_parsers import _rail_parsers
from .core import tdx_tool
from .utils import RailwayOperator
from .rail_models import *

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
    
    