# Dependencies
from logging import Logger
import pandas as pd
import geopandas as gpd
# Local imports
from ...core.parser import Parser
from .bike_models import Station, Availability

class BikeParsers(Parser):
    def __init__(self, crs: str, logger: Logger | None = None):
        super().__init__(crs, logger)
        
    # =====================
    # MARK: Stations Parser
    # =====================

    def parse_stations(self, stations: list[Station]) -> gpd.GeoDataFrame:
        """
        Parse a list of Station objects into a pandas DataFrame.
        """
        data = []
        for station in stations:
            data.append(self.flat_struct(station))
        df = pd.DataFrame(data).sort_values("StationUID").reset_index(drop=True)
        coor = df[["PositionLon", "PositionLat"]]
        return gpd.GeoDataFrame(
            df.drop(columns=["PositionLon", "PositionLat"]),
            geometry = gpd.points_from_xy(coor["PositionLon"], coor["PositionLat"]),
            crs = self.crs
        )
    
    # =========================
    # MARK: Availability Parser
    # =========================

    def parse_availability(self, availabilities: list[Availability]) -> pd.DataFrame:
        """
        Parse a list of Availability objects into a pandas DataFrame.
        """
        data = []
        for availablility in availabilities:
            base = self.flat_struct(availablility, skip_fields=["AvailableRentBikesDetail"])
            if availablility.AvailableRentBikesDetail:
                base = {**base, **self.flat_struct(availablility.AvailableRentBikesDetail)}
            data.append(base)
        return pd.DataFrame(data)
    
    # ==========================
    # MARK: Descriptions Parsers
    # ==========================
    
    def grouping_stations_by_size(self,
        stations: list[Station],
        bins: dict[str, tuple[int, int]]
    ) -> dict[str, list[Station]]:
        """
        """
        grouped = {key: [] for key in bins.keys()}
        for station in stations:
            capacity = station.BikesCapacity
            for key, (lower, upper) in bins.items():
                if lower <= capacity < upper:
                    grouped[key].append(station)
                    break
        return grouped

    def clustering_nearby_stations(self,
        stations: list[Station],
        distance: int,
        resolution: int = 20,
        window_factor: float = 3.5 
    ) -> dict[str,list[Station]]:
        """
        1. Convelute KDE (ρ)
        2. Running mean (ρ̄, background)
            - windowsize = window_factor * distance)
        3. Anomaly (ρ - ρ̄), and assign ≤ 0 one as isolated stations
        4. Calculate ∇ρ̄ and ∇²ρ̄ for > 0 anomaly stations each
        5. Find local maxima (∇²ρ̄ > 0) as a center of cluster
        6. Average the density along the circle of distance to each center (ρ̄_circle)
        7. Using ρ̄_circle as a threshold to assign other nearby stations to the center (tag it)
        8. If a station is multiple tagged, assign it by ∇ρ to the closing center
        9. If a station is not tagged, assign it as an isolated station (tag it as itself)
        10. For each cluster, using the largest bike capacity station as the ID of the cluster
        11. Return the clusters with their assigned stations, and the isolated stations as well.

        Parameters
        ----------
        stations: list[Station]
            List of Station objects to be clustered.
        distance: int
            The distance threshold for clustering.
        resolution: int, default=20
            The resolution for the clustering process.
        window_factor: float, default=3.5
            The factor for determining the window size.

        Returns
        -------
        dict[str, list[Station]]
            A dictionary where the keys are cluster labels and the values are lists of Station objects belonging to
        """

        # 先將行政區界以 buffer(distance) 的方式去填充 0 ，再用 convelution KDE 後，可以得到一個密度圖。
        # 再 running mean 一段距離(3~5\times distance)，得到一個大尺度的平均，之後去算 anomalies distribution。
        # 選出>0的站點，DBSCAN clustering，距離參數為 distance，min_samples 先設為 2~3，之後再調整。
        # 



        # sort
        return {}