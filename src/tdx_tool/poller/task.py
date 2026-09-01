# Dependencies
from dataclasses import dataclass
from datetime import datetime
from typing import TYPE_CHECKING, Callable, Generic, TypeVar
# Local imports
from .sink import Sink

if TYPE_CHECKING:
    # Imported for typing only, so `import tdx_tool.poller` does not pull the whole
    # tool tree (and pandas / geopandas through it).
    from ..tool.tdx_tool import TDX

T = TypeVar("T")

# A poll task's fetch function: given the shared facade, produce whatever the paired
# sink accepts (a DataFrame for `ParquetSink`, anything for `CallbackSink`).
FetchFn = Callable[["TDX"], T]


@dataclass(slots=True)
class PollTask(Generic[T]):
    """
    One recurring fetch job.

    Parameters
    ----------
    name : str
        Stable identifier. Used in logs and as the sink's partition key, so keep it
        filesystem-safe and unique within a `Poller`.
    fetch : Callable[[TDX], T]
        Called once per tick with the shared `TDX` facade. Returns whatever the paired
        sink accepts. Any exception it raises is caught by the `Poller`, recorded on
        the `PollResult`, and does not stop the loop.
    sink : Sink[T]
        Destination for each tick's result.

    Notes
    -----
    Static reference data on the tools is a `@cached_property`
    (``tdx.bus(...).routes``); realtime data is a plain method / property that
    re-fetches on every call (``tdx.bike(...).fetch_availability()``,
    ``tdx.bus(...).alert``). Poll tasks want the realtime kind — call it inside
    `fetch` so every tick gets fresh data.
    """
    name: str
    fetch: FetchFn[T]
    sink: Sink[T]


@dataclass(slots=True, frozen=True)
class PollResult:
    """
    Outcome of running one `PollTask` on one tick.

    Attributes
    ----------
    task_name : str
        The task this result belongs to.
    fetched_at : datetime
        UTC tick timestamp, shared by every task in the same tick.
    ok : bool
        True if `fetch` and `sink.write` both completed.
    rows : int | None
        `len(data)` when the result is sized, else None.
    error : BaseException | None
        The exception raised, when `ok` is False.
    duration_s : float
        Wall time spent on `fetch` + `sink.write`.
    """
    task_name: str
    fetched_at: datetime
    ok: bool
    rows: int | None = None
    error: BaseException | None = None
    duration_s: float = 0.0
