import pandas as pd
import geopandas as gpd
import numpy as np
from .scenario import Scenario
from typing import Callable


class DRTScenario(Scenario):
    def __init__(
        self,
        code: str,
        name: str | None = "my scenario",
        description: str | None = None,
        fleet_size: int = 0,
        trips_df: pd.DataFrame | None = None,
        legs_df: pd.DataFrame | None = None,
        links_df: pd.DataFrame | gpd.GeoDataFrame | None = None,
        network_df: gpd.GeoDataFrame | None = None,
        line_renamer: Callable | dict | None = None,
    ):
        super().__init__(
            code,
            name,
            description,
            trips_df,
            legs_df,
            links_df,
            network_df,
            line_renamer,
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
            self._legs_df[self._legs_df["mode"] == "drt"]
            .melt(
                id_vars=["trip_id", "leg_id"],
                var_name="travel_part",
                value_name="minutes",
            )
            .groupby("travel_part"),
            "minutes",
        )

        return df_ttime

    def get_eta_day(self, time_interval: int | None = None) -> pd.DataFrame:
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

        #! Should only give back ETA, not all travel_parts
        # TODO: Maybe add back ability to get only one statistic -> also implement in Scenario.get_travel_time_stats()

        self._require_table("legs_df")

        df_with_time_index = self._add_time_indices(
            self._legs_df[self._legs_df["mode"] == "drt"], time_interval=time_interval
        ).melt(
            id_vars=["trip_id", "leg_id", "time_index"],
            var_name="travel_part",
            value_name="minutes",
        )

        grouped_df = df_with_time_index.query("travel_part == 'waiting_time'").groupby(
            ["time_index"]
        )

        df_ttime = Scenario.calc_descriptive_statistics(
            grouped_df,
            "minutes",
        )

        return df_ttime

    def get_drt_travel_time_stats(self):
        # TODO: Returns the travel time stats only for drt legs (not intermodal trips i.e. drt+pt combined)
        raise NotImplementedError

    def get_drt_intermodal_analysis(
        self,
        agg_modes_ruleset: str | None = None,
    ):
        # TODO: Docstring

        self._require_table("trips_df", ["trip_id", "legs_count"])
        self._require_table("legs_df", ["mode", "line_id"])

        if "contains_drt" in list(self._trips_df.columns):
            drt_trip_ids = self._trips_df[self._trips_df["contains_drt"]][
                "trip_id"
            ].unique()
        else:
            drt_trip_ids = list(
                self._legs_df[self._legs_df["mode"] == self._settings["drt_mode"]][
                    "trip_id"
                ].unique()
            )

        # Filter legs DataFrame to keep only legs belonging to trips with "drt" mode and filter out walk legs
        drt_legs_no_walk = self._legs_df.loc[
            (self._legs_df["trip_id"].isin(drt_trip_ids))
            & (self._legs_df["mode"] != self._settings["walk_mode"])
        ].copy()
        drt_legs_no_walk["leg_number"] = (
            drt_legs_no_walk.groupby("trip_id").cumcount() + 1
        )
        drt_legs_no_walk["legs_count"] = drt_legs_no_walk.groupby("trip_id")[
            "leg_number"
        ].transform("max")

        # First step is to find the number of the drt leg for each trip and to add legs_count
        drt_numbers = (
            drt_legs_no_walk[drt_legs_no_walk["mode"] == self._settings["drt_mode"]]
            .rename(columns={"leg_number": "drt_number"})
            .drop_duplicates(subset=["trip_id", "drt_number"])
        )[["trip_id", "drt_number"]]

        # Second step is to filter the drt legs df (without walk) to only keep rows that have +- 1 delta to the drt leg number#
        # (or exactly the drt leg number)
        drt_adjacent_legs = drt_legs_no_walk.merge(drt_numbers, "left", "trip_id")
        # Below: only keep if drt_number equals 1 and legs_count also equals 1 -> drt leg is the only leg
        # and also keep if the number of the leg minus the number of the drt leg equals -1 or 1 -> leg is before or after drt leg

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
                (drt_adjacent_legs["leg_number"] == drt_adjacent_legs["drt_number"]),
                (drt_adjacent_legs["leg_number"] < drt_adjacent_legs["drt_number"]),
                (drt_adjacent_legs["leg_number"] > drt_adjacent_legs["drt_number"]),
            ],
            ["direct", "before", "after"],
        )

        # Rename pt lines
        if self._line_renamer is not None:
            if isinstance(self._line_renamer, Callable):
                drt_adjacent_legs["line_id"] = drt_adjacent_legs.apply(
                    lambda row: self._line_renamer(row["line_id"], row["mode"]), axis=1
                )
            elif isinstance(self._line_renamer, dict):
                drt_adjacent_legs["line_id"] = drt_adjacent_legs["line_id"].replace(
                    self._line_renamer
                )
            else:
                raise ValueError(
                    f"`line_renamer` must be of type Callable or dict, not {type(self._line_renamer)}"
                )

        if agg_modes_ruleset is not None:
            drt_adjacent_legs["mode"] = drt_adjacent_legs["mode"].replace(
                self._settings["mode_aggregation_rulesets"][agg_modes_ruleset]
            )

        # Last step is to group by mode, line and order and then count
        drt_intermodal = (
            drt_adjacent_legs.fillna("EMPTY")
            .replace(self._settings["drt_mode"], "EMPTY")
            .groupby(["mode", "line_id", "order"])
            .size()
            .reset_index(name="n")
        )
        drt_intermodal = drt_intermodal.replace("EMPTY", None)

        return drt_intermodal

    def get_pooling_share(self) -> float:
        """
        Get the DRT person km/vehicle km ratio across the day (person km / vehicle km)
        ---
        """
        df_modal_split = self.get_modal_split(split_type="performance")
        try:
            person_km = df_modal_split[
                df_modal_split["mode"] == self._settings["drt_mode"]
            ]["n"].values[0]
        except IndexError as exc:
            raise ValueError(
                "No legs with DRT mode `"
                + self._settings["drt_mode"]
                + "` could be found. Make sure there are DRT legs in the legs_df and setting `drt_mode` is correctly specified"
            ) from exc

        df_veh_km = self.get_vehicle_km()
        try:
            vehicle_km = df_veh_km[df_veh_km["mode"] == self._settings["drt_mode"]][
                "n"
            ].values[0]
        except IndexError as exc:
            raise ValueError(
                "No vehicles with DRT mode `"
                + self._settings["drt_mode"]
                + "` could be found on any of the links. Make sure there are DRT vehicles routed on the links in the links_df and setting `drt_mode` is correctly specified"
            ) from exc

        return person_km / vehicle_km

    def get_drt_occupancy_day(
        self,
        time_interval: int = 60,
    ) -> pd.DataFrame:
        """
        Get a `DataFrame` containing the number of vehicles with a certain number of passengers currently aboard for each time bin across the day
        ---
        Arguments:
        - `time_interval`: number of seconds (!) one time bin consists of

        Columns of `DataFrame` returned:
        - `time_index`: index of the time interval bin. Example: if `time_interval` = 60 secs, there will be indices 0-1439 (with a day of 24 hours)
        - `occupancy`: number of passengers in the drt vehicle
        - `n`: number of vehicles entering at least one link in the respective time interval

        Notes:
        This is technically the number of unique passengers per vehicle in the time bin so with larger time intervals or on rare occasions, occupancy could exceed capacity and might not always be 100% correct.
        Also, if a vehicle is occupied but does not enter a new link during the time bin it will not be counted.
        """
        df_drt_links = self._links_df[
            self._links_df["mode"] == self._settings["drt_mode"]
        ].copy()
        df_drt_links["time_index"] = df_drt_links["link_enter_time"] // time_interval
        df_persons_per_vehicle_per_bin = (
            df_drt_links.groupby(["time_index", "vehicle_id"])["person_id"].nunique()
            - 1
        ).reset_index()
        df_occupancy = (
            df_persons_per_vehicle_per_bin.groupby(["time_index", "person_id"])
            .size()
            .reset_index(name="n")
            .rename(columns={"person_id": "occupancy"})
        )

        return df_occupancy
