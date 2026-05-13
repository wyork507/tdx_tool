# Dependency imports
from datetime import datetime
from functools import cached_property
from logging import Logger
from typing import Literal
import msgspec, requests
import pandas as pd
import geopandas as gpd
# Local imports
from .parsers import _bike_parsers
from .core import tdx_tool
from .utils import BikeRegion
from .bike_models import Station, Availability

class tdx_bike(tdx_tool):
    def __init__(self,
        client_id: str, client_key: str,
        regions: list[BikeRegion] | None = None,
        logger: Logger | None = None
    ):
        super().__init__(client_id=client_id, client_key=client_key, logger=logger)
        if regions is None:
            raise ValueError("Regions must be specified for `tdx_bike` enums.")
        self.regions = regions
        self.logger.debug(f"tdx_bike initialized for region(s): {', '.join(r.value.en for r in self.regions)}")
        self._parsers = _bike_parsers(self.logger)
    
    @classmethod
    def from_region_str(cls,
        client_id: str,
        client_key: str,
        regions: list[str],
        skip_invalid: bool = False,
        logger: Logger | None = None
    ) -> "tdx_bike":
        """
        Factory method to create an instance of `tdx_bike` based on a region string.
        Args:
            client_id: TDX API client ID.
            client_key: TDX API client key.
            region: The name of the region to fetch bike data for. Must match one of the names in `BikeRegion`.
            skip_invalid: Whether to skip invalid region names.
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
            for region, identity in record:
                if identity is not None:
                    record.remove((region, identity))
            print(f"Warning: The following region names were invalid and have been skipped:")
            print(f"\t\t{', '.join(region for region, _ in record)}")
        return cls(
            client_id, client_key, [BikeRegion(identity) for identity in identities if identity is not None], logger=logger
        )
        

    def _url_middle_part(self) -> list[str]:
        return [f"City/{region.api_tag}" for region in self.regions]

    @cached_property
    def stations(self) -> gpd.GeoDataFrame:
        """
        """
        def decoder(response: requests.Response) -> list[Station]:
            return msgspec.json.decode(response.content, type=list[Station])
        
        data = self._fetch_combined_data(
            prefix="v2/Bike/Station",
            params={
                "$select": "StationUID,StationName,StationPosition,StationAddress,StopDescription,BikesCapacity,ServiceType,UpdateTime",
            },
            decoder=decoder,
            parser=self._parsers.parse_stations
        ).sort_values("StationUID").reset_index(drop=True)
        coor = data[["PositionLon", "PositionLat"]]
        self.logger.debug(f"Creating GeoDataFrame with {len(data)} stations.")
        return gpd.GeoDataFrame(
            data.drop(columns=["PositionLon", "PositionLat"]),
            geometry = gpd.points_from_xy(coor["PositionLon"], coor["PositionLat"]),
            crs = self.default_coor
        )
    
    def fetch_availability(self) -> pd.DataFrame:
        """
         Fetch bike availability data for the specified region.
         You can refresh the cache by `refresh_cache("availability")`.
        """
        def decoder(response: requests.Response) -> list[Availability]:
            return msgspec.json.decode(response.content, type=list[Availability])
        
        return self._fetch_combined_data(
            prefix="v2/Bike/Availability",
            params={
                "$select": "StationUID,ServiceStatus,AvailableRentBikes,AvailableReturnBikes,UpdateTime,AvailableRentBikesDetail",
            },
            decoder=decoder,
            parser=self._parsers.parse_availability
        )


