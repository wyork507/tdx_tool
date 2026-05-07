# Dependency imports
from logging import Logger
from typing import Literal
import pandas as pd
import geopandas as gpd
import requests
import os, logging
# Local imports
from .authority import tdx_auth

class tdx_tool:
    """
    Do NOT use tdx_tool directly. Use one of its subclasses for specific data retrieval.
    
    Subclasses list:
    - `tdx_bus`: For bus-related data
    - `tdx_railway`: For railway-related data
    
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
        if not isinstance(value, str):
            self.logger.error(f"Invalid value for default_coor: {value}. Must be a string.")
            raise ValueError("default_coor must be a string value representing a coordinate reference system (e.g., 'EPSG:4326').")
        self._default_coor = value
        self.logger.info(f"Set default_coor to {value}")


    def _get_data_from_suffix_url(self, suffix_url: str, params: dict | None = None, counter: int=2) -> requests.Response:
        from .utils import TDX_API_BASE as base_url
        import time
        url = f"{base_url}{suffix_url}"
        self.logger.info(f"Making GET request to URL: {url}")
        try:
            response = requests.get(url, headers=self.auth_header, params=params, timeout=10)
            self.logger.debug(f"Received response with status code: {response.status_code}")
            response.raise_for_status()
            return response
        except requests.RequestException as e:
            if counter > 0:
                self.logger.debug(f"Failed due to: {e}. Waiting for 1 second before retrying...")
                time.sleep(1)
                self.logger.info(f"Retrying... ({counter} attempts left)")
                return self._get_data_from_suffix_url(suffix_url, params, counter - 1)
            self.logger.error(f"Error occurred while fetching data from {url}:\n\t{e}")
            raise

    def _save_to_file(
        self,
        datas: pd.DataFrame | gpd.GeoDataFrame,
        dtype: FORM_OUTPUT_TYPE | GEOG_OUTPUT_TYPE,
        name: str,
        path: str = None,
        timestamp: bool = True
        ) -> None:

        def _generate_filename(prefix: str) -> str:
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
            name = f"{name}-{_generate_filename(name)}"
            
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