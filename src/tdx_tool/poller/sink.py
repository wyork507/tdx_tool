# Dependencies
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Protocol, TypeVar, runtime_checkable
import pandas as pd

T_contra = TypeVar("T_contra", contravariant=True)


# ==============
# MARK: Protocol
# ==============
@runtime_checkable
class Sink(Protocol[T_contra]):
    """
    Where a `PollTask`'s per-tick output goes.

    Methods
    -------
    write(task_name, fetched_at, data) -> None
        Called once per tick per task. May run on a worker thread, so either keep the
        implementation thread-safe or give each task its own sink instance.
    close() -> None
        Called once when the `Poller` shuts down. Flush / release resources here.
    """
    def write(self, task_name: str, fetched_at: datetime, data: T_contra) -> None: ...
    def close(self) -> None: ...


# ===================
# MARK: CallbackSink
# ===================
class CallbackSink:
    """
    Forwards each batch to a user function. Persists nothing on its own.

    Parameters
    ----------
    fn : Callable[[str, datetime, Any], None]
        Receives `(task_name, fetched_at, data)` every tick.

    Examples
    --------
    >>> seen = []
    >>> sink = CallbackSink(lambda name, ts, data: seen.append((name, ts, len(data))))
    """
    def __init__(self, fn: Callable[[str, datetime, Any], None]) -> None:
        self._fn = fn

    def write(self, task_name: str, fetched_at: datetime, data: Any) -> None:
        self._fn(task_name, fetched_at, data)

    def close(self) -> None:
        pass


# ==================
# MARK: ParquetSink
# ==================
class ParquetSink:
    """
    Appends each tick to a date-partitioned parquet tree:

        <root>/<task_name>/date=<YYYY-MM-DD>/<fetched_at:%Y%m%dT%H%M%SZ>.parquet

    Expects `data` to be a pandas DataFrame (call `.df` on a `Wrapper` inside the
    task). Uses `DataFrame.to_parquet`, which relies on pyarrow (already a project
    dependency).

    Parameters
    ----------
    root : Path | str
        Base directory. Created lazily on the first write.
    timestamp_column : str | None, default "fetched_at"
        Column stamped on every row with the tick time (UTC), so that a later
        `pandas.read_parquet(root / task_name)` yields a clean time series. Pass None
        to skip stamping.
    """
    def __init__(
        self,
        root: Path | str,
        *,
        timestamp_column: str | None = "fetched_at",
    ) -> None:
        self._root = Path(root)
        self._ts_col = timestamp_column

    def write(self, task_name: str, fetched_at: datetime, data: pd.DataFrame) -> None:
        if not isinstance(data, pd.DataFrame):
            raise TypeError(f"ParquetSink expects a pandas DataFrame, got {type(data)}.")
        frame = data if self._ts_col is None else data.assign(**{self._ts_col: fetched_at})
        part = self._root / task_name / f"date={fetched_at:%Y-%m-%d}"
        part.mkdir(parents=True, exist_ok=True)
        frame.to_parquet(part / f"{fetched_at:%Y%m%dT%H%M%SZ}.parquet", index=False)

    def close(self) -> None:
        pass
