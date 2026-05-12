from dataclasses import dataclass
from enum import Enum
from functools import cached_property

TDX_URL = "https://tdx.transportdata.tw"
TDX_API_BASE = f"{TDX_URL}/api/basic/"
TDX_AUTH = f"{TDX_URL}/auth/realms/TDXConnect/protocol/openid-connect/token"

@dataclass
class Identity:
    code: str
    zh: str
    en: str
    api_tag: str

class BusRegion(Enum):
    """
    This is an enumeration for bus regions in Taiwan.
    Use it to specify the region when initializing the `tdx_bus` class.

    Use Example:
    >>> bus_tool = tdx_bus(client_id="your_client_id", client_key="your_client_key", region=BusRegion.Taipei)
    """
    Keelung     = Identity("KEE", "基隆市", "Keelung City",     "Keelung")
    Taipei      = Identity("TPE", "台北市", "Taipei City",      "Taipei")
    New_Taipei  = Identity("NWT", "新北市", "New Taipei City",  "NewTaipei")
    Taoyuan     = Identity("TAO", "桃園市", "Taoyuan City",     "Taoyuan")
    HsinchuCity = Identity("HSZ", "新竹市", "Hsinchu City",     "Hsinchu")
    Hsinchu     = Identity("HSQ", "新竹縣", "Hsinchu County",   "HsinchuCounty")
    Miaoli      = Identity("MIA", "苗栗縣", "Miaoli County",    "MiaoliCounty")
    Taichung    = Identity("TXG", "台中市", "Taichung City",    "Taichung")
    Changhua    = Identity("CHA", "彰化縣", "Changhua County",  "ChanghuaCounty")
    Nantou      = Identity("NAN", "南投縣", "Nantou County",    "NantouCounty")
    Yunlin      = Identity("YUN", "雲林縣", "Yunlin County",    "YunlinCounty")
    ChiayiCity  = Identity("CYI", "嘉義市", "Chiayi City",      "Chiayi")
    Chiayi      = Identity("CYQ", "嘉義縣", "Chiayi County",    "ChiayiCounty")
    Tainan      = Identity("TNN", "台南市", "Tainan City",      "Tainan")
    Kaohsiung   = Identity("KHH", "高雄市", "Kaohsiung City",   "Kaohsiung")
    Pingtung    = Identity("PIF", "屏東縣", "Pingtung County",  "PingtungCounty")
    Yilan       = Identity("ILA", "宜蘭縣", "Yilan County",     "YilanCounty")
    Hualien     = Identity("HUA", "花蓮縣", "Hualien County",   "HualienCounty")
    Taitung     = Identity("TTT", "台東縣", "Taitung County",   "TaitungCounty")
    Penghu      = Identity("PEN", "澎湖縣", "Penghu County",    "PenghuCounty")
    Kinmen      = Identity("KIN", "金門縣", "Kinmen County",    "KinmenCounty")
    Lienchiang  = Identity("LIE", "連江縣", "Lienchiang County","LienchiangCounty")
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
            "Hsinchu": set([BusRegion.Hsinchu.value, BusRegion.HsinchuCity.value]),
            "Chiayi":  set([BusRegion.Chiayi.value,  BusRegion.ChiayiCity.value]),
            "Taipei":  set([BusRegion.Taipei.value,  BusRegion.New_Taipei.value])
        }

        name = self.value.en.split()[0]
        if name in ambiguos.keys():
            return BusRegion(ambiguos[name] - set([self.value]))
        else:
            return None

class BikeRegion(Enum):


class RailwayOperator(Enum):
    INTER_TRC = Identity(
        "TRA",
        "臺灣鐵路股份有限公司",
        "Taiwan Railway Corporation",
        "TRA"
    )
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
    