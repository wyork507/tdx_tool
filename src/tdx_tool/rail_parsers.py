# Dependencies
from logging import Logger
import pandas as pd
import geopandas as gpd
import shapely
# Local imports
from .rail_models import *
from .common_parsers import _parsers


class _rail_parsers(_parsers):
    def __init__(self, logger: Logger):
        super().__init__(logger)