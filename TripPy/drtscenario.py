import pandas as pd
import geopandas as gpd
import numpy as np
from .scenario import Scenario


class DRTScenario(Scenario):
    def __init__(
        self,
        code: str | None = None,
        name: str | None = "my scenario",
        description: str | None = None,
        fleet_size: int = 0,
        trips_df: pd.DataFrame | None = None,
        legs_df: pd.DataFrame | None = None,
        links_df: pd.DataFrame | gpd.GeoDataFrame | None = None,
        network_df: gpd.GeoDataFrame | None = None,
    ):
        super().__init__(
            code, name, description, trips_df, legs_df, links_df, network_df
        )
        self.fleet_size = fleet_size

    def get_n_drt_rides(self) -> int:
        """
        Get the total number or trips containing drt
        """
        self._require_table("trips_df")

        # get number of trips that contain drt
        if "contains_drt" in list(self._trips_df.columns):
            n_rides = len(self._trips_df[self._trips_df["contains_drt"]])
        elif "all_modes" in list(self._trips_df.columns):
            n_rides = len(
                self._trips_df[
                    self._trips_df["all_modes"].str.contains(
                        self._settings["drt_mode"]
                    )
                ]
            )
        else:
            self._require_table("trips_df", ["main_mode"])
            n_rides = len(
                self._trips_df[
                    self._trips_df["main_mode"] == self._settings["drt_mode"]
                ]
            )
        return n_rides
    def get_eta(self,kind: str = "mean", quantile: int = 95) -> float | pd.DataFrame:
        """
        Get the ETA (mean, median or a other quantile) of all DRT-Trips

        Arguments:
        - `kind`: specify a ETA-variant or choose all for a Dataframe with all kinds of ETA
        - `kind`: Define a quantile for the ETA-quantile

        Columns:
        - `ETA`: ETA-KPI
        - `minutes`: minuetes of the ETA78

        """
        self._require_table('legs_df')

        drt_legs = self._legs_df[self._legs_df['mode'] == 'drt']

        if kind == 'mean':
            return drt_legs['waiting_time'].mean()/60
        if kind == 'median':
            return drt_legs['waiting_time'].median()/60
        if kind == 'quantile':
            return drt_legs['waiting_time'].quantile(quantile/100)/60
        if kind == 'min':
            return drt_legs['waiting_time'].min()/60
        if kind == 'max':
            return drt_legs['waiting_time'].max()/60
        
        elif kind == 'all':
            etas = []
            etas.append(self.get_eta('mean'))
            etas.append(self.get_eta('median'))
            etas.append(self.get_eta('quantile', quantile=quantile))
            etas.append(self.get_eta('min'))
            etas.append(self.get_eta('max'))
            
            eta_df = pd.DataFrame()
            eta_df['ETA'] = ['mean', 'median', f'{quantile} % quantile', 'min', 'max']
            eta_df['minutes'] = etas
            return eta_df
        else:
           raise ValueError("Wrong 'kind'. Choose 'mean', 'median', 'quantile', 'min', 'max' or 'all' to get all ETAs in a dataframe.")

        
    def get_eta_day(self, kind: str ='mean',time_interval: int = 60, quantile:int = 95) -> float | pd.DataFrame:
        """
        Mean, median, min, max or a specific quantile ETA per time index.

        Arguement

        """
        self._require_table('legs_df')

        drt_legs = self._legs_df[self._legs_df['mode'] == 'drt']
        drt_legs['waiting_time'] = drt_legs["waiting_time"]/60
        if kind == 'mean':
            eta_day = (self._add_time_indices(drt_legs, time_interval=time_interval)).groupby('time_index')['waiting_time'].mean().reset_index()
            return eta_day
        elif kind == 'median':
            eta_day = (self._add_time_indices(drt_legs, time_interval=time_interval)).groupby('time_index')['waiting_time'].median().reset_index()
            return eta_day
        elif kind == 'quantile':
            eta_day = (self._add_time_indices(drt_legs, time_interval=time_interval)).groupby('time_index')['waiting_time'].quantile(quantile/100).reset_index()
            return eta_day
        elif kind == 'min':
            eta_day = (self._add_time_indices(drt_legs, time_interval=time_interval)).groupby('time_index')['waiting_time'].min().reset_index()
            return eta_day
        elif kind == 'max':
            eta_day = (self._add_time_indices(drt_legs, time_interval=time_interval)).groupby('time_index')['waiting_time'].max().reset_index()
            return eta_day
        elif kind == 'all':
            eta_day = (self._add_time_indices(drt_legs, time_interval=time_interval)).groupby('time_index').agg(mean=('waiting_time', "mean"),
                median=('waiting_time', "median"),
                min=('waiting_time', "min"),
                max=('waiting_time', "max"),
                quantile=('waiting_time', lambda x: np.percentile(x, quantile ))).reset_index()
            eta_day.columns = ['time_index', 'mean', 'median', 'min','max', f'{quantile}% quantile']
            return eta_day
        else:
            raise ValueError("Wrong 'kind'. Choose 'mean', 'median', 'quantile', 'min', 'max' or 'all' to get all ETAs in a dataframe.")

    def get_drt_intermodal_analysis(self):

        # TODO: Docstring

        self._require_table("trips_df", ["trip_id", "legs_count"])
        self._require_table("legs_df", ["mode"])

        if "contains_drt" in list(self._trips_df.columns):
            drt_trip_ids = self._trips_df[self._trips_df["contains_drt"]]
        else:
            drt_trip_ids = list(
                self._legs_df[self._legs_df["mode"] == self._settings["drt_mode"]][
                    "trip_id"
                ].unique()
            )

        # Filter legs DataFrame to keep only legs belonging to trips with "drt" mode and filter out walk legs
        drt_legs_no_walk = self._legs_df.loc[
            self._legs_df["trip_id"].isin(drt_trip_ids) & self._legs_df["mode"]
            != "walk"
        ]
        drt_legs_no_walk["leg_number"] = (
            drt_legs_no_walk.groupby("trip_id").cumcount() + 1
        )

        # First step is to find the number of the drt leg for each trip and to add legs_count
        drt_numbers = (
            drt_legs_no_walk[drt_legs_no_walk["mode"] == self._settings["drt_mode"]]
            .rename(columns={"leg_number": "drt_number"})
            .loc[:, ["trip_id", "drt_number"]]
            .merge(self._trips_df[["trip_id", "legs_count"]], how="left", on="trip_id")
        )

        # Second step is to filter the drt legs df (without walk) to only keep rows that have +- 1 delta to the drt leg number
        drt_adjacent_legs = drt_legs_no_walk.merge(drt_numbers, "left", "trip_id")

        # Below: only keep if drt_number equals 1 and legs_count also equals 1 => drt leg is the only leg
        # and also keep if the number of the leg minus the number of the drt leg equals -1 or 1 => leg is before or after drt leg
        drt_adjacent_legs = drt_adjacent_legs[
            (
                (drt_adjacent_legs["drt_number"]
                == 1) & (drt_adjacent_legs["legs_count"]
                == 1)
            )
            | (np.abs(drt_adjacent_legs["leg_number"] - drt_adjacent_legs["drt_number"])
            == 1)
        ]
        # Also add a column "order" to specify whether the leg is before or after (or it's a direct drt ride)
        drt_adjacent_legs["order"] = np.select([drt_adjacent_legs["leg_number"] == drt_adjacent_legs["drt_number"],
                                                drt_adjacent_legs["leg_number"] < drt_adjacent_legs["drt_number"],
                                                drt_adjacent_legs["leg_number"] > drt_adjacent_legs["drt_number"]
                                                ],
                                                ["direct", "before", "after"])
        
        # Last step is to group by mode and order and then count
        drt_intermodal = drt_adjacent_legs.groupby(["mode", "order"]).size().reset_index(name="n")
        
        return drt_intermodal

