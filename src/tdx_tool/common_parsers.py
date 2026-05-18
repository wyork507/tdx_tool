# Dependencies
from datetime import time, date
from logging import Logger
import pandas as pd

class _parsers:
    def __init__(self, logger: Logger):
        self.logger = logger

    def decoding_datetime(self, dt_str: str) -> pd.Timestamp:
        return pd.to_datetime(
            dt_str
        )
    
    def decode_time(self, t_str: str | None) -> time | None:
        return pd.to_datetime(
            t_str,
            format = "%H:%M"
        ).time() if t_str else None
    
    def decode_date(self, date_str: str | None) -> date | None:
        return pd.to_datetime(
            date_str
        ).date() if date_str else None