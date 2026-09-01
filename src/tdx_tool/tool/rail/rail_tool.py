# Dependencies
from functools import cached_property
from typing import Literal, TypeAlias
import pandas as pd
import geopandas as gpd
# Local imports
from ...core import Fetch, RailOperator, Zone
from ...core.wrapper import Wrapper
from ...core.tool import Tool
from .rail_parsers import RailParsers
from .rail_models import *

RefreshableCacheProperty: TypeAlias = Literal[
    "routes"
]

class RailTool(Tool):
    def __init__(
        self,
        fetch: Fetch,
        operator: RailOperator
    ):
        if not isinstance(operator, RailOperator):
            raise ValueError(f"The operator must be an instance of RailOperator.")
        super().__init__(fetch)
        self._operator = operator
        self._regions = [zone.to_id.name
                         for zone in Zone.all_cases()
                         if zone.hasRailService(self._operator)]
    
    @property
    def operator(self) -> RailOperator:
        return self._operator

    @property
    def _parsing(self) -> RailParsers:
        return RailParsers(self.crs, self.logger)

    @property
    def cover_zones(self) -> list[str]:
        return self._regions

    def __api(self, method_name: str, *, subsystem: bool | str = False) -> list[str]:
        """
        Parameter
        ---------
        url: str
            The API endpoint to fetch data from.
        subsystem: bool | str, default False
            *Only applicable for METRO operators*.
            - If `True`, all subsystems will be fetched.
            - If provided as a string, only the specified subsystem will be fetched.
        
        Raises
        ------
        ValueError
            If the `subsystem` parameter is provided as a string but does not match any known subsystem.
        """
        result: list[str] = []
        if self._operator.isMetro:
            match subsystem:
                case False:
                    result.append(
                        f"{self._operator.api}/{method_name}/{self._operator.api_tag_operator}"
                    )
                case True:
                    result.extend([
                        f"{self._operator.api}/{method_name}/{tag}"
                        for tag in self._operator.api_tag_operators
                    ])
                case str() as sub if sub in self._operator.api_tag_operators:
                    result.append(f"{self._operator.api}/{method_name}/{sub}")
                case str() as sub:
                    raise ValueError(f"Invalid subsystem specified: {subsystem}. Must be one of {', '.join(self._operator.api_tag_operators)}.")
        else:
            result.append(f"{self._operator.api}/{method_name}")
        return result
            