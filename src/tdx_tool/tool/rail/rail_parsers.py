# Dependencies
from logging import Logger
import pandas as pd
import geopandas as gpd
import shapely
# Local imports
from ...core.parser import Parser
from .rail_models import *


class RailParsers(Parser):
    def __init__(self, crs: str, logger: Logger | None = None):
        super().__init__(crs, logger)

    