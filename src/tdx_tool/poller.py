# Dependencies
from abc import ABC, abstractmethod
from pathlib import Path
from datetime import datetime, timedelta
from typing import Any, Callable, ClassVar, Set, TypeVar, overload
from logging import Logger
import msgspec as ms
import logging
import signal
# Local imports
from .common_models import DataclassInstance
from .authority import tdx_auth
from .bus import tdx_bus as Bus
from .bike import tdx_bike as Bike
from .rail import tdx_rail as Rail
from .utils import BusRegion, BikeRegion, RailwayOperator

Engines = Bus | Bike | Rail
TaskT = TypeVar('TaskT', bound='FetchTask')


class FetchTask(ABC):
    engine_cls: ClassVar[type[Bus] | type[Bike] | type[Rail] | None] = None
    engine_kwargs: ClassVar[dict[str, Any]] = {}
    engine: Engines

    @overload
    def __init_subclass__(
        cls,
        *,
        engine: type[Bus],
        region: BusRegion,
        together: bool = False,
    ) -> None:
        ...

    @overload
    def __init_subclass__(
        cls,
        *,
        engine: type[Bike],
        regions: list[BikeRegion],
    ) -> None:
        ...

    @overload
    def __init_subclass__(
        cls,
        *,
        engine: type[Rail],
        operator: RailwayOperator,
    ) -> None:
        ...

    @overload
    def __init_subclass__(cls) -> None:
        ...

    def __init_subclass__(
        cls,
        *,
        engine: type[Bus] | type[Bike] | type[Rail] | None = None,
        **engine_kwargs: Any,
    ) -> None:
        super().__init_subclass__()
        if engine is not None:
            cls.engine_cls = engine
            cls.engine_kwargs = engine_kwargs

    def bind_engine(self, poller: 'Poller') -> None:
        if self.engine_cls is None:
            raise ValueError(f"{self.__class__.__name__} does not define an engine_cls.")
        self.engine = poller.add_engine(self.engine_cls, **self.engine_kwargs)

    @property
    def name(self) -> str:
        return self.__class__.__name__

    @abstractmethod
    def fetchs(self) -> list[ms.Struct | DataclassInstance]:
        ...

    @abstractmethod
    def teardown(self) -> None:
        ...


@overload
def configure_task(*, engine: type[Bus], region: BusRegion, together: bool = False) -> Callable[[type[TaskT]], type[TaskT]]:
    """
    Make a FetchTask subclass that fetches bus data for a specific region.

    Parameters
    ----------
    engine: type[Bus]
        The bus data-fetching engine to use for this task.
    region: BusRegion
        The region for which to fetch bus data.
    together: bool, optional
        Whether to fetch all bus data together in one file or separate files for each region. Defaults to False.

    See Also
    --------
    - `tdx_bus` for more details on bus data-fetching engines and their configurations.
    """
    ...


@overload
def configure_task(*, engine: type[Bike], regions: list[BikeRegion]) -> Callable[[type[TaskT]], type[TaskT]]:
    """
    Make a FetchTask subclass that fetches bike data for specified regions.

    Parameters
    ----------
    engine: type[Bike]
        The bike data-fetching engine to use for this task.
    regions: list[BikeRegion]
        A list of regions for which to fetch bike data.
    
    See Also
    --------
    - `tdx_bike` for more details on bike data-fetching engines and their configurations.
    """
    ...


@overload
def configure_task(*, engine: type[Rail], operator: RailwayOperator) -> Callable[[type[TaskT]], type[TaskT]]:
    """
    Make a FetchTask subclass that fetches rail data for a specific railway operator.

    Parameters
    ----------
    engine: type[Rail]
        The rail data-fetching engine to use for this task.
    operator: RailwayOperator
        The railway operator for which to fetch rail data.
    
    See Also
    --------
    - `tdx_rail` for more details on rail data-fetching engines and their configurations.
    """
    ...


def configure_task(*, engine: type[Bus] | type[Bike] | type[Rail], **engine_kwargs: Any) -> Callable[[type[TaskT]], type[TaskT]]:
    """
    Use this for class-level, dataclass-like configuration when the engine type and its
    arguments are fixed by the task definition.
    """
    def decorator(cls: type[TaskT]) -> type[TaskT]:
        if not issubclass(cls, FetchTask):
            raise TypeError("@configure_task can only decorate subclasses of FetchTask")
        cls.engine_cls = engine
        cls.engine_kwargs = engine_kwargs
        return cls
    return decorator


class Poller:
    """
    A class responsible for managing data-fetching tasks from TDX API, including scheduling,
    logging, and graceful shutdown.
    
    Parameters
    ----------
    client_id: str
        The client ID for TDX API authentication.
    client_key: str
        The client key for TDX API authentication.
    data_path: Path
        The directory where fetched data will be stored.
    log_path: Path, optional
        The file path for logging. If not provided, defaults to `data_path/poller.log`.
    interval: timedelta, optional
        The time interval between consecutive data fetches. Defaults to 30 seconds.
    end_time: datetime, optional
        The time at which the poller should stop fetching data. Defaults to 1 hour from initialization.
    """
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
        self._engines: dict[tuple, Engines] = {} # key = (engine_cls, *args, **kwargs)
        self.__tasks: list[FetchTask] = []

    def add_task(self, task: FetchTask) -> None:
        task.bind_engine(self)
        self.__tasks.append(task)
    
    @overload
    def add_engine(self, engine: type[Bus], region: BusRegion, together: bool = False) -> Bus:
        """
        Add a bus data-fetching engine for a specific bus region.

        Parameters
        ----------
        engine: Bus
            The bus data-fetching engine to add.
        region: BusRegion
            The region for which to fetch bus data.
        together: bool, optional
            Whether to fetch all bus data together in one file or separate files for each region.
        
        Raises
        ------
        ValueError
            If no region/operator is specified for the engine.
        """
        ...

    @overload
    def add_engine(self, engine: type[Bike], regions: list[BikeRegion]) -> Bike:
        """
        Add a bike data-fetching engine for specified bike regions.

        Parameters
        ----------
        engine: Bike
            The bike data-fetching engine to add.
        regions: list[BikeRegion]
            A list of regions for which to fetch bike data.
        
        Raises
        ------
        ValueError
            If no region/operator is specified for the engine.
        """
        ...
        
    @overload
    def add_engine(self, engine: type[Rail], operator: RailwayOperator) -> Rail:
        """
        Add a rail data-fetching engine for a specific railway operator.

        Parameters
        ----------
        engine: Rail
            The rail data-fetching engine to add.
        operator: RailwayOperator
            The railway operator for which to fetch rail data.
        
        Raises
        ------
        ValueError
            If no region/operator is specified for the engine.
        """
        ...

    def add_engine(self, engine: type[Bus] | type[Bike] | type[Rail], *args, **kwargs) -> Engines:
        if engine is Bus:
            return self._add_bus_engine(*args, **kwargs)
        elif engine is Bike:
            return self._add_bike_engine(*args, **kwargs)
        elif engine is Rail:
            return self._add_rail_engine(*args, **kwargs)
        else:
            raise ValueError(f"Unsupported engine type: {engine}")
    
    def _add_bus_engine(self, region: BusRegion, together: bool = False) -> Bus:
        if not isinstance(region, BusRegion):
            raise ValueError(f"Invalid region type for Bus engine: expected BusRegion, got {type(region)}")
        if not isinstance(together, bool):
            raise ValueError(f"Invalid together flag type for Bus engine: expected bool, got {type(together)}")
        key = (Bus, region, together)
        if key not in self._engines:
            self._engines[key] = Bus(
                self.client_id,
                self.client_key,
                region,
                together,
                logger=self.logger
            )
        return Bus, self._engines[key] # type: ignore[return-value]
    
    def _add_bike_engine(self, regions: list[BikeRegion]) -> Bike:
        if not all(isinstance(region, BikeRegion) for region in regions):
            raise ValueError(f"Invalid region type for Bike engine: expected list of BikeRegion, got {type(regions)}")
        key = (Bike, frozenset(regions))
        if key not in self._engines:
            self._engines[key] = Bike(
                self.client_id,
                self.client_key,
                regions,
                logger=self.logger
            )
        return self._engines[key] # type: ignore[return-value]
    
    def _add_rail_engine(self, operator: RailwayOperator) -> Rail:
        if not isinstance(operator, RailwayOperator):
            raise ValueError(f"Invalid operator type for Rail engine: expected RailwayOperator, got {type(operator)}")
        key = (Rail, operator)
        if key not in self._engines:
            self._engines[key] = Rail(
                self.client_id,
                self.client_key,
                [operator],
                logger=self.logger
            )
        return self._engines[key] # type: ignore[return-value]
    
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
            self.logger.info("Received shutdown signal %s; tearing down engines.", signum)
            for task in self.__tasks:
                task.teardown()
            raise SystemExit(0)

        signal.signal(signal.SIGINT, graceful_exit)
        signal.signal(signal.SIGTERM, graceful_exit)