# Dependencies
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from logging import Logger
from threading import Event, Thread
from time import monotonic
from typing import TYPE_CHECKING
# Local imports
from ..core.logger import get_logger
from .task import PollResult, PollTask

if TYPE_CHECKING:
    from datetime import timedelta
    from ..tool.tdx_tool import TDX


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _as_utc(dt: datetime) -> datetime:
    """Treat a naive datetime as UTC; leave an aware datetime alone."""
    return dt if dt.tzinfo is not None else dt.replace(tzinfo=timezone.utc)


class Poller:
    """
    Runs a set of `PollTask` jobs on a fixed interval until a stop condition trips.

    Scheduling is a plain monotonic-clock loop (no external scheduler), matching the
    repo's threads-and-`concurrent.futures` style. Each *tick* runs all tasks
    concurrently on a thread pool and writes every result through its sink. One task
    raising does not abort the tick or the loop — the error lands on its `PollResult`
    and is logged.

    Parameters
    ----------
    tdx : TDX
        Shared facade handed to every task. One `Auth` / `Fetch`, so the token cache
        and 429 back-off are shared across tasks.
    tasks : list[PollTask]
        Jobs to run each tick. Names must be unique.
    interval : timedelta
        Wall time between the *starts* of consecutive ticks. If a tick overruns, the
        next one starts immediately (logged as a warning) and the schedule realigns so
        drift stays bounded — the poller never tries to "catch up" missed ticks.
    until : datetime | None, optional
        Stop before starting a tick at or after this time. A naive datetime is treated
        as UTC. None means no time limit.
    max_ticks : int | None, optional
        Stop after this many ticks. None means no count limit.
    max_workers : int, default 4
        Thread-pool size for the per-tick fan-out.
    logger : Logger | None, optional
        Defaults to `get_logger("poller")`. The poller never adds handlers or sets
        levels — configure logging in your application.

    Attributes
    ----------
    last_results : list[PollResult]
        Results from the most recent tick.

    Examples
    --------
    >>> from datetime import timedelta, datetime, timezone
    >>> from tdx_tool import TDX
    >>> from tdx_tool.core import Region
    >>> from tdx_tool.poller import Poller, PollTask, ParquetSink
    >>> tdx = TDX(client_id, client_key)
    >>> tasks = [
    ...     PollTask(
    ...         "taipei_bike_availability",
    ...         lambda t: t.bike(Region.TAIPEI).fetch_availability().df,
    ...         ParquetSink("data/poll"),
    ...     ),
    ... ]
    >>> poller = Poller(tdx, tasks, interval=timedelta(seconds=30),
    ...                 until=datetime.now(timezone.utc) + timedelta(hours=1))
    >>> poller.run()                     # blocks until `until`

    Graceful Ctrl-C (the caller wires signals, not the library):

    >>> import signal
    >>> from threading import Event
    >>> stop = Event()
    >>> signal.signal(signal.SIGINT, lambda *_: stop.set())
    >>> poller.run(stop)
    """

    def __init__(
        self,
        tdx: "TDX",
        tasks: list[PollTask],
        *,
        interval: "timedelta",
        until: datetime | None = None,
        max_ticks: int | None = None,
        max_workers: int = 4,
        logger: Logger | None = None,
    ):
        if not tasks:
            raise ValueError("Poller needs at least one task.")
        if interval.total_seconds() <= 0:
            raise ValueError(f"interval must be positive, got {interval}.")
        names = [task.name for task in tasks]
        if len(set(names)) != len(names):
            raise ValueError(f"Task names must be unique, got {names}.")

        self._tdx = tdx
        self._tasks = list(tasks)
        self._interval = interval.total_seconds()
        self._until = _as_utc(until) if until is not None else None
        self._max_ticks = max_ticks
        self._max_workers = max_workers
        self.logger = logger if logger is not None else get_logger("poller")
        self._stop = Event()
        self.last_results: list[PollResult] = []

    # ---- control ---------------------------------------------------------

    def stop(self) -> None:
        """Ask the loop to exit after the current tick / wait. Thread-safe."""
        self._stop.set()

    def run(self, stop: Event | None = None) -> None:
        """
        Block, running ticks until one of these trips: `stop()` is called, the optional
        external `stop` Event is set, `until` is reached, or `max_ticks` ticks have
        run. Sinks are closed on the way out.

        Parameters
        ----------
        stop : threading.Event | None, optional
            An externally owned stop signal, checked alongside the internal one. Set it
            from your own SIGINT / SIGTERM handler for graceful shutdown.
        """
        bridge = self._bridge_external_stop(stop) if stop is not None else None
        try:
            tick = 0
            next_at = monotonic()
            while not self._should_stop(tick):
                self.last_results = self.tick_once()
                tick += 1

                next_at += self._interval
                slack = next_at - monotonic()
                if slack < 0:
                    self.logger.warning(
                        "Tick %d overran by %.1fs; next tick starts immediately.",
                        tick, -slack,
                    )
                    next_at = monotonic()                   # realign, do not catch up
                elif self._stop.wait(slack):
                    break                                   # interrupted during the wait

            self.logger.info("Poller finished after %d tick(s).", tick)
        finally:
            if bridge is not None:
                self._stop.set()                            # release the bridge thread
                bridge.join(timeout=1)
            self._close_sinks()

    def _bridge_external_stop(self, external: Event) -> Thread:
        """
        `Event.wait` can only block on one Event, so mirror an externally owned stop
        signal onto our internal one from a small daemon thread.
        """
        def _mirror() -> None:
            external.wait()
            self._stop.set()

        thread = Thread(target=_mirror, name="poll-stop-bridge", daemon=True)
        thread.start()
        return thread

    def _should_stop(self, tick: int) -> bool:
        if self._stop.is_set():
            self.logger.info("Poller stopped by request.")
            return True
        if self._max_ticks is not None and tick >= self._max_ticks:
            self.logger.info("Poller reached max_ticks=%d.", self._max_ticks)
            return True
        if self._until is not None and _utcnow() >= self._until:
            self.logger.info("Poller reached until=%s.", self._until.isoformat())
            return True
        return False

    # ---- one pass ------------------------------------------------------

    def tick_once(self) -> list[PollResult]:
        """
        Run every task once, concurrently, writing each result through its sink.
        Returns one `PollResult` per task and never raises for a single task's
        failure. Public so callers can drive the poller manually or exercise one pass.
        """
        fetched_at = _utcnow()
        results: list[PollResult] = []
        with ThreadPoolExecutor(
            max_workers=self._max_workers, thread_name_prefix="poll"
        ) as pool:
            futures = {
                pool.submit(self._run_task, task, fetched_at): task
                for task in self._tasks
            }
            for future in as_completed(futures):
                results.append(future.result())             # _run_task never raises

        for result in results:
            if result.ok:
                self.logger.info(
                    "[%s] ok - %s rows in %.2fs",
                    result.task_name,
                    "?" if result.rows is None else result.rows,
                    result.duration_s,
                )
            else:
                self.logger.error(
                    "[%s] failed in %.2fs: %r",
                    result.task_name, result.duration_s, result.error,
                )
        return results

    def _run_task(self, task: PollTask, fetched_at: datetime) -> PollResult:
        start = monotonic()
        try:
            data = task.fetch(self._tdx)
            task.sink.write(task.name, fetched_at, data)
            rows = len(data) if hasattr(data, "__len__") else None
            return PollResult(
                task.name, fetched_at, ok=True, rows=rows, duration_s=monotonic() - start
            )
        except Exception as e:                              # isolate one task's failure
            return PollResult(
                task.name, fetched_at, ok=False, error=e, duration_s=monotonic() - start
            )

    def _close_sinks(self) -> None:
        for task in self._tasks:
            try:
                task.sink.close()
            except Exception as e:                          # cleanup must not crash shutdown
                self.logger.warning("Closing sink for [%s] raised: %r", task.name, e)
