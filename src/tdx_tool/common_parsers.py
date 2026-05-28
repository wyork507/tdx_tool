# Dependencies
from datetime import time, date
from functools import wraps
from logging import Logger
from tqdm.auto import tqdm
from typing import Callable, Any
from msgspec import Struct
import pandas as pd
import inspect
# Local imports
from .common_models import I18n, PointPosition, DataclassInstance

FieldsName = str

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
    
    def flat_struct(self,
        data: Struct | DataclassInstance,
        point_prefix: str | None = None,
        date_fields: list[FieldsName] | None = None,
        time_fields: list[FieldsName] | None = None,
        datetime_fields: list[FieldsName] | None = None,
        skip_fields: list[FieldsName] | None = None,
        rename_fields: dict[FieldsName, FieldsName] | None = None,
        convertors: dict[FieldsName, Callable[[Any], Any]] | None = None
    ) -> dict:
        """
        Flatten a Struct object into a dictionary.
        """
        result = {}
        if isinstance(data, Struct):
            keys = data.__struct_fields__
        else:
            keys = data.__dataclass_fields__.keys()
        
        for key in keys:
            # Speical fields handling
            if skip_fields and key in skip_fields:
                continue
            value = getattr(data, key)
            new_key = rename_fields[key] if rename_fields and key in rename_fields else key
            if key != "UpdateTime":
                if date_fields and key in date_fields:
                    result[new_key] = self.decode_date(value)
                    continue
                if time_fields and key in time_fields:
                    result[new_key] = self.decode_time(value)
                    continue
                if datetime_fields and key in datetime_fields:
                    result[new_key] = self.decoding_datetime(value)
                    continue
            
            # Normal fields handling
            if isinstance(value, I18n):
                result = {**result, **value.flat(new_key)}
            elif isinstance(value, PointPosition):
                if point_prefix:
                    result = {**result, **value.flat(new_key)}
                else:
                    result = {**result, **value.flat_without_prefix}
            elif key == "UpdateTime" and isinstance(value, str):
                result[new_key] = self.decoding_datetime(value)
            elif convertors and key in convertors:
                result[new_key] = convertors[key](value)
            else:
                result[new_key] = value
        return result
    
def with_tqdm(arg_names: list[str], desc: str = "Processing", unit: str = "it", pos: int = 0, **tqdm_kwargs):
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
    pos : int, optional
        The position of the tqdm progress bar when multiple bars are used, by default 0.
    **tqdm_kwargs
        Additional keyword arguments to pass to tqdm.
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
                        unit=unit,
                        position=pos,
                        **tqdm_kwargs
                    )
            return func(**bound.arguments)
        return wrapper
    return decorator