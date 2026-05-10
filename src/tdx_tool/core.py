# Dependency imports
from wsgiref.handlers import format_date_time
from logging import Logger
from typing import Literal, Optional, List, Callable
from datetime import datetime
from requests import Response
from msgspec import Struct
import pandas as pd
import geopandas as gpd
import requests, os, logging, time
# Local imports
from .authority import tdx_auth
from .utils import TDX_API_BASE as base_url

class tdx_tool:
    """
    Do NOT use tdx_tool directly. Use one of its subclasses for specific data retrieval.
    
    Subclasses list:
    - `tdx_bus`: For bus-related data
    - `tdx_rail`: For railway-related data
    - `tdx_bike`: For bike-sharing-related data
    ---
    General Attributes:
        auth: An instance of `tdx_auth` for handling authentication
        logger: Logger instance for logging
        export_result: Boolean indicating whether to export results
    """
    FORM_OUTPUT_TYPE = Literal["csv", "parquet", "json"]
    GEOG_OUTPUT_TYPE = Literal["shapefile", "geojson"]
    def __init__(self, client_id: str, client_key: str, logger: Logger | None = None):
        self.logger = logger or logging.getLogger(__name__)
        self.logger.debug("Initializing tdx_tool with provided client_id and client_key")
        self.auth = tdx_auth(client_id=client_id, client_key=client_key, logger=self.logger)
        self._export_result = True
        self._default_coor = "EPSG:4326" # WGS 84 - World Geodetic System 1984

    @property
    def auth_header(self) -> dict:
        return {"Authorization": f"Bearer {self.auth.token}", "Accept": "gzip"}
    
    @property
    def export_result(self) -> bool:
        return self._export_result
    
    @export_result.setter
    def export_result(self, value: bool) -> None:
        if not isinstance(value, bool):
            self.logger.error(f"Invalid value for export_result: {value}. Must be a boolean.")
            raise ValueError("export_result must be a boolean value.")
        self._export_result = value
        self.logger.info(f"Set export_result to {value}")
    
    @property
    def default_coor(self) -> str:
        return self._default_coor
    
    @default_coor.setter
    def default_coor(self, value: str) -> None:
        import pyproj
        try:
            pyproj.CRS(value) # Make sure the provided CRS string is valid
        except pyproj.exceptions.CRSError as e:
            self.logger.error(f"Invalid coordinate reference system: {value}. Error: {e}")
            raise ValueError(f"Invalid coordinate reference system: {value}. Please provide a valid CRS string (e.g., 'EPSG:4326').")
        self._default_coor = value
        self.logger.info(f"Set default_coor to {value}")

    def _get_data_from_suffix_url(
        self,
        suffix_url: str,
        params: dict | None = None,
        counter: int = 2
        ) -> requests.Response | None:
        url = f"{base_url}{suffix_url}"
        self.logger.info(f"Making GET request to URL: {url}")
        try:
            response = requests.get(
                url,
                headers=self.auth_header,
                params=params, timeout=10)
            self.logger.debug(f"Received response with status code: {response.status_code}")
            response.raise_for_status()
        except requests.RequestException as e:
            match getattr(e.response, 'status_code', None):
                case 401: # Unauthorized - likely token expired
                    self.logger.debug("Received 401 Unauthorized. Attempting to refresh token and retry...")
                    self.auth.update_token() # Refresh token
                    return self._get_data_from_suffix_url(suffix_url, params, counter) # Retry immediately after refreshing token
                case 429: # Too Many Requests - rate limit exceeded
                    if counter > 0:
                        wait_time: int = 4**(-counter+2) # Exponential backoff: 16, 4, 1 seconds
                        self.logger.debug(f"Received 429 Too Many Requests. Waiting for {wait_time} seconds before retrying...")
                        time.sleep(wait_time)
                        self.logger.debug(f"Retrying ... ({counter} attempts left)")
                        return self._get_data_from_suffix_url(suffix_url, params, counter - 1)
                    else:
                        self.logger.error(f"Due to repeated 429 Too Many Requests, no more retries will be attempted for URL: {url}")
                        raise
                case _:
                    if counter > 0: # For other types of errors, we can attempt a retry with a short delay
                        self.logger.debug(f"Failed due to: {e}. Waiting for 1 second before retrying...")
                        time.sleep(1)
                        self.logger.info(f"Retrying... ({counter} attempts left)")
                        return self._get_data_from_suffix_url(suffix_url, params, counter - 1)
                    self.logger.error(f"Error occurred while fetching data from {url}:\n\t{e}")
                    raise
        finally:
            return response
    
    def _fetch_combined_data(
        self,
        prefix: str,
        params: dict,
        decoder: Callable[Response, [Struct]],
        parser: Callable[[Struct], pd.DataFrame] | None = None
    ) -> List[Struct] | pd.DataFrame:
        """
        Fetch data from the API for the specified endpoint template and parameters.

        Parameters
        ----------
        prefix : A string template for the API endpoint, with a placeholder for the middle part
            example: `v2/Bus/Route`
        params : A dictionary of query parameters to include in the API request
        decoder : A function to decode the API response into a pandas DataFrame
        """
        data = []
        for middle_part in self._url_middle_part():
            suffix_url = f"{prefix}/{middle_part}?%24format=JSON"
            self.logger.debug(f"Fetching data from URL: {suffix_url}")
            response = self._get_data_from_suffix_url(suffix_url, params=params)
            data.extend(decoder(response))
        
        if parser is None:
            return data
        else:
            return parser(data)

    def _save_to_file(
        self,
        datas: pd.DataFrame | gpd.GeoDataFrame,
        dtype: FORM_OUTPUT_TYPE | GEOG_OUTPUT_TYPE,
        name: str,
        path: str = None,
        timestamp: bool = True
        ) -> None:

        def generate_filename(prefix: str) -> str:
            from datetime import datetime
            return datetime.now().strftime("%Y_%m%d_%H%M")

        path = path or "output"
        os.makedirs(path, exist_ok=True)
        
        match datas, dtype:
            case pd.DataFrame(), "csv" | "parquet" | "json":
                output_type = dtype
            case gpd.GeoDataFrame(), "shapefile" | "geojson":
                output_type = dtype
            case _:
                self.logger.error(f"Data type and output type mismatch: {type(datas)} cannot be saved as {dtype}")
                raise ValueError(f"Unsupported output type '{dtype}' for data type '{type(datas).__name__}'")

        if timestamp:
            name = f"{name}-{generate_filename(name)}"
            
        output_ext = {
            "shapefile": "shp",
            "geojson": "geojson",
        }.get(output_type, output_type)
        output_path = os.path.join(path, f"{name}.{output_ext}")
        
        match output_type:
            case "csv":
                datas.to_csv(output_path, index=False, encoding="utf-8")
            case "parquet":
                datas.to_parquet(output_path, index=False)
            case "json":
                datas.to_json(output_path, orient="records", force_ascii=False)
            case "geojson":
                datas.to_file(output_path, driver="GeoJSON")
            case _:
                datas.to_file(output_path)
        self.logger.info(f"Data saved to {output_path}")
        
    def __str__(self) -> str:
        return f"tdx_tool(auth=tdx_auth(client_id={self.auth.client_id}, token_expire_time={self.auth._expire_time}))"
    
    def __repr__(self) -> str:
        return self.__str__()