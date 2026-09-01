# Dependencies
from functools import cached_property
import pandas as pd
import geopandas as gpd
# Local imports
from ...core import Fetch, Zone
from ...core.wrapper import Wrapper
from ...core.tool import Tool
from .bike_parsers import BikeParsers
from .bike_models import Station, Availability

class BikeTool(Tool):
    def __init__(
        self,
        fetch: Fetch,
        region: Zone
    ):
        if not isinstance(region, Zone):
            raise ValueError(f"The region must be an instance of Zone.")
        super().__init__(fetch)
        self._region = region

    @property
    def _parsing(self) -> BikeParsers:
        return BikeParsers(self.crs, self.logger)

    @property
    def cover_zones(self) -> list[str]:
        return [self._region.to_id.name]

    @cached_property
    def stations(self) -> Wrapper:
        """
        Get the bike stations for the specified region.
        """
        return Wrapper(
            data=self.fetch.retrieve_data(
                "v2/Bike/Station/{City}".format(
                    City = self._region.api_tag_city
                ),
                Station
            ),
            datatype=Station,
            parsers={
                gpd.GeoDataFrame: self._parsing.parse_stations
            },
            hasSpatial=True
        )

    def fetch_availability(self) -> Wrapper:
        """
        Fetch the bike availability for the specified region.
        """
        return Wrapper(
            data=self.fetch.retrieve_data(
                "v2/Bike/Availability/{City}".format(
                    City = self._region.api_tag_city
                ),
                Availability
            ),
            datatype=Availability,
            parsers={
                pd.DataFrame: self._parsing.parse_availability
            }
        )