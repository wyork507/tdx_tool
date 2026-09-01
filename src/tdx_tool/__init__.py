"""Public interface for tdx_tool — a Python client for Taiwan's TDX transport API."""

# Entry point: TDX(client_id, client_key).bus(...) / .bike(...) / .rail(...) / .fetch
from .tool.tdx_tool import TDX

# Domain enums — pick one when calling TDX.bus/.bike/.rail
from .core.constants import Zone, RailOperator, BikeOperator

# Auth — only needed to share a token cache manually or inspect the token
from .core.auth import Auth

# Container returned by the tool data properties (.routes, .stations, ...)
from .core.wrapper import Wrapper

# Recurring fetch / polling
from .poller import (
    Poller,
    PollTask,
    PollResult,
    Sink,
    CallbackSink,
    ParquetSink,
)

__all__ = [
    "TDX",
    "Zone",
    "RailOperator",
    "BikeOperator",
    "Auth",
    "Wrapper",
    "Poller",
    "PollTask",
    "PollResult",
    "Sink",
    "CallbackSink",
    "ParquetSink",
]
