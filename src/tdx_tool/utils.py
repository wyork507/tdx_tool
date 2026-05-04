from enum import Enum
import msgspec

TDX_URL = "https://tdx.transportdata.tw"
TDX_API_BASE = f"{TDX_URL}/api/basic/"
TDX_AUTH = f"{TDX_URL}/auth/realms/TDXConnect/protocol/openid-connect/token"

class I18n(msgspec.Struct):
    Zh_tw: str
    En: str

class BusRegion(Enum):
    Keelung     = 'Keelung'
    Taipei      = 'Taipei'
    New_Taipei  = 'NewTaipei'
    Taoyuan     = 'Taoyuan'
    HsinchuCity = 'Hsinchu'
    Hsinchu     = 'HsinchuCounty'
    Miaoli      = 'MiaoliCounty'
    Taichung    = 'Taichung'
    Changhua    = 'ChanghuaCounty'
    Nantou      = 'NantouCounty'
    Yunlin      = 'YunlinCounty'
    ChiayiCity  = 'Chiayi'
    Chiayi      = 'ChiayiCounty'
    Tainan      = 'Tainan'
    Kaohsiung   = 'Kaohsiung'
    Pingtung    = 'PingtungCounty'
    Yilan       = 'YilanCounty'
    Hualien     = 'HualienCounty'
    Taitung     = 'TaitungCounty'
    Penghu      = 'PenghuCounty'
    Kinmen      = 'KinmenCounty'
    Lienchiang  = 'LienchiangCounty'
    Intercity   = 'Intercity'
    
    @property
    def isCounty(self) -> bool:
        return self.value.endswith("County")
    
    @property
    def ambiguous_name(self) -> str | None:
        def _drop_others(lst: list[str], target: str) -> str:
            return [item for item in lst if item != target][0]
        
        match self.value:
            case "Hsinchu" | "HsinchuCounty":
                return _drop_others(["Hsinchu", "HsinchuCounty"], self.value)
            case "Chiayi" | "ChiayiCounty":
                return _drop_others(["Chiayi", "ChiayiCounty"], self.value)
            case "Taipei" | "NewTaipei":
                return _drop_others(["Taipei", "NewTaipei"], self.value)
            case _:
                return None

    