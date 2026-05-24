# Dependencies
from abc import ABC, abstractmethod
from pathlib import Path
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Literal, Set, TypeVar, overload
from logging import Logger
import msgspec as ms
import logging
import signal
# Local imports
from .common_models import DataType, DataclassInstance, Identity
from .authority import tdx_auth
from .bus import tdx_bus as Bus
from .bike import tdx_bike as Bike
from .rail import tdx_rail as Rail
from .utils import BusRegion, BikeRegion, RailwayOperator, RailwayRegion

Engines = TypeVar("Engines", Bus, Bike, Rail)

class FetchTask(ABC):
    @property
    def name(self) -> str:
        """the prefix of the output file name, also used for logging and identification."""
        return self.__class__.__name__
    @abstractmethod
    def fetchs(self) -> list[ms.Struct | DataclassInstance]:
        """fetch data from TDX API, return a list of data items."""
        pass
    @abstractmethod
    def teardown(self) -> None:
        """perform any necessary cleanup after fetching data."""
        pass

class Poller:
    def __init__(self,
        client_id: str,
        client_key: str,
        data_path: Path,
        log_path: Path | None = None,
        interval: timedelta | None = None,
        end_time: datetime | None = None
    ):
        self.log_path = log_path or (data_path / "poller.log")
        self.logger = self._init_logger(self.log_path)
        try:
            tdx_auth(client_id, client_key, self.logger)()
        except RuntimeError:
            self.logger.fatal(f"Check your TDX API credentials")
            raise
        except Exception as e:
            self.logger.error(f"Failed to initialize TDX authentication: {e}")
            raise e
        try:
            data_path.mkdir(parents=True, exist_ok=True)
        except Exception as e:
            self.logger.fatal(f"Failed to create data directory at {data_path}: {e}")
            raise e        
        self.client_id = client_id
        self.client_key = client_key
        self.data_path = data_path
        self.interval = interval or timedelta(seconds=30)
        self.end_time = end_time or (datetime.now() + timedelta(hours=1))
        self.__tasks: list[FetchTask] = []
    
    @overload
    def add_engine(self, engine: Bus, region: BusRegion, together: bool = False) -> None:
        """
        Parameters
        ----------
        region: BusRegion
            The region for which to fetch bus data.
        together: bool, optional
            Whether to fetch all bus data together in one file or separate files for each region.
        """
        ...

    @overload
    def add_engine(self, engine: Bike, regions: list[BikeRegion]) -> None:
        """
        Parameters
        ----------
        regions: list[BikeRegion]
            A list of regions for which to fetch bike data.
        """
        ...
        
    @overload
    def add_engine(self, engine: Rail, operator: RailwayOperator) -> None:
        """
        Parameters
        ----------
        operator: RailwayOperator
            The railway operator for which to fetch rail data.
        """
        ...

    def add_engine(self, engine: Engines, *args, **kwargs) -> None:
        """
        Add a data-fetching engine to the poller with the specified parameters.

        Parameters
        ----------
        engine: Engines
            The data-fetching engine to add (e.g., Bus, Bike, Rail).
        """
        


    
    def _init_logger(self, log_path: Path) -> Logger:
        """Initialize the logger to write to the specified log file."""
        logger = logging.getLogger("TDXPoller")
        logger.setLevel(logging.DEBUG)
        if not logger.hasHandlers():
            formatter = logging.Formatter('%(asctime)s - [%(levelname)s] - %(message)s')
            file_handler = logging.FileHandler(log_path, encoding='utf-8')
            file_handler.setFormatter(formatter)
            stream_handler = logging.StreamHandler()
            stream_handler.setFormatter(formatter)
            logger.addHandler(file_handler)
            logger.addHandler(stream_handler)
        return logger
    
    def _setup_signals(self):
        def graceful_exit(signum, frame):


        