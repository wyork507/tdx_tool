from enum import Enum

TDX_URL = "https://tdx.transportdata.tw"
TDX_API_BASE = f"{TDX_URL}/api/basic/"
TDX_AUTH = f"{TDX_URL}/auth/realms/TDXConnect/protocol/openid-connect/token"

class BusRegion(Enum):
    """
    This is an enumeration for bus regions in Taiwan.
    Use it to specify the region when initializing the `tdx_bus` class.

    Use Example:
    >>> bus_tool = tdx_bus(client_id="your_client_id", client_key="your_client_key", region=BusRegion.Taipei)
    """
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
        """
        Returns True if the region is a county (i.e., its name ends with "County"), False otherwise.
        """
        return self.value.endswith("County")
    
    @property
    def ambiguous_name(self) -> str | None:
        """
        Returns the ambiguous region name if it exists.
        For example, *Hsinchu* and *HsinchuCounty* are ambiguous because they both contain *Hsinchu*.
        If there is no ambiguity, returns None.
        """
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

    