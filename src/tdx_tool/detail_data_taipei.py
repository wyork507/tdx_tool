# Dependencies
from concurrent.futures import ThreadPoolExecutor, as_completed
from requests import Response
from zipfile import ZipFile
from io import BytesIO
from pathlib import Path
from logging import Logger
from typing import Callable
import requests
import pandas as pd
import time

BASE_URL = "https://data.taipei/api/v1/dataset/"

class taipei_open_data:
    def __init__(self, logger: Logger) -> None:
        if isinstance(logger, Logger):
            self.logger = logger
        else:
            raise TypeError("logger must be an instance of logging.Logger")

    def __fetch_taipei_data(self,
        suffix_url: str,
        params: dict | None = None,
        counter: int = 3
    ) -> requests.Response:
        url = f"{BASE_URL}{suffix_url}"
        response: requests.Response | None = None
        try:
            response = requests.get(
                url,
                params=params,
                timeout=10
            )
            response.raise_for_status()
        except requests.RequestException as e:
            match getattr(e.response, 'status_code', None):
                case 429: # Too Many Requests - rate limit exceeded
                    if counter > 0:
                        wait_time: int = 4**(-counter+2) # Exponential backoff: 16, 4, 1 seconds
                        self.logger.debug(f"Received 429 Too Many Requests. Waiting for {wait_time} seconds before retrying...")
                        time.sleep(wait_time)
                        self.logger.debug(f"Retrying ... ({counter} attempts left)")
                        return self.__fetch_taipei_data(suffix_url, params, counter - 1)
                    else:
                        self.logger.error(f"Due to repeated 429 Too Many Requests, no more retries will be attempted for URL: {url}")
                        raise
                case _:
                    if counter > 0: # For other types of errors, we can attempt a retry with a short delay
                        self.logger.debug(f"Failed due to: {e}. Waiting for 1 second before retrying...")
                        time.sleep(1)
                        self.logger.info(f"Retrying... ({counter} attempts left)")
                        return self.__fetch_taipei_data(suffix_url, params, counter - 1)
                    self.logger.error(f"Error occurred while fetching data from {url}:\n\t{e}")
                    raise
        if response is None:
            raise RuntimeError(f"Failed to fetch data from {url}")
        return response
    
    def _fetch_data_list(
        self,
        suffix_url: str,
        params: dict,
        top_size: int,
        decoder: Callable[[requests.Response], pd.DataFrame],
    ) -> pd.DataFrame:
        """
        Fetch data from the API for the specified endpoint template and parameters.
        Uses concurrent requests to fetch data from multiple endpoints simultaneously.
        Handles pagination automatically for endpoints with large datasets.

        Parameters
        ----------
        suffix_url : The API endpoint URL
        params : A dictionary of query parameters to include in the API request
        top_size : The number of records to fetch per request
        decoder : A function to decode the API response into a pandas DataFrame
        """
        data: pd.DataFrame = pd.DataFrame()
        skip = 0
        while True:
            requests_params = {
                "limit": top_size,
                "offset": skip
            }
            requests_params.update(params or {})
            self.logger.debug(f"Fetching data from URL: {suffix_url} (offset={skip}, limit={top_size})")
            response = self.__fetch_taipei_data(suffix_url, params=requests_params)
            batch = decoder(response)
            data = pd.concat([data, batch], axis=0, ignore_index=True)
            if len(batch) < top_size:
                break
            time.sleep(0.05)
            skip += top_size
        return data

    def _download_file_and_extract(self, data_detail: pd.Series, save_folder: str, overwrite: bool = False) -> Path:
        if data_detail.empty:
            raise ValueError("No data found for the specified month:")
        if Path(save_folder).joinpath(data_detail["FileName"]).exists() and not overwrite:
            raise FileExistsError(f"File '{data_detail['FileName']}' already exists in '{save_folder}'. Set overwrite=True to overwrite it.")
        response = requests.get(data_detail["FileURL"])
        response.raise_for_status()
        try:
            with ZipFile(BytesIO(response.content), metadata_encoding="utf-8") as zip_file:
                zip_file.extractall(save_folder)
        except UnicodeDecodeError:
            with ZipFile(BytesIO(response.content), metadata_encoding="cp950") as zip_file:
                zip_file.extractall(save_folder)
        return Path(save_folder)
    
    def _download_files(self, data_details: pd.DataFrame, save_folder: str, overwrite: bool = False) -> list[Path]:
        """
        Field including:
        -   `FileName`: The name of the file to be downloaded
        -   `FileURL`: The URL from which to download the file
        """
        paths: list[Path] = []
        with ThreadPoolExecutor() as executor:
            futures = {
                executor.submit(self._download_file_and_extract, row, save_folder, overwrite): row["FileName"]
                for _, row in data_details.iterrows()
            }
            for future in as_completed(futures):
                file_name = futures[future]
                try:
                    path = future.result()
                    paths.append(path)
                    self.logger.info(f"Successfully downloaded and extracted '{file_name}' to '{path}'")
                except Exception as e:
                    self.logger.error(f"Error downloading '{file_name}': {e}")
        return paths

    