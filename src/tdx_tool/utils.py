# Dependencies
from dataclasses import dataclass
from enum import Enum
from functools import cached_property
from typing import Optional, Literal
# Local imports
from .bike_models import ServiceType
from .common_models import I18n, PointPosition, Identity

TDX_URL = "https://tdx.transportdata.tw"
TDX_API_BASE = f"{TDX_URL}/api/basic/"
TDX_AUTH = f"{TDX_URL}/auth/realms/TDXConnect/protocol/openid-connect/token"

ZONES: dict[str, Identity] = {
    "KEE": Identity("KEE", "基隆市", "Keelung City",     "Keelung"),
    "TPE": Identity("TPE", "台北市", "Taipei City",      "Taipei"),
    "NWT": Identity("NWT", "新北市", "New Taipei City",  "NewTaipei"),
    "TAO": Identity("TAO", "桃園市", "Taoyuan City",     "Taoyuan"),
    "HSZ": Identity("HSZ", "新竹市", "Hsinchu City",     "Hsinchu"),
    "HSQ": Identity("HSQ", "新竹縣", "Hsinchu County",   "HsinchuCounty"),
    "MIA": Identity("MIA", "苗栗縣", "Miaoli County",    "MiaoliCounty"),
    "TXG": Identity("TXG", "台中市", "Taichung City",    "Taichung"),
    "CHA": Identity("CHA", "彰化縣", "Changhua County",  "ChanghuaCounty"),
    "NAN": Identity("NAN", "南投縣", "Nantou County",    "NantouCounty"),
    "YUN": Identity("YUN", "雲林縣", "Yunlin County",    "YunlinCounty"),
    "CYI": Identity("CYI", "嘉義市", "Chiayi City",      "Chiayi"),
    "CYQ": Identity("CYQ", "嘉義縣", "Chiayi County",    "ChiayiCounty"),
    "TNN": Identity("TNN", "台南市", "Tainan City",      "Tainan"),
    "KHH": Identity("KHH", "高雄市", "Kaohsiung City",   "Kaohsiung"),
    "PIF": Identity("PIF", "屏東縣", "Pingtung County",  "PingtungCounty"),
    "ILA": Identity("ILA", "宜蘭縣", "Yilan County",     "YilanCounty"),
    "HUA": Identity("HUA", "花蓮縣", "Hualien County",   "HualienCounty"),
    "TTT": Identity("TTT", "台東縣", "Taitung County",   "TaitungCounty"),
    "PEN": Identity("PEN", "澎湖縣", "Penghu County",    "PenghuCounty"),
    "KIN": Identity("KIN", "金門縣", "Kinmen County",    "KinmenCounty"),
    "LIE": Identity("LIE", "連江縣", "Lienchiang County","LienchiangCounty")
}

def string_into_identity(region: str) -> Optional[Identity]:
    """
    ---
    Parameters:
        region: A string representing the region name, which can be in either Chinese or English.
    Returns:
        An Identity object corresponding to the region if a match is found, or None if no match
        is found.
    Raises:
        ValueError: If the input string does not match any known region names.
    """
    region_split = region.split()
    if region_split in [["New", "Taipei"]] or region.capitalize().startswith("NewTaipei"):
        return ZONES["NWT"] # Special case for "New Taipei"

    def get_regions(lang: Literal["zh", "en"]) -> dict[str, Identity]:
        regions = list(ZONES.values())
        data: dict[str, Identity] = {}
        for region in regions:
            data.update({
                getattr(region, lang): region
            })
        return data
    
    def replace_list(string: str, convert_list: dict[str, str]) -> str:
        for from_str, to_str in convert_list.items():
            if from_str in string:
                return string.replace(from_str, to_str)
        return string
    
    regions = [get_regions("en"), get_regions("zh")]
    # Convert the input region string to a standardized format for comparison
    region_split = region.split()
    target = replace_list(region_split[0].capitalize(), { # type: ignore
        "-": "",
        " ": "",
        "臺": "台"
    })

    # If the target matches a known region, initialize the class with that region. Otherwise, raise an error.
    for retion_dict in regions:
        if target in retion_dict:
            identity = retion_dict[target]
            return identity
    raise ValueError(f"Invalid region name: {region}. Valid options are: {', '.join(key for r in regions for key in r.keys())}.")

def strings_into_identities(regions: list[str], ignore_invalid: bool = False) -> list[Optional[Identity]]:
    identities: list[Optional[Identity]] = []
    for region in regions:
        try:
            identities.append(string_into_identity(region))
        except ValueError as e:
            if ignore_invalid:
                identities.append(None)
            else:
                raise e
    return identities

class BusRegion(Enum):
    """
    A enum for bus regions in Taiwan.
    """
    Keelung     = ZONES["KEE"]
    Taipei      = ZONES["TPE"]
    New_Taipei  = ZONES["NWT"]
    Taoyuan     = ZONES["TAO"]
    HsinchuCity = ZONES["HSZ"]
    Hsinchu     = ZONES["HSQ"]
    Miaoli      = ZONES["MIA"]
    Taichung    = ZONES["TXG"]
    Changhua    = ZONES["CHA"]
    Nantou      = ZONES["NAN"]
    Yunlin      = ZONES["YUN"]
    ChiayiCity  = ZONES["CYI"]
    Chiayi      = ZONES["CYQ"]
    Tainan      = ZONES["TNN"]
    Kaohsiung   = ZONES["KHH"]
    Pingtung    = ZONES["PIF"]
    Yilan       = ZONES["ILA"]
    Hualien     = ZONES["HUA"]
    Taitung     = ZONES["TTT"]
    Penghu      = ZONES["PEN"]
    Kinmen      = ZONES["KIN"]
    Lienchiang  = ZONES["LIE"]
    Intercity   = Identity("THB", "公路客運", "Intercity Bus",  "Intercity")

    @property
    def isCounty(self) -> bool:
        """
        Returns True if the region is a county (i.e., its name ends with "County"), False otherwise.
        """
        return self.value.api_tag.endswith("County")
    
    @property
    def code(self) -> str:
        """
        Returns the 3-digit code used in the prefix of UID encoding.
        """
        return self.value.code
    
    @property
    def names(self) -> list[str]:
        """
        The name of the region in both Chinese and English, used for display purposes.
        """
        return [self.value.zh, self.value.en]
    
    @property
    def api_tag(self) -> str:
        """
        Return the api_tag used in the TDX API endpoint URLs for this region.
        """
        return self.value.api_tag

    @cached_property
    def ambiguous_case(self) -> "BusRegion | None":
        """
        Returns the ambiguous region name if it exists.
        For example, *Hsinchu* and *HsinchuCounty* are ambiguous because they both contain *Hsinchu*.
        If there is no ambiguity, returns None.
        """
        ambiguos: dict[str, set[Identity]] = {
            "Hsinchu": set([ZONES["HSZ"], ZONES["HSQ"]]),
            "Chiayi":  set([ZONES["CYI"], ZONES["CYQ"]]),
            "Taipei":  set([ZONES["TPE"], ZONES["NWT"]])
        }
        name = self.value.en.split()[0]
        if name == "New":
            name = "Taipei"
        
        if name in ambiguos.keys():
            other_identity = (ambiguos[name] - set([self.value])).pop()
            for region in BusRegion:
                if region.value == other_identity:
                    return region
        return None

class BikeRegion(Enum):
    """
    A enum for bike regions in Taiwan.
    """
    Taipei      = ZONES["TPE"]
    New_Taipei  = ZONES["NWT"]
    Taoyuan     = ZONES["TAO"]
    HsinchuCity = ZONES["HSZ"]
    Hsinchu     = ZONES["HSQ"]
    Miaoli      = ZONES["MIA"]
    Taichung    = ZONES["TXG"]
    Changhua    = ZONES["CHA"]
    Yunlin      = ZONES["YUN"]
    ChiayiCity  = ZONES["CYI"]
    Chiayi      = ZONES["CYQ"]
    Tainan      = ZONES["TNN"]
    Kaohsiung   = ZONES["KHH"]
    Pingtung    = ZONES["PIF"]
    Taitung     = ZONES["TTT"]

    @property
    def bike_type(self) -> list[ServiceType]:
        match self:
            case BikeRegion.Changhua | BikeRegion.Yunlin:
                return [ServiceType.Moovo]
            case BikeRegion.Taipei:
                return [ServiceType.YouBike2, ServiceType.Moovo]
            case _:
                return [ServiceType.YouBike2]
    
    @property
    def api_tag(self) -> str:
        """
        Return the api_tag used in the TDX API endpoint URLs for this region.
        """
        return self.value.api_tag

class RailwayOperator(Enum):
    """
    A enum for railway operators in Taiwan.
    """
    INTER_TRC = Identity(
        "TRA",
        "臺灣鐵路股份有限公司",
        "Taiwan Railway Corporation",
        "TRA"
    )
    """
    If you are fetching data from TDx API, you would still receive the oudated details
    with `TRA` tag and the name of "臺灣鐵路管理局" (Taiwan Railway Administration).

    But the TRA was companilze and changed its name to Taiwan Railway Corporation in 2024,
    so I use the updated name and keep the api_tag in the code.
    """
    INTER_HSR = Identity(
        "THSR",
        "台灣高速鐵路股份有限公司",
        "Taiwan High Speed Rail Corporation",
        "THSR"
    )
    METRO_TPE = Identity(
        "TRTC",
        "臺北大眾捷運股份有限公司",
        "Taipei Rapid Transit Corporation",
        "TRTC"
    )
    METRO_NTP = Identity(
        "NTMC",
        "新北大眾捷運股份有限公司",
        "New Taipei Metro Corporation",
        "NTMC"
    )
    METRO_TAO = Identity(
        "TYMC",
        "桃園大眾捷運股份有限公司",
        "Taoyuan Metro Corporation",
        "TYMC"
    )
    METRO_TXG = Identity(
        "TMRT",
        "臺中捷運股份有限公司",
        "Taichung Mass Rapid Transit Corporation",
        "TMRT"
    )
    METRO_KNN = Identity(
        "KRTC",
        "高雄捷運股份有限公司",
        "Kaohsiung Rapid Transit Corporation",
        "KRTC"
    )

    @property
    def api_tag(self) -> str:
        """
        Return the api_tag used in the TDX API endpoint URLs for this railway operator.
        """
        return self.value.api_tag
    
    @property
    def isMetro(self) -> bool:
        if self.name.startswith("METRO"):
            return True
        else:
            return False

    @property
    def subRailSystem(self) -> dict[str, str] | None:
        """
        In TDx API, the metro systems might have multiple `RailSystem`s belonging to the same `RailwayOperator`.
        This property will only retrun that more than one `RailSystem` exists for the `RailwayOperator`.
        Otherwise, it will return None, and you can directly use the `api_tag` property for API calls.
        Retruns the `RailSystem`s that belong to the `RailwayOperator`
        """
        match self:
            case RailwayOperator.METRO_TPE:
                return {
                    "TRTCMG": "Maokong Gondola"
                }
            case RailwayOperator.METRO_NTP:
                return {
                    "NTMC": "New Taipei Metro",
                    "NTDLRT": "Danhai Light Rail",
                    "NTALRT": "Ankeng Light Rail"
                }
            case RailwayOperator.METRO_KNN:
                return {
                    "KLRT": "Kaohsiung Light Rail"
                }
            case _:
                return None
