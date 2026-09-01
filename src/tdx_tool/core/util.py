# Dependencies
from functools import wraps
from tqdm.auto import tqdm
import inspect

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