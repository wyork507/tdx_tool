# Dependency imports
from logging import Logger
from typing import Literal, Callable, TypeVar, overload
from datetime import datetime
from requests import Response
from msgspec import Struct
import pandas as pd
import geopandas as gpd
import requests, os, logging, time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pyproj.exceptions import CRSError
# Local imports
from .authority import tdx_auth
from .utils import TDX_API_BASE as base_url

T = TypeVar("T", bound=Struct)
DataFrame = TypeVar("DataFrame", bound=pd.DataFrame|gpd.GeoDataFrame)

class tdx_tool:
    """
    **Do NOT use tdx_tool directly**. Use one of its subclasses for specific data retrieval.
    
    Subclasses list:
    - `tdx_bus`: For bus-related data
    - `tdx_rail`: For railway-related data
    - `tdx_bike`: For bike-sharing-related data
    
    General Attributes
    ------------------
    auth: tdx_auth
        an instance of `tdx_auth` for handling authentication
    logger: Logger
        a Logger instance for logging
    export_result: bool
        whether to export results
    default_coor: str, default="EPSG:4326"
        specifies the default coordinate reference system for geospatial data (default is WGS 84)
    output_path: str, default="output"
        the directory path where output files will be saved (default is "output")
    
    Output Formats
    --------------
    - For tabular data: csv(.csv), parquet(.parquet), json(.json)
    - For geospatial data: shapefile(.shp), geojson(.geojson)
    """
    FORM_OUTPUT_TYPE = Literal["csv", "parquet", "json"]
    """Supported output formats for tabular data."""
    GEOG_OUTPUT_TYPE = Literal["shapefile", "geojson"]
    """Supported output formats for geospatial data."""

    def __init__(self, client_id: str, client_key: str, logger: Logger | None = None):
        self.logger = logger or logging.getLogger(__name__)
        self.logger.debug("Initializing tdx_tool with provided client_id and client_key")
        self.auth = tdx_auth(client_id=client_id, client_key=client_key, logger=self.logger) 
        self.__export_result = False
        self.__default_coor = "EPSG:4326" # WGS 84 - World Geodetic System 1984
        self.__output_path = "output"
    
    @classmethod
    def from_auth(cls, auth: tdx_auth, *args, **kwargs) -> "tdx_tool":
        return cls(client_id=auth.client_id, client_key=auth.client_key, logger=auth.logger)

    @property
    def auth_header(self) -> dict:
        return {"Authorization": f"Bearer {self.auth.token}", "Accept": "gzip"}
    
    @property
    def export_result(self) -> bool:
        return self.__export_result
    
    @export_result.setter
    def export_result(self, value: bool) -> None:
        if not isinstance(value, bool):
            self.logger.error(f"Invalid value for export_result: {value}. Must be a boolean.")
            raise ValueError("export_result must be a boolean value.")
        self.__export_result = value
        self.logger.info(f"Set export_result to {value}")
    
    @property
    def default_coor(self) -> str:
        return self.__default_coor
    
    @default_coor.setter
    def default_coor(self, value: str) -> None:
        import pyproj
        try:
            pyproj.CRS(value) # Make sure the provided CRS string is valid
        except CRSError as e:
            self.logger.error(f"Invalid coordinate reference system: {value}. Error: {e}")
            raise ValueError(f"Invalid coordinate reference system: {value}. Please provide a valid CRS string (e.g., 'EPSG:4326').")
        self.__default_coor = value
        self.logger.info(f"Set default_coor to {value}")
    
    @property
    def output_path(self) -> str:
        return self.__output_path
    
    @output_path.setter
    def output_path(self, value: str) -> None:
        if not isinstance(value, str):
            self.logger.error(f"Invalid value for output_path: {value}. Must be a string.")
            raise ValueError("output_path must be a string value.")
        try:
            os.makedirs(value, exist_ok=True) # Ensure the directory exists
        except Exception as e:
            self.logger.error(f"Error occurred while creating output directory: {e}")
            raise e
        self.__output_path = value
        self.logger.info(f"Set output_path to {value}")

    def _get_data_from_suffix_url(self,
        suffix_url: str,
        params: dict | None = None,
        counter: int = 2
    ) -> requests.Response:
        """
        Parameters
        ----------
        suffix_url: str
            The suffix part of the API endpoint URL to fetch data from (e.g., `v2/Bus/Route`).
        params: dict | None
            Optional dictionary of query parameters to include in the API request.
        counter: int, default=2
            The number of retry attempts remaining for handling rate limits and transient errors (default is 2).
        
        Raises
        ------
        requests.exceptions.Timeout
            No response received over 10 seconds while trying to fetch data from the API.
        requests.exceptions.HTTPError
            Non-successful HTTP status code received while trying to fetch data from the API.
            - 401 Unauthorized errors, the method will attempt to refresh the token and retry once before raising an exception.
            - 429 Too Many Requests errors, the method will implement an exponential backoff strategy, and retry up to 3 times
              before giving up and raising an exception.
            - For other types of HTTP errors, the method will retry once after a short delay before raising an exception.
        RuntimeError
            Failed to fetch data due to unknown reasons.
        """
        url = f"{base_url}{suffix_url}"
        self.logger.info(f"Making GET request to URL: {url}")
        response: requests.Response | None = None
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
                    if counter >= 0:
                        wait_time: int = 4**(-counter+2) # Exponential backoff: 16, 4, 1 seconds
                        self.logger.debug(f"Received 429 Too Many Requests. Waiting for {wait_time} seconds before retrying...")
                        time.sleep(wait_time)
                        self.logger.debug(f"Retrying ... ({counter} attempts left)")
                        return self._get_data_from_suffix_url(suffix_url, params, counter - 1)
                    else:
                        self.logger.error(f"Due to repeated 429 Too Many Requests, no more retries will be attempted for URL: {url}")
                        raise
                case _:
                    if counter >= 0: # For other types of errors, we can attempt a retry with a short delay
                        self.logger.debug(f"Failed due to: {e}. Waiting for 1 second before retrying...")
                        time.sleep(1)
                        self.logger.info(f"Retrying... ({counter} attempts left)")
                        return self._get_data_from_suffix_url(suffix_url, params, counter - 1)
                    self.logger.error(f"Error occurred while fetching data from {url}:\n\t{e}")
                    raise
        if response is None:
            raise RuntimeError(f"Failed to fetch data from {url}")
        return response

    def _url_middle_part(self) -> list[str]:
        raise NotImplementedError

    @overload
    def _fetch_combined_data(
        self,
        prefix: str,
        params: dict,
        decoder: Callable[[Response], list[T]],
        parser: None = None,
    ) -> list[T]:
        ...

    @overload
    def _fetch_combined_data(
        self,
        prefix: str,
        params: dict,
        decoder: Callable[[Response], list[T]],
        parser: Callable[[list[T]], DataFrame],
    ) -> DataFrame:
        ...
    
    def _fetch_combined_data(
        self,
        prefix: str,
        params: dict,
        decoder: Callable[[Response], list[T]],
        parser: Callable[[list[T]], DataFrame] | None = None
    ) -> list[T] | DataFrame:
        """
        Fetch data from the API for the specified endpoint template and parameters.
        Uses concurrent requests to fetch data from multiple endpoints simultaneously.
        Handles pagination automatically for endpoints with large datasets.

        Parameters
        ----------
        prefix: str
            A string template for the API endpoint, with a placeholder for the middle part
            - example: `v2/Bus/Route`
        params: dict
            A dictionary of query parameters to include in the API request
        decoder: Callable[[Response], list[T]]
            A function to decode the API response into a pandas DataFrame
        parser: Callable[[list[T]], DataFrame] | None
            A function to parse the decoded data into a pandas DataFrame, or None to return the raw decoded data
        """
        data: list[T] = []
        
        def fetch_single_middle_part_with_pagination(middle_part: str) -> list[T]:
            """Fetch data for a single middle_part, handling pagination automatically."""
            result: list[T] = []
            top_size = 500 # Number of records to fetch per request
            skip = 0
            
            while True:
                suffix_url = f"{prefix}/{middle_part}?%24format=JSON"
                # Add pagination parameters
                request_params = params.copy() if params else {}
                request_params["$top"] = top_size
                request_params["$skip"] = skip
                
                self.logger.debug(f"Fetching data from URL: {suffix_url} (skip={skip}, top={top_size})")
                response = self._get_data_from_suffix_url(suffix_url, params=request_params)
                batch = decoder(response)
                
                result.extend(batch)
                
                # If we received fewer items than requested, we've reached the end
                if len(batch) < top_size:
                    break
                time.sleep(0.05)
                skip += top_size
            
            return result
        
        # Use ThreadPoolExecutor to fetch data concurrently
        with ThreadPoolExecutor(max_workers=5) as executor:
            futures = {
                executor.submit(fetch_single_middle_part_with_pagination, middle_part): middle_part 
                for middle_part in self._url_middle_part()
            }
            
            for future in as_completed(futures):
                try:
                    result = future.result()
                    data.extend(result)
                except Exception as e:
                    middle_part = futures[future]
                    self.logger.error(f"Error fetching data for {middle_part}: {e}")
                    raise
        
        if parser is None:
            return data
        else:
            return parser(data)
    
    @property
    def __timestamp(self) -> str:
        return datetime.now().strftime("%Y_%m-%d_%H:%M")
    
    def __check_path(self, path: str | None = None) -> str:
        path = path or self.__output_path
        if not isinstance(path, str):
            self.logger.error(f"Invalid value for output_path: {path}. Must be a string.")
            raise ValueError("output_path must be a string value.")
        os.makedirs(path, exist_ok=True)
        return path
    
    def __given_name(self,
        name: str | None,
        timestamp: bool
    ) -> str:
        if name is None:
            return f"data_{self.__timestamp}"
        elif timestamp:
            return f"{name}_{self.__timestamp}"
        else:
            return name
    
    def _save_to_file(self,
        datas: pd.DataFrame,
        dtype: FORM_OUTPUT_TYPE = "csv",
        name: str | None = None,
        path: str | None = None,
        timestamp: bool = True,
    ) -> None:
        path = self.__check_path(path)
        name = self.__given_name(name, timestamp)
        self.logger.debug(f"Ready to save data to file with name: {name} and type: {dtype}")
        output_path = os.path.join(path, f"{name}.{dtype}")
        match dtype:
            case "csv":
                datas.to_csv(output_path, index=False, encoding="utf-8")
            case "parquet":
                datas.to_parquet(output_path, index=False)
            case "json":
                datas.to_json(output_path, orient="records", force_ascii=False)
            case _:
                self.logger.error(f"Unsupported output type: {dtype}, output as csv by default.")
                return self.__save_to_file(datas, dtype="csv", name=name, path=path, timestamp=False)

    def _save_to_geofile(self,
        datas: gpd.GeoDataFrame,
        dtype: GEOG_OUTPUT_TYPE,
        name: str | None = None,
        path: str | None = None,
        timestamp: bool = True,
    ) -> None:
        path = self.__check_path(path)
        name = self.__given_name(name, timestamp)
        self.logger.debug(f"Ready to save geospatial data to file with name: {name} and type: {dtype}")
        output_path = os.path.join(path, f"{name}.{dtype}")
        match dtype:
            case "geojson":
                datas.to_file(output_path, driver="GeoJSON")
            case "shapefile":
                datas.to_file(output_path)
            case _:
                self.logger.error(f"Unsupported geospatial output type: {dtype}. Supported types are 'shapefile' and 'geojson'.")
                return self._save_to_geofile(datas, dtype="shapefile", name=name, path=path, timestamp=False)