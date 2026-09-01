# Dependencies
from enum import IntEnum
from typing import Literal
from pandas import DataFrame
from geopandas import GeoDataFrame
from xarray import DataArray
# Local imports
from .models import IdEnum, ID, DataclassInstance

# =======================
# MARK: - Library Related
# =======================
PACKAGE_NAME = "tdx_tool"
OUTPUT_DIR = "tdx_tool_output"

# Supported vehicle types for TDX API
VEHICLES: list[str] = ["Bus", "Rail", "Bike"]
VEHICLE_TYPE = Literal["Bus", "Rail", "Bike"]

# Supported Output Formats
FORM_OUTPUTS: list[str] = ["json", "csv", "parquet"]
FORM_OUTPUT_TYPE = Literal["json", "csv", "parquet"]
GEOG_OUTPUTS: list[str] = ["shapefile", "geojson", "geoparquet"]
GEOG_OUTPUT_TYPE = Literal["shapefile", "geojson", "geoparquet"]

# Wrapper Output Types
WRAPPER_OUTPUTS: list[str] = ["DataFrame", "GeoDataFrame", "DataArray"]
WRAPPER_OUTPUT_TYPE = Literal[DataFrame, GeoDataFrame, DataArray]

# Spatial defaults
DEFAULT_CRS = "EPSG:4326" # WGS 84
DEFAULT_OUTPUT_FORMAT: FORM_OUTPUT_TYPE = "parquet"
DEFAULT_OUTPUT_GEOFORMAT: GEOG_OUTPUT_TYPE = "geoparquet"

# TDX API Site
TDX_URL_BASE = "https://tdx.transportdata.tw"
TDX_API_BASE = f"{TDX_URL_BASE}/api/basic"
TDX_URL_AUTH = f"{TDX_URL_BASE}/auth/realms/TDXConnect/protocol/openid-connect/token"

# =================
# MARK: - Operators
# =================
# Bike
class BikeOperator(IntEnum):
    """All available bike operators for TDX API."""
    YouBike1 = 1 # YouBike1.0 (已退役)
    YouBike2 = 2
    Moovo    = 3

# Railway
class RailOperator(IdEnum):
    """All available railway operators for TDX API."""
    INTER_TRC = ("TRA", "Taiwan Railway Corporation")
    """
    臺灣鐵路股份有限公司
    
    Note
    ----
    If you are fetching data from TDx API, you would still receive the oudated details with `TRA` tag and
    the name of "臺灣鐵路管理局" (Taiwan Railway Administration).

    But the TRA was companilze and changed its name to Taiwan Railway Corporation in 2024, so I use the
    updated name and keep the api_tag in the code.
    """
    INTER_HSR = ("THSR", "Taiwan High Speed Rail Corporation")
    """台灣高速鐵路股份有限公司"""
    INTER_AFR = ("AFR",  "Alishan Forest Railway and Cultural Heritage Office")
    """阿里山林業鐵路及文化資產管理處"""
    METRO_TPE = ("TRTC", "Taipei Rapid Transit Corporation")
    """臺北大眾捷運股份有限公司"""
    METRO_NTP = ("NTMC", "New Taipei Metro Corporation")
    """新北大眾捷運股份有限公司"""
    METRO_TAO = ("TYMC", "Taoyuan Metro Corporation")
    """桃園大眾捷運股份有限公司"""
    METRO_TXG = ("TMRT", "Taichung Mass Rapid Transit Corporation")
    """臺中捷運股份有限公司"""
    METRO_KNN = ("KRTC", "Kaohsiung Rapid Transit Corporation")
    """高雄捷運股份有限公司"""

    @property
    def isMetro(self) -> bool:
        return self.name.startswith("METRO_")
    
    @property
    def systems(self) -> list[ID]:
        match self:
            case RailOperator.METRO_TPE:
                return [
                    self.to_id,
                    ID("TRTCMG", "Maokong Gondola")
                ]
            case RailOperator.METRO_NTP:
                return [
                    self.to_id,
                    ID("NTDLRT", "Danhai Light Rail"),
                    ID("NTALRT", "Ankeng Light Rail")
                ]
            case RailOperator.METRO_KNN:
                return [
                    self.to_id,
                    ID("KLRT", "Kaohsiung Light Rail")
                ]
            case _:
                return [self.to_id]
    
    @property
    def api_tag_operator(self) -> str:
        return self.code

    @property
    def api_tag_operators(self) -> list[str]:
        return [system.code for system in self.systems]

    @property
    def api(self) -> str:
        match self:
            case RailOperator.INTER_TRC:
                return "v3/Rail/TRA"
            case RailOperator.INTER_AFR:
                return "v3/Rail/AFR"
            case RailOperator.INTER_HSR:
                return "v2/Rail/THSR"
            case _:
                return "v2/Rail/Metro"
    
# ===============
# MARK: - Spatial
# ===============
class Zone(IdEnum):
    """All available zones for TDX API."""
    KEELUNG_CITY    = ("KEE", "Keelung City") 
    """基隆市"""
    TAIPEI          = ("TPE", "Taipei City")
    """台北市"""
    NEW_TAIPEI      = ("NWT", "New Taipei City")
    """新北市"""
    TAOYUAN         = ("TAO", "Taoyuan City")
    """桃園市"""
    HSINCHU_CITY    = ("HSZ", "Hsinchu City")
    """新竹市"""
    HSINCHU         = ("HSQ", "Hsinchu County")
    """新竹縣"""
    MIAOLI          = ("MIA", "Miaoli County")
    """苗栗縣"""
    TAICHUNG        = ("TXG", "Taichung City")
    """台中市"""
    CHANGHUA        = ("CHA", "Changhua County")
    """彰化縣"""
    NANTOU          = ("NAN", "Nantou County")
    """南投縣"""
    YUNLIN          = ("YUN", "Yunlin County")
    """雲林縣"""
    CHIAYI_CITY     = ("CYI", "Chiayi City")
    """嘉義市"""
    CHIAYI          = ("CYQ", "Chiayi County")
    """嘉義縣"""
    TAINAN          = ("TNN", "Tainan City")
    """台南市"""
    KAOHSIUNG       = ("KHH", "Kaohsiung City")
    """高雄市"""
    PINGTUNG        = ("PIF", "Pingtung County")
    """屏東縣"""
    YILAN           = ("ILA", "Yilan County")
    """宜蘭縣"""
    HUALIEN         = ("HUA", "Hualien County")
    """花蓮縣"""
    TAITUNG         = ("TTT", "Taitung County")
    """台東縣"""
    PENGHU          = ("PEN", "Penghu County")
    """澎湖縣"""
    KINMEN          = ("KIN", "Kinmen County")
    """金門縣"""
    LIENCHIANG      = ("LIE", "Lienchiang County")
    """連江縣"""
    INTERZONES      = ("InterCity", "Intercity")
    """跨縣市(公路客運)"""

    @property
    def api_tag_city(self) -> str:
        """TDx API usage."""
        return self.value.replace(" ", "").removesuffix("City")

    @property
    def switch_to_ambiguous(self) -> "Zone":
        """Return the ambiguous zone for this zone, if applicable."""
        match self:
            case Zone.TAIPEI:
                return self.NEW_TAIPEI
            case Zone.NEW_TAIPEI:
                return Zone.TAIPEI
            case Zone.HSINCHU_CITY:
                return Zone.HSINCHU
            case Zone.HSINCHU:
                return Zone.HSINCHU_CITY
            case Zone.CHIAYI_CITY:
                return Zone.CHIAYI
            case Zone.CHIAYI:
                return Zone.CHIAYI_CITY
            case _:
                return self

    @property
    def isAmbiguous(self) -> bool:
        return self != self.switch_to_ambiguous
    
    def isAvailable(self, vehicle: VEHICLE_TYPE) -> bool:
        """Check if the zone is available for a specific vehicle type."""
        if vehicle not in VEHICLES:
            raise ValueError(f"Invalid vehicle type: {vehicle}. Must be {', '.join(VEHICLES)}.")
        unrail_zones = [
            Zone.PENGHU,
            Zone.KINMEN,
            Zone.LIENCHIANG
        ]
        unbike_zones = [
            Zone.KEELUNG_CITY,
            Zone.NANTOU,
            Zone.YILAN,
            Zone.HUALIEN,
            Zone.PENGHU,
            Zone.KINMEN,
            Zone.LIENCHIANG
        ]
        match vehicle:
            case "Rail" if self in unrail_zones:
                return False
            case "Bike" if self in unbike_zones:
                return False
            case _:
                return True

    @property
    def rail_operators(self) -> list[RailOperator] | None:
        """
        Get the available operators for a specific vehicle type in this zone.

        Returns
        -------
        list[RailOperator]
            A list of rail operators available in this zone.
        """
        hsr_zones = [
            Zone.TAIPEI,    Zone.NEW_TAIPEI,
            Zone.TAOYUAN,   Zone.HSINCHU,
            Zone.MIAOLI,    Zone.TAICHUNG,
            Zone.CHANGHUA,  Zone.YUNLIN,
            Zone.CHIAYI,    Zone.TAINAN,
            Zone.KAOHSIUNG, Zone.INTERZONES
        ]
        afr_zones = [
            Zone.CHIAYI,    Zone.CHIAYI_CITY
        ]
        if self.isAvailable("Rail"):
            services = [RailOperator.INTER_TRC]
            if self in hsr_zones:
                services.append(RailOperator.INTER_HSR)
            if self in afr_zones:
                services.append(RailOperator.INTER_AFR)
            # Metros
            if self in [Zone.TAIPEI, Zone.NEW_TAIPEI]:
                services.append(RailOperator.METRO_TPE)
                services.append(RailOperator.METRO_NTP)
                services.append(RailOperator.METRO_TAO)
            if self is Zone.TAOYUAN:
                services.append(RailOperator.METRO_TAO)
            if self is Zone.TAICHUNG:
                services.append(RailOperator.METRO_TXG)
            if self is Zone.KAOHSIUNG:
                services.append(RailOperator.METRO_KNN)
            return services

    def hasRailService(self, operator: RailOperator) -> bool:
        """Check if the zone has rail service for a specific operator."""
        available_operators = self.rail_operators
        if available_operators is None:
            return False
        return operator in available_operators