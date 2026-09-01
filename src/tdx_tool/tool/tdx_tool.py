# Dependencies
from typing import Self, overload, Literal
from logging import Logger
# Local imports
from ..core import (
    RailOperator,
    Zone,
    Auth,
    Fetch
)
from ..core.logger import get_logger
from ..core.constants import VEHICLE_TYPE
from .bus import BusTool
from .bike import BikeTool
from .rail import RailTool

class TDX:
    def __init__(
        self,
        client_id: str,
        client_key: str,
        logger: Logger | None = None
    ):
        self._auth = Auth(
            client_id,
            client_key,
            logger if logger is not None else get_logger()
        )
        self._fetch = Fetch(self._auth)

    @property
    def fetch(self) -> Fetch:
        """
        The shared `Fetch` engine.

        Use this for ad-hoc queries against TDX endpoints that this package does not
        wrap, e.g. inside a poll task:

        >>> tdx.fetch.retrieve_data("v2/Bus/RealTimeByFrequency/City/Taipei", SomeSchema)
        """
        return self._fetch

    def bus(
        self,
        region: Zone | None = None,
        *,
        together: bool = False
    ) -> BusTool:
        if region is None:
            return BusTool.intercity(self._fetch)
        if not isinstance(region, Zone):
            raise ValueError(f"The region must be an instance of Zone.")
        return BusTool(
            self._fetch,
            region=region,
            together=together
        )
    
    def bike(
        self,
        region: Zone
    ) -> BikeTool:
        if not isinstance(region, Zone):
            raise ValueError(f"The region must be an instance of Zone.")
        if not region.isAvailable("Bike"):
            available_regions = [r.name for r in Zone if r.isAvailable("Bike")]
            raise ValueError(f"No bike info for {region.name}, available regions: {', '.join(available_regions)}.")
        return BikeTool(
            self._fetch,
            region=region
        )
    
    def rail(
        self,
        operator: RailOperator
    ) -> RailTool:
        if not isinstance(operator, RailOperator):
            raise ValueError(f"The operator must be an instance of RailOperator.")
        return RailTool(
            self._fetch,
            operator=operator
        )