# Dependency imports
from datetime import datetime
from functools import cached_property
from logging import Logger
from typing import Literal
import msgspec, requests
import pandas as pd
import geopandas as gpd
# Local imports
from .parsers import _bike_parsers
from .core import tdx_tool
from .utils import BikeRegion
from .bike_models import Station, Availability