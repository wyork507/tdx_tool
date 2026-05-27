# Dependencies
from datetime import time, date
from functools import wraps
from logging import Logger
from tqdm.auto import tqdm
import pandas as pd
import inspect

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
    
    def progress_bar(self, func, *args, **kwargs):
        with tqdm(*args, **kwargs) as pbar:
            return func(pbar)

def with_tqdm(arg_names: list[str], desc: str = "Processing", unit: str = "it"):
    """
    This is a decorator factory that creates a decorator to wrap functions with tqdm progress bars.

    Parameters
    ----------
    arg_names : list[str]
        which one or more arguments of the decorated function should be wrapped with tqdm. The argument must be an iterable.
    desc : str, default "Processing"
        left side text in the tqdm progress bar
    unit : str, optional
        The unit to display in the tqdm progress bar, by default "it".
    """
    def decorator(func): # the actual decorator
        @wraps(func) # to preserve the original function's metadata
        def wrapper(*args, **kwargs):
            sig = inspect.signature(func) # get the parameter names and default values (also called signature) of the original function
            bound = sig.bind(*args, **kwargs) # 
            bound.apply_defaults()
            for arg_name in arg_names:
                if arg_name in bound.arguments:
                    bound.arguments[arg_name] = tqdm(
                        bound.arguments[arg_name],
                        desc=desc,
                        unit=unit
                    )
            return func(*bound.args, **bound.kwargs)
        return wrapper
    return decorator