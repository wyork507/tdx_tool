# Dependencies
from dataclasses import dataclass, field
from logging import Logger
from random import random
from typing import Callable, TypeVar
from msgspec import Struct
from time import sleep
from concurrent.futures import ThreadPoolExecutor, as_completed
import msgspec
import requests
# Local imports
from .auth import Auth
from .constants import TDX_API_BASE
from .logger import get_logger

StructT = TypeVar("StructT", bound=Struct)

@dataclass(slots=True, frozen=True)
class Fetch:
    auth: Auth
    logger: Logger = field(init=False, default_factory=get_logger)
    
    def fetch_single(
        self,
        api: str,
        counter: int = 2,
        *,
        params: dict[str, str | int] | None = None
    ) -> requests.Response:
        """
        Fetch data from a single TDX API endpoint with retry logic.

        Parameters
        ----------
        api : str
            The TDX API endpoint to fetch data from.
        counter : int, optional; default=2
            The number of retry attempts in case of failure.
        params : dict[str, str | int], optional
            Additional query parameters to include in the request. Default is None.
        
        Returns
        -------
        requests.Response
            The response object from the successful API request.
        
        Raises
        ------
        requests.exceptions.RequestException
            If the request fails after the specified number of retries.
        """
        def handling_error(
            message: str,
            wait_time: int,
            *,
            reduce_counter: bool = True
        ) -> requests.Response:
            left_retries: int = counter - 1 if reduce_counter else counter 
            self.logger.warning(message)
            sleep(wait_time)
            return self.fetch_single(api, left_retries, params=params)
        # Main logic
        url = "/".join([TDX_API_BASE, api])
        response: requests.Response | None = None
        params = params if params is not None else {}
        self.logger.debug(f"Making GET request to {url} with params: {params}")
        try:
            response = requests.get(
                url,
                headers=self.auth.header,
                params=params,
                timeout=10
            )
            response.raise_for_status()
        except requests.exceptions.RequestException as e:
            code = getattr(e.response, "status_code", None)
            match code:
                case 401: # Unauthorized
                    return handling_error(
                        "401 Unauthorized, try to refresh token and retry.",
                        0,
                        reduce_counter = False
                    )
                case 429 if counter >= 0: # Too Many Requests
                    wait_time = int(4**(-counter+2)) # Wait 1 (for first retry), 4, 16 seconds respectively
                    return handling_error(
                        f"429 Too Many Requests, retrying in {wait_time} seconds. ({counter} retries left)",
                        wait_time
                    )
                case _:
                    if counter < 0:
                        self.logger.error(f"Too many retries for {code} error, giving up.")
                        raise e
                    return handling_error(
                        f"{code} error, retrying in 1 second. ({counter} retries left)\n{e}",
                        1
                    )
        if response is None:
            raise RuntimeError(f"Failed to fetch data from {url}.")
        return response

    def retrieve_data(
        self,
        api: str,
        schema: type[StructT],
        counter: int = 2,
        *,
        params: dict[str, str | int] | None = None,
        top_size: int = 500,
        custom_decoder: Callable[[requests.Response], list[StructT]] | None = None,
        _total_threads: int = 1
    ) -> list[StructT]:
        """
        Fetch data from a TDX API, decoding the response by the provided schema, and
        handling pagination.
        
        Parameters
        ----------
        api : str
            The TDX API endpoint to fetch data from.
        schema : type[StructT]
            (Msgspec Struct)
            The schema class to decode the response data into.
        counter : int, optional; default=2
            The number of retry attempts in case of failure.
        params : dict[str, str | int], optional
            Additional query parameters to include in the request. Default is None.
        top_size : int, optional; default=500
            The number of records to fetch per request. Default is 500.
        custom_decoder : Callable[[requests.Response], list[StructT]], optional
            A custom function to decode the response. If not provided, a default decoder
            using msgspec will be used.
        _total_threads : int, optional; default=1
            Internal, DO NOT USE.
        
        Returns
        -------
        list[StructT]
            A list of decoded data objects of type `StructT`.
        
        Raises
        ------
        requests.exceptions.RequestException
            If the request fails after the specified number of retries.
        """
        # Variables
        top_size = max(top_size, 500)
        skip = 0
        # Functions
        def default_decoder(response: requests.Response) -> list[StructT]:
            return msgspec.json.decode(response.content, type=list[schema])
        def no_next_batch(batch: list[StructT]) -> bool:
            """and with a little random delay"""
            if len(batch) < top_size:
                return True
            else:
                sleep(_total_threads/5+random()*0.1)                
            return False
        # Main logic
        decoder = custom_decoder if custom_decoder is not None else default_decoder
        params = params if params is not None else {}
        result: list[StructT] = []
        
        while True:
            self.logger.debug(f"Fetching data from {api} with skip={skip} and top={top_size}")
            response = self.fetch_single(
                api,
                counter=counter,
                params={
                    **params,
                    "$select": ",".join(schema.__struct_fields__),
                    "$top": top_size,
                    "$skip": skip,
                    "$format": "JSON"
                }
            )
            batch = decoder(response)
            result.extend(batch)
            if no_next_batch(batch):
                break
            skip += top_size
        self.logger.debug(f"Total records fetched from {api}: {len(result)}")
        return result

    def retrieve_datas(
        self,
        api: list[str],
        schema: type[StructT],
        counter: int = 2,
        *,
        params: dict[str, str | int] | None = None,
        top_size: int = 500,
        custom_decoder: Callable[[requests.Response], list[StructT]] | None = None
    ) -> list[StructT]:
        """
        Retrieve data from multiple APIs.

        Parameters
        ----------
        api : list[str]
            A list of API endpoints to fetch data from.
        schema : type[StructT]
            (Msgspec Struct)
            The schema class to decode the response data into.
        counter : int, optional; default=2
            The number of retry attempts in case of failure.
        params : dict[str, str | int], optional
            Additional query parameters to include in the request. Default is None.
        top_size : int, optional; default=500
            The number of records to fetch per request. Default is 500.
        custom_decoder : Callable[[requests.Response], list[StructT]], optional
            A custom function to decode the response. If not provided, a default decoder
            using msgspec will be used.

        Returns
        -------
        list[StructT]
            A list of decoded data objects of type `StructT`.

        Raises
        ------
        requests.exceptions.RequestException
            If the request fails after the specified number of retries.
        """
        results: list[StructT] = []
        with ThreadPoolExecutor() as executor:
            futures = [
                executor.submit(self.retrieve_data,
                    api=api_item,
                    schema=schema,
                    counter=counter,
                    params=params,
                    top_size=top_size,
                    custom_decoder=custom_decoder,
                    _total_threads=min(len(api), 5)
                )
                for api_item in api
            ]
            for future in as_completed(futures):
                try:
                    results.extend(future.result())
                except Exception as e:
                    self.logger.error(f"Error occurred while fetching data: {e}")
                    raise e
        return results

