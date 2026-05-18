# Dependencies
from datetime import datetime, time, date
from logging import Logger
import pandas as pd
import geopandas as gpd
import shapely
# Local imports
from .bike_models import Station, Availability
from .common_parsers import _parsers

class _bike_parsers(_parsers):
    def __init__(self, logger: Logger):
        super().__init__(logger)
    
    def parse_stations(self, stations: list[Station]) -> pd.DataFrame:
        """
        """
        data = []
        for s in stations:
            data.append({
                "StationUID": s.StationUID,
                **s.StationName.flat("StationName"),
                "StationPosition": s.StationPosition,
                **s.StationAddress.flat("StationAddress"),
                "StopDescription": s.StopDescription,
                "BikesCapacity": s.BikesCapacity,
                "ServiceType": s.ServiceType,
                "UpdateTime": self.decoding_datetime(s.UpdateTime),
                **s.StationPosition.flat_without_prefix
            })
        return pd.DataFrame(data)
    
    def parse_availability(self, availability: list[Availability]) -> pd.DataFrame:
        """
        """
        data = []
        for a in availability:
            base = {
                "StationUID": a.StationUID,
                "ServiceStatus": a.ServiceStatus,
                "AvailableRentBikes": a.AvailableRentBikes,
                "AvailableReturnBikes": a.AvailableReturnBikes,
                "UpdateTime": self.decoding_datetime(a.UpdateTime)
            }
            if a.AvailableRentBikesDetail is not None:
                base["AvailableGeneralBikes"] = a.AvailableRentBikesDetail.GeneralBikes
                base["AvailableElectricBikes"] = a.AvailableRentBikesDetail.ElectricBikes
            data.append(base)
        return pd.DataFrame(data)