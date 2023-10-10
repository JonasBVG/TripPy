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
                    self._trips_df["all_modes"].str.contains(self._settings["drt_mode"])
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

    def get_eta(self) -> pd.DataFrame:
        """
        Get a `DataFrame` containing a collection of travel time statistics for DRT
        ---

        Columns of `DataFrame` returned:
        - `travel_part`: part of travel time the minutes value stands for. Example: 'waiting'
        - `mean`: mean number of minutes
        - `median`: median number of minutes
        - `min`: minimum number of minutes
        - `max`: minimum number of minutes
        - `p_5`: fifth percentile
        - `p_95`: ninety-fifth percentile
        - `std`: standard deviation
        """
        self._require_table("legs_df")

        df_ttime = Scenario.calc_descriptive_statistics(
            self._legs_df[self._legs_df['mode'] == "drt"]
            .melt(
                id_vars=["trip_id", "stage_id"],
                var_name="travel_part",
                value_name="minutes",
            )
            .groupby("travel_part"),
            "minutes",
        )

        return df_ttime

    def get_eta_day(
        self, 
        time_interval: int | None = None
    ) -> pd.DataFrame:
        """
        Get a `DataFrame` containing DRT ETA statistics per time_index.
        ---
        
        Columns of `DataFrame` returned:
        - `time_index`: the time index calculated using _add_time_indices
        - `mean`: mean number of minutes
        - `median`: median number of minutes
        - `min`: minimum number of minutes
        - `max`: minimum number of minutes
        - `p_5`: fifth percentile
        - `p_95`: ninety-fifth percentile
        - `std`: standard deviation
        """
        # TODO: implement custom quantiles

        self._require_table("legs_df")

        df_with_time_index = self._add_time_indices(
            self._legs_df[self._legs_df['mode'] == "drt"]
            .melt(
                id_vars=["trip_id", "stage_id"],
                var_name="travel_part",
                value_name="minutes",
            )
            .groupby("travel_part"),
            time_interval=time_interval
        )
        
        grouped_df = df_with_time_index.groupby(["time_index", "travel_part"])
    
        df_ttime = Scenario.calc_descriptive_statistics(
            grouped_df,
            "minutes",
        )

        return df_ttime

    def get_drt_travel_time_stats(self):
        # TODO: Returns the travel time stats only for drt legs (not intermodal trips i.e. drt+pt combined)
        raise NotImplementedError

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
                (drt_adjacent_legs["drt_number"] == 1)
                & (drt_adjacent_legs["legs_count"] == 1)
            )
            | (
                np.abs(
                    drt_adjacent_legs["leg_number"] - drt_adjacent_legs["drt_number"]
                )
                == 1
            )
        ]
        # Also add a column "order" to specify whether the leg is before or after (or it's a direct drt ride)
        drt_adjacent_legs["order"] = np.select(
            [
                drt_adjacent_legs["leg_number"] == drt_adjacent_legs["drt_number"],
                drt_adjacent_legs["leg_number"] < drt_adjacent_legs["drt_number"],
                drt_adjacent_legs["leg_number"] > drt_adjacent_legs["drt_number"],
            ],
            ["direct", "before", "after"],
        )

        # Last step is to group by mode and order and then count
        drt_intermodal = (
            drt_adjacent_legs.groupby(["mode", "order"]).size().reset_index(name="n")
        )

        return drt_intermodal

    # TODO: Intermodal ratio of drt and pt (travel time, distance)