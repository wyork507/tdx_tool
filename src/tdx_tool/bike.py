# Dependency imports
from collections.abc import Sequence
from datetime import datetime
from functools import cached_property
from pathlib import Path
from logging import Logger
from typing import Literal, overload
import msgspec, requests
import pandas as pd
import geopandas as gpd
# Local imports
from .authority import tdx_auth
from .bike_parsers import _bike_parsers
from .core import tdx_tool
from .utils import BikeRegion
from .bike_models import Station, Availability
from .detail_data_taipei import taipei_open_data

class tdx_bike(tdx_tool):
    """
    A class for fetching and processing bike-sharing data from the TDX API. This class provides methods to
    access bike station information, availability, and other related data for specified regions. It also
    includes functionality to refresh cached data and handle region-specific data fetching.
    
    Parameters
    ----------
    client_id: str
        TDX API Client ID (required)
    client_key: str
        TDX API Client Key (required)
    region: BikeRegion
        The region for which to fetch bike data. Must be specified as a `BikeRegion` enum value.
    logger: Logger, optional
        Logger instance for logging. If not provided, a default logger that does not output anywhere will be used.
    
    Attributes
    ----------
    auth: tdx_auth
        an instance of `tdx_auth` for handling authentication, see `tdx_auth` class for details.
    logger: Logger
        a Logger instance for logging
    export_result: bool
        whether to export results
    default_coor: str, default="EPSG:4326"
        specifies the default coordinate reference system for geospatial data (default is WGS 84)
    output_path: str, default="output"
        the directory path where output files will be saved (default is "output")
    regions: BikeRegion (read-only)
        where the bike data is fetched for
    stations: gpd.GeoDataFrame (cached)
        bike station information, such as name, location, capacity, etc.
    
    Methods
    -------
    fetch_availability() -> pd.DataFrame
        Fetch bike availability data for the specified region.
    """
    @overload
    def __new__(cls,
        client_id: str,
        client_key: str,
        regions: Sequence[Literal[BikeRegion.Taipei]],
        logger: Logger | None = None
    ) -> "tdx_bike_taipei_city": ...
    
    @overload
    def __new__(cls,
        client_id: str,
        client_key: str,
        regions: Sequence[BikeRegion] | None = None,
        logger: Logger | None = None
    ) -> "tdx_bike": ...

    def __new__(cls,
        client_id: str,
        client_key: str,
        regions: Sequence[BikeRegion] | None = None,
        logger: Logger | None = None,
    ) -> "tdx_bike | tdx_bike_taipei_city":
        if cls is tdx_bike:
            match regions:
                case [BikeRegion.Taipei]:
                    return object.__new__(tdx_bike_taipei_city)
                case None | []:
                    raise ValueError("Regions must be specified for `tdx_bike` enums.")
                case _:
                    return super().__new__(cls)
        else:
            return super().__new__(cls)

    def __init__(self,
        client_id: str,
        client_key: str,
        regions: Sequence[BikeRegion] | None = None,
        logger: Logger | None = None
    ):
        """
        Parameters
        ----------
        client_id: str
            TDX API Client ID (required)
        client_key: str
            TDX API Client Key (required)
        regions: Sequence[BikeRegion]
            The regions for which to fetch bike data. Must be specified as a `BikeRegion` enum value.
        logger: Logger, optional
            Logger instance for logging. If not provided, a default logger that does not output anywhere will be used.

        Raises
        ------
        ValueError
            If regions is not specified for `tdx_bike` enums.
        """
        super().__init__(client_id=client_id, client_key=client_key, logger=logger)
        if regions is None:
            raise ValueError("Regions must be specified for `tdx_bike` enums.")
        self.__regions = regions
        self.logger.debug(f"tdx_bike initialized for region(s): {', '.join(r.value.en for r in self.__regions)}")
        self._parsers = _bike_parsers(self.logger)
    
    @classmethod
    def from_region_str(cls,
        client_id: str,
        client_key: str,
        regions: list[str],
        skip_invalid: bool = False,
        logger: Logger | None = None
    ) -> "tdx_bike":
        """
        Factory method to create an instance of `tdx_bike` based on a region string.
        
        Parameters
        ----------
        client_id: str
            TDX API client ID.
        client_key: str
            TDX API client key.
        regions: list[str]
            The names of the regions to fetch bike data for. Must match one of the names in `BikeRegion`.
        skip_invalid: bool, default=False
            Whether to skip invalid region names.
        logger: Logger, optional
            Logger for debugging and information messages.
        """
        from .utils import strings_into_identities as convertor
        identities = []
        try:
            identities = convertor(regions, skip_invalid)
        except ValueError as e:
            raise e
        if skip_invalid and any(identity is None for identity in identities):
            record = list(zip(regions, identities))
            for region, identity in record:
                if identity is not None:
                    record.remove((region, identity))
            print(f"Warning: The following region names were invalid and have been skipped:")
            print(f"\t\t{', '.join(region for region, _ in record)}")
        return cls(
            client_id, client_key, [BikeRegion(identity) for identity in identities if identity is not None], logger=logger
        )
    
    @classmethod
    def from_auth(cls,
        auth: tdx_auth,
        regions: list[BikeRegion]
    ) -> "tdx_bike":
        """
        Factory method to create an instance of `tdx_bike` based on a `tdx_auth` instance and specified regions.
        
        Parameters
        ----------
        auth: tdx_auth
            An instance of `tdx_auth` containing authentication information.
        regions: BikeRegion 
        A list of `BikeRegion` enums specifying the regions to fetch bike data for.
        """
        return cls(auth.client_id, auth.client_key, regions, logger=auth.logger)
    
    @property
    def regions(self) -> Sequence[BikeRegion]:
        return self.__regions

    def _url_middle_part(self) -> list[str]:
        return [f"City/{region.api_tag}" for region in self.__regions]

    @cached_property
    def stations(self) -> gpd.GeoDataFrame:
        """
        """
        def decoder(response: requests.Response) -> list[Station]:
            return msgspec.json.decode(response.content, type=list[Station])
        
        data = self._fetch_combined_data(
            prefix="v2/Bike/Station",
            params={
                "$select": ','.join(Station.__struct_fields__),
            },
            decoder=decoder,
            parser=self._parsers.parse_stations
        ).sort_values("StationUID").reset_index(drop=True)
        coor = data[["PositionLon", "PositionLat"]]
        self.logger.debug(f"Creating GeoDataFrame with {len(data)} stations.")
        return gpd.GeoDataFrame(
            data.drop(columns=["PositionLon", "PositionLat"]),
            geometry = gpd.points_from_xy(coor["PositionLon"], coor["PositionLat"]),
            crs = self.default_coor
        )
    
    def fetch_availability(self) -> pd.DataFrame:
        """
        Fetch bike availability data for the specified region.
        """
        def decoder(response: requests.Response) -> list[Availability]:
            return msgspec.json.decode(response.content, type=list[Availability])
        
        return self._fetch_combined_data(
            prefix="v2/Bike/Availability",
            params={
                "$select": ','.join(Availability.__struct_fields__),
            },
            decoder=decoder,
            parser=self._parsers.parse_availability
        )

class tdx_bike_taipei_city(tdx_bike, taipei_open_data):
    """
    This class extends `tdx_bike`, specifically for Taipei City. Since Taipei City has
    more detailed bike data (e.g. OD data), you can create a instance for this by just
    specifying the region as Taipei when creating an instance of `tdx_bike`.
    >>> bike = tdx_bike(client_id, client_key, BikeRegion.Taipei)

    Attributes
    ----------
    od_data_detail: pd.DataFrame (cached)
        The available OD data list for Taipei City. Field includes:
    od_data_list: dict[str, str] (cached)
        A dict mapping the month to related file URL.
    
    Methods
    -------
    download_od_datas(months: list[str], overwrite: bool = False) -> list[Path]
        Download the OD data file for a specific month. The file will be downloaded and extracted to `output_path`.
    load_od_data(month: str, specify_folder: str | None = None, specify_filename: str | None = None) -> pd.DataFrame
        Load the OD data from a default or specified path.
    load_od_datas(months: list[str], specify_folder: str | None = None) -> pd.DataFrame
        Load multiple OD data files for the specified months.
    
    Notes
    -----
    - Do NOT directly create an instance of this class, use `tdx_bike` with Taipei region instead.
    - Keep the internet connection when using the download methods, and make sure you have enough storage space.
    
    See Also
    --------
    - `tdx_bike`: The parent class for fetching bike data from TDX API, which can be used for multiple regions.
    """
    def __init__(
        self,
        client_id: str,
        client_key: str,
        regions: list[BikeRegion] | None = None,
        logger: Logger | None = None,
    ):
        if regions is not None and regions != [BikeRegion.Taipei]:
            raise ValueError("`tdx_bike_taipei_city` only supports Taipei region.")
        tdx_bike.__init__(self, client_id, client_key, [BikeRegion.Taipei], logger=logger)
        taipei_open_data.__init__(self, logger=self.logger)
        self.output_path += "/taipei_bike_data"
        print(f"Some of methods will download files to {self.output_path}, chaning by setting `output_path` attribute.")
    
    @cached_property
    def od_data_detail(self) -> pd.DataFrame:
        """
        The available OD data list for Taipei City. Field includes:
        - Publisher: The publish organization.
        - Month: The month of the data (format: YYYYMM).
        - FileURL: The URL to download the data file.
        - UpdateTime: The time when the data was last updated.
        - SourceUpdateTime: The time when the data was last updated by the source.
        
        Returns
        -------
        pd.DataFrame
            A DataFrame containing the details of available OD data for Taipei City. 
        """
        def decoder(response: requests.Response) -> pd.DataFrame:
            return pd.DataFrame(
                response.json()["result"]["results"]
            )
        # Fetch the data list for bike OD data
        data = self._fetch_data_list(
            "1105750a-e8f5-4b89-9f7f-006493bb6de7",
            params = {
                "scope": "resourceAquire"
            },
            top_size=1000,
            decoder=decoder
        )[["發布機關名稱", "fileinfo", "fileurl", "updatetime", "srcupdatetime"]]
        # Rename columns for clarity and consistency
        data = data.rename(columns={
            "發布機關名稱": "Publisher",
            "fileinfo": "Month",
            "fileurl": "FileURL",
            "updatetime": "UpdateTime",
            "srcupdatetime": "SourceUpdateTime"
        })
        # Process the 'Month' column to extract the year and month in 'YYYY/MM' format
        data["Month"] = data["Month"].apply(lambda x: x[:-2])
        data.insert(1, "FileName",
            data["FileURL"].apply(lambda x: x.split("/")[-1])
        )
        # Sort by Month in descending order to have the most recent data at the top
        return data.sort_values("Month", ascending=False).reset_index(drop=True)
    
    @property
    def od_data_list(self) -> dict[str, str]:
        """
        Return a dict mapping the month to related file URL.
        
        Returns
        -------
        dict[str, str]
            A dictionary mapping each month to its corresponding file URL.
        """
        return dict(
            zip(
                self.od_data_detail["Month"],
                self.od_data_detail["FileURL"]
            )
        )
    
    def download_od_datas(self, months: list[str], overwrite: bool = False) -> list[Path]:
        """
        Download the OD data file for a specific month. The file will be downloaded and extracted to `output_path`.
        
        Parameters
        ----------
        months: list[str]
            A list of months for which to download data (format: YYYY/M).
        overwrite: bool, default=False
            Whether to overwrite the file if it already exists. Default is False.
        
        Returns
        -------
        list[Path]
            A list of folder paths where the files are downloaded.
        
        Raises
        --------
        ValueError
            If the specified month is not found in the OD data list.
        FileExistsError
            If the file already exists and overwrite is set to False.
        HttpError
            If there is an HTTP error during the download process.
        """
        if not all(month in self.od_data_list.keys() for month in months):
            self.logger.error(f"One or more specified months are not found in the OD data list: {months}. Available months: {list(self.od_data_list.keys())}")
            raise ValueError(f"One or more specified months are not found in the OD data list: {months}. Please check the available months in `od_data_list`.")
        try:
            return self._download_files(
                self.od_data_detail[self.od_data_detail["Month"].isin(months)],
                save_folder=self.output_path,
                overwrite=overwrite
            )
        except ValueError as e:
            self.logger.error(f"No data found for the specified month: {months}. Please check the available months in `od_data_detail`.")
            raise KeyError(e.add_note(f"{months}"))
        except FileExistsError as e:
            self.logger.error(f"File already exists for '{months}': {str(e)}")
            raise e
        except requests.HTTPError as e:
            self.logger.error(f"HTTP error occurred while downloading OD data for '{months}': {str(e)}")
            raise e
        
    def load_od_data(self, month: str, specify_folder: str | None = None, specify_filename: str | None = None) -> pd.DataFrame:
        """
        Load the OD data from a default or specified path.
        
        Parameters
        ----------
        month: str
            The month of the data to load (format: YYYYMM).
        specify_folder: str | None, default=None
            The folder containing the CSV file with the OD data. If None, the default folder will be used.
        specify_filename: str | None, default=None
            The name of the CSV file to load. If None, the default filename will be used (assumed to be the same as the downloaded file).
        Returns
        -------
        pd.DataFrame
            The loaded OD data.
        """
        # Confirm the month is valid
        if month not in self.od_data_list.keys():
            self.logger.warning(f"Specified month '{month}' does not match any available month in `od_data_list`")
            raise KeyError(f"Specified month '{month}' does not match any available month in `od_data_list`")
        # Determine the file path to load
        if specify_folder is not None and not Path(specify_folder).exists():
            self.logger.info(f"Specified folder '{specify_folder}' does not exist. Attempting to download the data for month '{month}' to the {self.output_path}.")
            self.download_od_datas([month], overwrite=False)
        folder_path = specify_folder if specify_folder is not None else self.output_path
        # Determine the path including filename to load
        if specify_filename is not None:
            file_path = Path(folder_path).joinpath(specify_filename)
            if not file_path.exists():
                raise FileNotFoundError(f"Specified file '{specify_filename}' does not exist in folder '{folder_path}'. Please check the filename and try again.")
        else:
            file_path = Path(folder_path).joinpath(self.od_data_detail[self.od_data_detail["Month"] == month]["FileName"].iloc[0])
        # Load the data
        try:
            data = pd.read_csv(file_path, encoding="utf-8", header=None)
        except UnicodeDecodeError:
            data = pd.read_csv(file_path, encoding="cp950") # big5 encoding extension
        except Exception as e:
            self.logger.error(f"Error occurred while loading OD data from '{file_path}': {str(e)}")
            raise e
        finally:
            self.logger.info(f"OD data for month '{month}' loaded successfully from '{file_path}'.")
        return data
    
    def load_od_datas(self, months: list[str], specify_folder: str | None = None) -> pd.DataFrame:
        """
        Load multiple OD data files for the specified months.
        Parameters
        ----------
        months: list[str]
            A list of months for which to load data (format: YYYYMM).
        specify_folder: str | None, default=None
            The folder containing the CSV files with the OD data. If None, the default folder will be used.
        Returns
        -------
        pd.DataFrame
            The loaded OD data.
        """
        pass

    
