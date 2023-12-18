import json
import warnings
import numpy as np
import pandas as pd
import geopandas as gpd
from typing import Callable


class Scenario:
    """
    Class that models a transport planning scenario holding one or more different
    `(geo)pandas` `(Geo)DataFrames` containing data on trips, legs and/or network links
    """

    # TODO: Add methods for data to be used for visualizations like heatmaps and linestring stuff (precise coordinates)
    # TODO: Add ability to add a matsim timetable for the line related methods

    def __init__(
        self,
        code: str,
        name: str | None = "my scenario",
        description: str | None = None,
        operating_zone: gpd.GeoDataFrame | None = None,
        trips_df: pd.DataFrame | None = None,
        legs_df: pd.DataFrame | None = None,
        links_df: pd.DataFrame | gpd.GeoDataFrame | None = None,
        network_df: gpd.GeoDataFrame | None = None,
        line_renamer: Callable | dict | None = None,
        path_tables_specification: str = "tables_specification.json",  # TODO: Move to settings
    ):
        # TODO: Argument type checking
        # TODO: Docstring
        # TODO: Implement settings to be loaded from a json file as well

        self.code = code
        self.name = name
        self.description = description
        self._line_renamer = line_renamer
        self._operating_zone = operating_zone
        if self._operating_zone is not None:
            self._operating_zone = self._operating_zone.to_crs("epsg:4326")

        self._settings = {
            "default_time_agg_interval": 60,
            "drt_mode": "drt",
            "walk_mode": "walk",
            "crs": "epsg:25833",
            "pt_modes": [
                "100",
                "300",
                "500",
                "600",
                "700",
                "800",
                "BVB10",
                "BVB10M",
                "BVT30",
                "BVT30M",
                "BVB10X",
                "BVU20",
                "BVF100",
            ],
            # TODO: for release: replace with ".*"
            "person_id_filter": "^((?!^pt).)*$",  # only selects person_ids that do not start with "pt"
            # TODO: for release: replace with {}
            "mode_aggregation_rulesets": {
                "all_pt": {
                    "100": "ÖV",
                    "300": "ÖV",
                    "400": "ÖV",
                    "500": "ÖV",
                    "600": "ÖV",
                    "700": "ÖV",
                    "800": "ÖV",
                    "BVB10": "ÖV",
                    "BVB10M": "ÖV",
                    "BVT30": "ÖV",
                    "BVT30M": "ÖV",
                    "BVB10X": "ÖV",
                    "BVU20": "ÖV",
                    "BVF100": "ÖV",
                    "bike": "Fahrrad",
                    "car": "MIV",
                    "ride": "Mitfahren",
                    "walk": "Laufen",
                    "drt": "DRT",
                },
                "vsys": {
                    "100": "Bus",
                    "300": "Tram",
                    "400": "Fähre",
                    "500": "S-Bahn",
                    "600": "RV",
                    "700": "FV",
                    "800": "FV",
                    "BVB10": "Bus",
                    "BVB10M": "Bus",
                    "BVT30": "Tram",
                    "BVT30M": "Tram",
                    "BVB10X": "Bus",
                    "BVU20": "U-Bahn",
                    "BVF100": "Fähre",
                    "bike": "Fahrrad",
                    "car": "MIV",
                    "ride": "Mitfahren",
                    "walk": "Laufen",
                    "drt": "DRT",
                },
            },
        }

        with open(path_tables_specification, encoding="utf-8") as file:
            self._tables_specification = json.load(file)

        self._trips_df: pd.DataFrame = None
        self._legs_df: pd.DataFrame = None
        self._links_df: pd.DataFrame | gpd.GeoDataFrame = None
        self._network_df: gpd.GeoDataFrame = None

        self.add_data(trips_df=trips_df)
        self.add_data(legs_df=legs_df)
        self.add_data(links_df=links_df)
        self.add_data(network_df=network_df)

    def add_data(self, **kwargs) -> None:
        """
        Add data to the scenario via a `DataFrame` or `GeoDataFrame`
        ---
        Arguments:
        - `trips_df`: a `pandas` `DataFrame` containing at least one trip
        - `legs_df`: a `pandas` `DataFrame` containing at least one leg
        - `links_df`: a `pandas` `DataFrame` or a `geopandas` `GeoDataFrame` containing at least one link
        - `network_df`: a `GeoDataFrame` containing at least one link
        - `operating_zone`: a `GeoDataFrame` containing exactly one polygon which defines the operating zone
        """

        # TODO: It would probably make sense to create a (more versatile) method to also add ids/other information from a shape containing more than 1 polygon
        # TODO: ... for things like aggregating to zones instead of supplying the shape each time when using such a method

        def add_operating_zone_to_trips(trips_df: pd.DataFrame) -> pd.DataFrame:
            """
            Add information on origin and destination of trips using operating_zone
            ---
            Adds these columns:
            `starts_in_zone`: `True` if origin lies inside the operating zone, else `False`
            `ends_in_zone`: `True` if destination lies inside the operating zone, else `False`
            `relation_type`: "inland" if origin and destination lie inside the operating zone, "od" if either origin or destination falls inside the operating zone and "outside" if neither do
            """
            try:
                self._require_table("trips_df", ["from_x", "from_y", "to_x", "to_y"])
            except AssertionError:
                warnings.warn(
                    UserWarning(
                        "Could not add information on the operating zone to the trips_df because columns defining trip locations were missing (`from_x`, `from_y`, `to_x`, `to_y`)"
                    )
                )

            for col in ("relation_type", "starts_in_zone", "ends_in_zone"):
                if col in trips_df.columns:
                    trips_df = trips_df.drop(columns=col)

            gdf_points_from = (
                gpd.GeoDataFrame(
                    trips_df,
                    geometry=gpd.points_from_xy(trips_df["from_x"], trips_df["from_y"]),
                )
                .set_crs(self._settings["crs"])
                .to_crs(4326)
            )
            gdf_points_to = (
                gpd.GeoDataFrame(
                    trips_df,
                    geometry=gpd.points_from_xy(trips_df["to_x"], trips_df["to_y"]),
                )
                .set_crs(self._settings["crs"])
                .to_crs(4326)
            )

            # Check if 'from' and 'to' points are inside the polygon
            gdf_points_from["starts_in_zone"] = gdf_points_from["geometry"].within(
                self._operating_zone.geometry.iloc[0]
            )
            gdf_points_to["ends_in_zone"] = gdf_points_to["geometry"].within(
                self._operating_zone.geometry.iloc[0]
            )

            # Merge the results back into the original DataFrame
            df = pd.concat(
                [
                    trips_df,
                    gdf_points_from["starts_in_zone"],
                    gdf_points_to["ends_in_zone"],
                ],
                axis=1,
            )
            df["relation_type"] = "outside"
            df.loc[df["starts_in_zone"] | df["ends_in_zone"], "relation_type"] = "od"
            df.loc[
                df["starts_in_zone"] & df["ends_in_zone"], "relation_type"
            ] = "inland"

            return df

        for key, value in kwargs.items():
            if value is not None:
                if key == "trips_df" and self._check_specification_compliance(
                    value, "trips_df"
                ):
                    self._trips_df = value
                    if "trip_id" not in list(self._trips_df.columns):
                        self._trips_df["trip_id"] = self._trips_df.index.astype(str)

                    if self._operating_zone is not None:
                        self._trips_df = add_operating_zone_to_trips(self._trips_df)
                elif key == "operating_zone":
                    self._operating_zone = value.to_crs(4326)
                    self._trips_df = add_operating_zone_to_trips(self._trips_df)

                elif key == "legs_df" and self._check_specification_compliance(
                    value, "legs_df"
                ):
                    self._legs_df = value
                    if "leg_id" not in list(self._legs_df.columns):
                        self._legs_df["leg_id"] = self._legs_df.index.astype(str)
                    if "leg_number" not in list(self._legs_df.columns):
                        self._legs_df["leg_number"] = (
                            self._legs_df.groupby("trip_id").cumcount() + 1
                        )

                elif key == "links_df" and self._check_specification_compliance(
                    value, "links_df"
                ):
                    self._links_df = value
                    if "link_id" not in list(self._links_df.columns):
                        self._links_df["link_id"] = self._links_df.index.astype(str)

                elif key == "network_df" and self._check_specification_compliance(
                    value, "network_df"
                ):
                    self._network_df = value

                else:
                    raise TypeError(f"Unrecognized argument: {key}")

    def get_trips_df(self) -> pd.DataFrame:
        """
        Get the trips `DataFrame` stored in the scenario
        ---
        """
        self._require_table("trips_df")
        return self._trips_df

    def get_legs_df(self) -> pd.DataFrame:
        """
        Get the legs `DataFrame` stored in the scenario
        ---
        """
        self._require_table("legs_df")
        return self._legs_df

    def get_links_df(self) -> gpd.GeoDataFrame:
        """
        Get the links `DataFrame` stored in the scenario
        ---
        """
        self._require_table("links_df")
        return self._links_df

    def get_n_trips(self) -> int:
        """
        Get the total number of trips
        ---
        """
        # TODO: Add ability to filter spatially for a specific area, start/end.
        # Maybe create something like self.analysis_areas as GeoDataFrame of areas (Polygons) and specify only area name for this method to filter for

        self._require_table("trips_df")

        return self._trips_df.shape[0]

    def get_n_persons(self) -> int:
        """
        Get the number of unique persons
        ---
        """

        self._require_table("trips_df", ["person_id"])

        return self._trips_df["person_id"].unique().size

    def get_person_km(
        self, exclude_modes: list[str] = [], agg_modes_ruleset: str | None = None
    ) -> pd.DataFrame:
        """
        Get a `DataFrame` containing the total number of person kilometers performed per mode
        ---
        Arguments:
        - `exclude_modes`: specify a list of mode names to be disregarded. Note that these modes have to be supplied in the form they exist in the `links_df`, not any aggregated form
        - `agg_modes_ruleset`: which ruleset to use to aggregate the modes in the `links_df`. Has to be configured in the settings first (key `mode_aggregation_rulesets`)

        Columns of `DataFrame` returned:
        - `mode`: mode of transport
        - `n`: number of person kilometers performed
        """

        self._require_table("legs_df", ["person_id", "routed_distance", "mode"])

        df_legs_without_excluded_modes = self._legs_df.copy()[
            ~self._legs_df["mode"].isin(exclude_modes)
        ]

        if agg_modes_ruleset is not None:
            df_legs_without_excluded_modes["mode"] = df_legs_without_excluded_modes[
                "mode"
            ].replace(self._settings["mode_aggregation_rulesets"][agg_modes_ruleset])

        df_pkm = (
            df_legs_without_excluded_modes.groupby("mode")
            .agg(n=("routed_distance", "sum"))
            .reset_index()
            .assign(n=lambda x: x["n"] / 1000)  # m -> km
            # please do not delete comment:
            # // df["person_id"].str.match(self._settings["legs_table_person_id_filter"])
        )

        return df_pkm

    def get_trips_day(
        self, time_interval: int = 60, time_col: str = "start_time"
    ) -> pd.DataFrame:
        """
        Get a `DataFrame` containing the number of trips over the course of the day
        ---
        Arguments:
        - `time_interval`: number of minutes one time bin consists of
        - `time_col`: name of the column containing the time information to be binned

        Columns of `DataFrame` returned:
        - `time_index`: index of the time interval bin. Example: if `time_interval` was set to 60 mins, there will be indices 0-23
        - `n`: number of trips starting in this time bin
        """

        self._require_table("trips_df")

        df_trips_day = (
            self._add_time_indices(self._trips_df, time_interval, time_col)
            .groupby("time_index")
            .size()
            .reset_index(name="n")
        )
        return df_trips_day

    def get_modal_split(
        self,
        split_type: str = "volume",
        exclude_modes: list[str] = [],
        agg_modes_ruleset: str | None = None,
    ) -> pd.DataFrame:
        """
        Get a `DataFrame` containing the number of trips or the number of person kilometers per mode of transport
        ---
        Arguments:
        - `split_type`: 'volume', 'performance'. Using 'volume' will return the number of trips based on their `main_mode` and needs `trips_df`, using 'performance' will return person kilometers based on the `legs_df`
        - `exclude_modes`: specify a list of mode names to be disregarded in the modal split. Note that these modes have to be supplied in the form they exist in the `trips_df`, not any aggregated form
        - `agg_modes_ruleset`: which ruleset to use to aggregate the modes in the `trips_df` and `legs_df`. Has to be configured in the settings first (key `mode_aggregation_rulesets`)

        Columns of `DataFrame` returned:
        - `mode`: mode of transport
        - `n`: number of trips OR number of person kilometers travelled
        - `share`: share of all trips or person kilometers travelled
        """

        if split_type == "volume":
            self._require_table("trips_df", ["main_mode"])

            df_filtered = self._trips_df.copy()[
                ~self._trips_df["main_mode"].isin(exclude_modes)
            ]

            if agg_modes_ruleset is not None:
                df_filtered["main_mode"] = df_filtered["main_mode"].replace(
                    self._settings["mode_aggregation_rulesets"][agg_modes_ruleset]
                )

            df_split = (
                df_filtered.groupby("main_mode")
                .size()
                .reset_index(name="n")
                .rename(columns={"main_mode": "mode"})
                .assign(share=lambda x: (x["n"] / x["n"].sum()))
            )
        elif split_type == "performance":
            # This is a pretty thin wrapper around get_person_km and only adds a share column

            df_split = self.get_person_km(
                exclude_modes=exclude_modes, agg_modes_ruleset=agg_modes_ruleset
            ).assign(share=lambda x: (x["n"] / x["n"].sum()))

            ## This was unneccessarily duplicated code:
            # // self._require_table("legs_df", ["mode"])

            # // df_filtered = self._legs_df.copy()[
            # //     ~self._legs_df["mode"].isin(exclude_modes)
            # // ]

            # // if agg_modes_ruleset is not None:
            # //     df_filtered["mode"] = df_filtered["mode"].replace(
            # //         self._settings["mode_aggregation_rulesets"][agg_modes_ruleset]
            # //     )

            # // df_split = (
            # //     df_filtered.groupby("mode")
            # //     .agg(n=("routed_distance", "sum"))
            # //     .reset_index()
            # //     .assign(n=lambda x: x["n"] / 1000)
            # //     .assign(share=lambda x: (x["n"] / x["n"].sum()))
            # // )
        else:
            raise ValueError(
                "Argument `split_type` has to be either 'volume' or 'performance'"
            )

        return df_split

    # Might consider consolidating all these non-time-related/time-bin-related pairs of methods into one method respectively.
    # Setting time_interval=None then might just lead to aggregating across the whole day
    def get_modal_split_day(
        self,
        split_type: str = "volume",
        time_interval: int = 60,
        time_col: str = "start_time",
        exclude_modes: list[str] = [],
        agg_modes_ruleset: str | None = None,
    ) -> pd.DataFrame:
        """
        Get a `DataFrame` containing the number of trips or the number of person kilometers per mode of transport
        ---
        Arguments:
        - `split_type`: currently, only 'volume' is supported
        - `time_interval`: number of minutes one time bin consists of
        - `time_col`: name of the column containing the time information to be binned
        - `exclude_modes`: specify a list of mode names to be disregarded in the modal split. Note that these modes have to be supplied in the form they exist in the `trips_df`, not any aggregated form
        - `agg_modes_ruleset`: which ruleset to use to aggregate the modes in the `trips_df`. Has to be configured in the settings first (key `mode_aggregation_rulesets`)

        Columns of DataFrame returned:
        - `mode`: mode of transport
        - `time_index`: Index of the time interval bin. Example: if `time_interval` = 60 mins, there will be indices 0-23
        - `n`: Number of trips starting in this time bin OR Number of person kilometers travelled on trips starting in this time bin
        """

        # TODO: performance

        if split_type == "volume":
            self._require_table("trips_df", ["main_mode"])

            df_filtered = self._trips_df.copy()[
                ~self._trips_df["main_mode"].isin(exclude_modes)
            ]

            if agg_modes_ruleset is not None:
                df_filtered["main_mode"] = df_filtered["main_mode"].replace(
                    self._settings["mode_aggregation_rulesets"][agg_modes_ruleset]
                )

            df_split = (
                self._add_time_indices(
                    df_filtered,
                    time_interval,
                    time_col,
                )
                .groupby(by=["main_mode", "time_index"])
                .size()
                .reset_index(name="n")
                .rename(columns={"main_mode": "mode"})
            )
        else:
            raise ValueError("Only `split_type='volume'` is currently supported")

        return df_split

    def get_vehicle_km(
        self,
        exclude_modes: list[str] = [],
        agg_modes_ruleset: str | None = None,
    ) -> pd.DataFrame:
        """
        Get a `DataFrame` containing the total number of vehicle kilometers performed per (vehicle-using) mode
        ---
        Arguments:
        - `exclude_modes`: specify a list of mode names to be disregarded. Note that these modes have to be supplied in the form they exist in the `links_df`, not any aggregated form
        - `agg_modes_ruleset`: which ruleset to use to aggregate the modes in the `links_df`. Has to be configured in the settings first (key `mode_aggregation_rulesets`)

        Columns of `DataFrame` returned:
        - `mode`: mode of transport
        - `n`: number of vehicle kilometers performed
        """

        self._require_table("links_df", ["vehicle_id", "mode"])

        df_links_without_excluded_modes = self._links_df.copy()[
            ~self._links_df["mode"].isin(exclude_modes)
        ]

        if agg_modes_ruleset is not None:
            df_links_without_excluded_modes["mode"] = df_links_without_excluded_modes[
                "mode"
            ].replace(self._settings["mode_aggregation_rulesets"][agg_modes_ruleset])

        df_veh_km = (
            df_links_without_excluded_modes.drop_duplicates(
                subset=["vehicle_id", "link_id", "link_enter_time"]
            )
            .groupby("mode")
            .agg(n=("distance_travelled", "sum"))
            .reset_index()
        )
        df_veh_km["n"] = df_veh_km["n"] / 1000

        return df_veh_km

    def get_travel_time_stats(
        self,
        stats_for: str = "trips",
        distinguish_modes: bool = True,
        agg_modes_ruleset: str | None = None,
    ) -> pd.DataFrame:
        """
        Get a `DataFrame` containing a collection of travel time statistics
        ---
        Arguments:
        - `stats_for`: whether to calculate the statistics for 'trips' or 'legs'
        - `distinguish_modes`: whether or not to distinguish between modes in the resulting `DataFrame`. If calculated for trips, `main_mode` will be used
        - `agg_modes_ruleset`: which ruleset to use to aggregate the modes in the `trips_df` (Only if `distinguish_modes=True`). Has to be configured in the settings first (key `mode_aggregation_rulesets`)

        Columns of `DataFrame` returned:
        - `travel_part`: part of travel time the minutes value stands for. Example: 'waiting'
        - `main_mode`: main_mode of transport the statistics belong to. Only if `stats_for='trips'` and `distinguish_modes=True`
        - `mode`: mode of transport the statistics belong to. Only if `stats_for='legs'` and `distinguish_modes=True`
        - `mean`: mean number of minutes
        - `median`: median number of minutes
        - `min`: minimum number of minutes
        - `max`: minimum number of minutes
        - `p_5`: fifth percentile
        - `p_95`: ninety-fifth percentile
        - `std`: standard deviation
        """
        if stats_for == "trips":
            df_ttime = self.__travel_time_stats_trips(
                distinguish_modes, agg_modes_ruleset
            )
        elif stats_for == "legs":
            df_ttime = self.__travel_time_stats_legs(
                distinguish_modes, agg_modes_ruleset
            )
        else:
            raise ValueError("Argument `stats_for` has to be either 'trips' or 'legs'")

        return df_ttime

    def __travel_time_stats_trips(
        self,
        distinguish_modes: bool = True,
        agg_modes_ruleset: str | None = None,
    ):
        self._require_table("trips_df", ["trip_id", "travel_time"])

        # Get the names of columns to include as "travel parts"
        time_cols = [
            col["name"]
            for col in self._tables_specification["trips_df"]
            if "time" in col["name"] and col["name"] not in ("start_time", "end_time")
        ]

        df_ttime = self._trips_df.copy()
        if agg_modes_ruleset is not None:
            df_ttime["main_mode"] = df_ttime["main_mode"].replace(
                self._settings["mode_aggregation_rulesets"][agg_modes_ruleset]
            )

        if distinguish_modes:
            self._require_table("trips_df", ["trip_id", "travel_time", "main_mode"])
            df_ttime = df_ttime[["trip_id", "main_mode"] + time_cols]
            # Melt the DataFrame to stack travel_parts into rows
            df_ttime_molten = df_ttime.melt(
                id_vars=["trip_id", "main_mode"],
                var_name="travel_part",
                value_name="minutes",
            )
            df_ttime_molten["minutes"] = df_ttime_molten["minutes"] / 60

            df_ttime = Scenario.calc_descriptive_statistics(
                df_ttime_molten.groupby(["travel_part", "main_mode"]),
                "minutes",
            )
        else:
            df_ttime = df_ttime[["trip_id"] + time_cols]
            df_ttime_molten = df_ttime.melt(
                id_vars=["trip_id"],
                var_name="travel_part",
                value_name="minutes",
            )
            df_ttime_molten["minutes"] = df_ttime_molten["minutes"] / 60

            df_ttime = Scenario.calc_descriptive_statistics(
                df_ttime_molten.groupby("travel_part"),
                "minutes",
            )

        return df_ttime

    def __travel_time_stats_legs(
        self,
        distinguish_modes: bool = True,
        agg_modes_ruleset: str | None = None,
    ):
        self._require_table("legs_df", ["leg_id", "travel_time"])

        # Get the names of columns to include as "travel parts"
        time_cols = [
            col["name"]
            for col in self._tables_specification["legs_df"]
            if "time" in col["name"] and col["name"] not in ("start_time", "end_time")
        ]

        df_ttime = self._legs_df.copy()
        if agg_modes_ruleset is not None:
            df_ttime["mode"] = df_ttime["mode"].replace(
                self._settings["mode_aggregation_rulesets"][agg_modes_ruleset]
            )

        if distinguish_modes:
            self._require_table("legs_df", ["leg_id", "travel_time", "mode"])
            df_ttime = df_ttime[["leg_id", "mode"] + time_cols]
            # Melt the DataFrame to stack travel_parts into rows
            df_ttime_molten = df_ttime.melt(
                id_vars=["leg_id", "mode"],
                var_name="travel_part",
                value_name="minutes",
            )
            df_ttime_molten["minutes"] = df_ttime_molten["minutes"] / 60

            df_ttime = Scenario.calc_descriptive_statistics(
                df_ttime_molten.groupby(["travel_part", "mode"]),
                "minutes",
            )
        else:
            df_ttime = df_ttime[["leg_id"] + time_cols]
            df_ttime_molten = df_ttime.melt(
                id_vars=["leg_id"],
                var_name="travel_part",
                value_name="minutes",
            )
            df_ttime_molten["minutes"] = df_ttime_molten["minutes"] / 60

            df_ttime = Scenario.calc_descriptive_statistics(
                df_ttime_molten.groupby("travel_part"),
                "minutes",
            )

        return df_ttime

    def get_travel_distance_stats(
        self,
        stats_for: str = "trips",
        distinguish_modes: bool = True,
        agg_modes_ruleset: str | None = None,
        distance_col: str = "routed_distance",
    ) -> pd.DataFrame:
        """
        Get a `DataFrame` containing a collection of travel distance statistics
        ---
        Arguments:
        - `stats_for`: whether to calculate the statistics for 'trips' or 'legs'
        - `distinguish_modes`: whether or not to distinguish between modes in the resulting `DataFrame`. If calculated for trips, `main_mode` will be used
        - `agg_modes_ruleset`: which ruleset to use to aggregate the modes in the `trips_df` (Only if `distinguish_modes=True`). Has to be configured in the settings first (key `mode_aggregation_rulesets`)
        - `distance_col`: which column to generate the statistics for. The default `routed_distance` should be sensible most of the time

        Columns of `DataFrame` returned:
        - `main_mode`: main_mode of transport the statistics belong to. Only if `stats_for='trips'` and `distinguish_modes=True`
        - `mode`: mode of transport the statistics belong to. Only if `stats_for='legs'` and `distinguish_modes=True`
        - `mean`: mean distance
        - `median`: median distance
        - `min`: minimum distance
        - `max`: minimum distance
        - `p_5`: fifth percentile
        - `p_95`: ninety-fifth percentile
        - `std`: standard deviation
        """

        if stats_for == "trips":
            df_tdist = self.__travel_distance_stats_trips(
                distinguish_modes, agg_modes_ruleset, distance_col
            )
        elif stats_for == "legs":
            df_tdist = self.__travel_distance_stats_legs(
                distinguish_modes, agg_modes_ruleset, distance_col
            )
        else:
            raise ValueError("Argument `stats_for` has to be either 'trips' or 'legs'")

        return df_tdist

    def __travel_distance_stats_trips(
        self,
        distinguish_modes: bool = True,
        agg_modes_ruleset: str | None = None,
        distance_col: str = "routed_distance",
    ):
        self._require_table("trips_df", [distance_col])

        df_tdist = self._trips_df.copy()
        if agg_modes_ruleset is not None:
            df_tdist["main_mode"] = df_tdist["main_mode"].replace(
                self._settings["mode_aggregation_rulesets"][agg_modes_ruleset]
            )

        # We don't have to melt here because we only select one column for distance anyway
        if distinguish_modes:
            self._require_table("trips_df", [distance_col, "main_mode"])
            df_tdist = Scenario.calc_descriptive_statistics(
                df_tdist.groupby("main_mode"),
                distance_col,
            )
        else:
            df_tdist = Scenario.calc_descriptive_statistics(df_tdist, distance_col)

        return df_tdist

    def __travel_distance_stats_legs(
        self,
        distinguish_modes: bool = True,
        agg_modes_ruleset: str | None = None,
        distance_col: str = "routed_distance",
    ):
        self._require_table("legs_df", [distance_col])

        df_tdist = self._legs_df.copy()
        if agg_modes_ruleset is not None:
            df_tdist["mode"] = df_tdist["mode"].replace(
                self._settings["mode_aggregation_rulesets"][agg_modes_ruleset]
            )

        # We don't have to melt here because we only select one column for distance anyway
        if distinguish_modes:
            self._require_table("legs_df", [distance_col, "mode"])
            df_tdist = Scenario.calc_descriptive_statistics(
                df_tdist.groupby("mode"),
                distance_col,
            )
        else:
            df_tdist = Scenario.calc_descriptive_statistics(df_tdist, distance_col)

        return df_tdist

    def get_n_vehicles_day(
        self,
        time_interval: int = 60,
        exclude_modes: list[str] = [],
        agg_modes_ruleset: str | None = None,
    ) -> pd.DataFrame:
        """
        Get a `DataFrame` containing the number of unique vehicles travelling on the network per mode and time interval
        ---
        Arguments:
        - `time_interval`: number of minutes one time bin consists of
        - `agg_modes_ruleset`: which ruleset to use to aggregate the modes in the `links_df`. Has to be configured in the settings first (key `mode_aggregation_rulesets`)

        Columns of `DataFrame` returned:
        - `mode`: mode of transport
        - `time_index`: Index of the time interval bin. Example: if `time_interval` = 60 mins, there will be indices 0-23
        - `n`: Number of vehicles entering at least one link in the respective time bin
        """

        self._require_table("links_df", ["vehicle_id", "mode"])

        df_filtered = self._links_df.copy()[~self._links_df["mode"].isin(exclude_modes)]

        if agg_modes_ruleset is not None:
            df_filtered["mode"] = df_filtered["mode"].replace(
                self._settings["mode_aggregation_rulesets"][agg_modes_ruleset]
            )

        df_veh = (
            self._add_time_indices(
                df_filtered,
                time_interval=time_interval,
                time_col="link_enter_time",
            )
            .groupby(["mode", "time_index"])["vehicle_id"]
            .nunique()
            .reset_index(name="n")
        )

        return df_veh

    def get_peak_intervals(
        self,
        time_interval: int = 60,
        time_col: str = "start_time",
        exclude_modes: list[str] = [],
        agg_modes_ruleset: str | None = None,
    ) -> pd.DataFrame:
        """
        Get the index of the time bin with the highest number of trips starting/ending, summarised over the specified mode(s)
        ---
        Arguments:
        - `time_interval`: number of minutes one time bin consists of
        - `time_col`: name of the column containing the time information to be binned
        - `exclude_modes`: specify a list of mode names to be disregarded. Note that these modes have to be supplied in the form they exist in the `links_df`, not any aggregated form
        - `agg_modes_ruleset`: which ruleset to use to aggregate the modes in the `links_df`. Has to be configured in the settings first (key `mode_aggregation_rulesets`)
        """

        # df_split_day = self.get_modal_split_day(
        #     split_type="volume",
        #     time_interval=time_interval,
        #     time_col=time_col,
        #     exclude_modes=exclude_modes,
        #     agg_modes=agg_modes,
        # )

        # return peak_interval

        raise NotImplementedError

    def get_trip_locations(
        self,
        direction: str = "origin",
    ) -> gpd.GeoDataFrame:
        """
        Get a `GeoDataFrame` containing the origin or destination points of trips
        ---
        """
        gdf_trips = gpd.GeoDataFrame(
            self._trips_df,
            geometry=gpd.points_from_xy(
                x=self._trips_df["from_x" if direction == "origin" else "to_x"],
                y=self._trips_df["from_y" if direction == "origin" else "to_y"],
                crs="EPSG:25833",
            ),
        )

        return gdf_trips

    def get_zone_trips(
        self,
        agg_gdf: gpd.GeoDataFrame,
        distinguish_modes=True,
        exclude_modes: list[str] = [],
        agg_modes_ruleset: str | None = None,
        pt_lines: list[str] | None = None,
        direction: str = "origin",
    ) -> gpd.GeoDataFrame:
        """
        Get a `GeoDataFrame` containing the number of trips originating/ending in specified zones the trips are aggregated to, optionally per mode and only for specified pt lines
        ---
        Arguments:
        - `agg_gdf`: multipolygon `GeoDataFrame` containing zones the trips will be aggregated to. Must contain a column called `zone_id`. Will append all feature attributes to the df
        - `distinguish_modes`: whether or not to distinguish between modes in the resulting `GeoDataFrame`. Must be set to `True` to use `pt_lines`
        - `exclude_modes`: specify a list of mode names to be disregarded. Note that these modes have to be supplied in the form they exist in the `trips_df`, not any aggregated form
        - `agg_modes_ruleset`: which ruleset to use to aggregate the modes in the `trips_df`. Has to be configured in the settings first (key `mode_aggregation_rulesets`)
        - `pt_lines`: line id, list of line ids or `None`. If line id(s) are specified, the pt mode(s) will only contain OD data for those lines. If set to `None`, all lines will be included
        - `direction`: 'origin' or 'destination'. Whether to count trips originating or ending in the zones provided in `agg_gdf`

        Columns of `GeoDataFrame` returned:
        - `zone_id`: id of the respective zone
        - `mode`: mode of transport. If `distinguish_modes` is set to `False` this column will contain `nan`s
        - `n_origin`: Number of trips originating from this zone
        - `n_destination`: Number of trips ending in this zone
        """
        # NOT TESTED YET
        # TODO: Consider renaming agg_gdf to something like "zones" or "zones_gdf"
        # TODO: Separate aggreations for origin / destination # DONE?

        self._require_table("trips_df", ["from_x", "from_y", "to_x", "to_y"])

        # Convert df with point coordinates to actual Points gdf
        gdf_trips = gpd.GeoDataFrame(
            self._trips_df,
            geometry=gpd.points_from_xy(
                self._trips_df["from_x" if direction == "origin" else "to_x"],
                self._trips_df["from_y" if direction == "origin" else "to_y"],
                crs="EPSG:25833",
            ),
        )

        # Perform a spatial join to associate each trip with a polygon
        agg_gdf = agg_gdf.to_crs("EPSG:25833")
        joined: gpd.GeoDataFrame = gpd.sjoin(
            gdf_trips, agg_gdf, how="left", predicate="within"
        )

        # Count trips per zone
        if distinguish_modes:
            self._require_table("trips_df", ["main_mode"])

            # if the pt trips should be filtered for specific pt lines
            if pt_lines is not None:
                self._require_table("legs_df", ["line_id"])
                assert (
                    isinstance(self._settings["pt_modes"], list)
                    and len(self._settings["pt_modes"]) > 0
                ), "To use this functionality, please set `pt_modes` in settings first"

                # filter for trips first that have a non-pt main_mode
                trips_non_pt = joined[
                    ~joined["main_mode"].isin(self._settings["pt_modes"])
                ]
                # find legs with one of the line_ids to filter for and get corresponding trip ids
                trip_ids_with_pt_lines = self._legs_df[
                    self._legs_df["line_id"].isin(pt_lines)
                ]["trip_id"].unique()
                # final filter
                trips_filtered = pd.concat(
                    [
                        trips_non_pt,
                        joined[joined["trip_id"].isin(trip_ids_with_pt_lines)],
                    ]
                )

                trips_filtered = trips_filtered[
                    ~trips_filtered["main_mode"].isin(exclude_modes)
                ]
            else:
                trips_filtered = joined

            if agg_modes_ruleset is not None:
                trips_filtered["main_mode"] = trips_filtered["main_mode"].replace(
                    self._settings["mode_aggregation_rulesets"][agg_modes_ruleset]
                )

            counts = (
                joined.groupby(["zone_id", "mode"])
                .size()
                .reset_index(name="n")
                .pivot(index="zone_id", columns="mode", values="n")
            )

        else:
            counts = (
                joined["zone_id"]
                .groupby("zone_id")
                .size()
                .reset_index(name="all modes")
            )

        return counts

    def get_zone_trips_day(
        self,
        agg_gdf: gpd.GeoDataFrame,
        distinguish_modes=True,
        pt_lines: str | list[str] | None = None,
        time_interval: int = 60,
    ) -> pd.DataFrame:
        """
        Get a `GeoDataFrame` containing the number of trips originating/ending in specified zones the trips are aggregated to per time bin, optionally per mode and only for specified pt lines
        ---
        Arguments:
        - `agg_gdf`: multipolygon `GeoDataFrame` containing zones the trips will be aggregated to. Must contain a column called `zone_id`
        - `distinguish_modes`: whether or not to distinguish between modes in the resulting `GeoDataFrame`. Must be set to `True` to use `pt_lines`
        - `pt_lines`: line id, list of line ids or `None`. If line id(s) are specified, the pt mode(s) will only contain OD data for those lines. If set to `None`, all lines will be included
        - `time_interval`: number of minutes one time bin consists of

        Columns of `GeoDataFrame` returned:
        - `zone_id`: id of the respective zone
        - `mode`: mode of transport. If `distinguish_modes` is set to `False` this column will contain `nan`s
        - `time_index`: Index of the time interval bin. Example: if `time_interval` = 60 mins, there will be indices 0-23
        - `n_origin`: Number of trips originating from this zone in the respective time bin
        - `n_destination`: Number of trips ending in this zone in the respective time bin
        """

        raise NotImplementedError

    def get_relations_agg(
        self,
        agg_gdf: gpd.GeoDataFrame,
        distinguish_modes=True,
        pt_lines: str | list[str] | None = None,
    ) -> gpd.GeoDataFrame:
        raise NotImplementedError

    def get_relations_agg_day(
        self,
        agg_gdf: gpd.GeoDataFrame,
        distinguish_modes=True,
        pt_lines: str | list[str] | None = None,
        time_interval: int = 60,
    ) -> gpd.GeoDataFrame:
        raise NotImplementedError

    def get_access_egress_distances(
        self,
        agg_modes_ruleset: str | None = None,
    ) -> pd.DataFrame:
        """
        Get a `DataFrame` containing descriptive statistics on access and egress walking distances per mode
        ---
        Arguments:
        - `agg_modes_ruleset`: which ruleset to use to aggregate the modes in the `trips_df`. Has to be configured in the settings first (key `mode_aggregation_rulesets`)

        Columns of `DataFrame` returned:
        - `main_mode`: main_mode of transport the statistics belong to. Only if `distinguish_modes` was set to `True`
        - `kind`: either 'access' or 'egress'
        - `mean`: mean distance in meters
        - `median`: median distance in meters
        - `min`: minimum distance in meters
        - `max`: minimum distance in meters
        - `p_5`: fifth percentile
        - `p_95`: ninety-fifth percentile
        - `std`: standard deviation
        """
        self._require_table(
            "trips_df", ["main_mode", "access_distance", "egress_distance"]
        )

        access_egress = self._trips_df.copy()

        if agg_modes_ruleset is not None:
            access_egress["main_mode"] = access_egress["main_mode"].replace(
                self._settings["mode_aggregation_rulesets"][agg_modes_ruleset]
            )

        access_egress = self.calc_descriptive_statistics(
            (
                access_egress
                # melt into long format so we can use the descriptive statistics method
                .melt(
                    id_vars=["main_mode"],
                    value_vars=["access_distance", "egress_distance"],
                    value_name="distance",
                    var_name="kind",
                )
                .replace({"access_distance": "access", "egress_distance": "egress"})
                .groupby(["main_mode", "kind"])
            ),
            value_col="distance",
        ).fillna(0)

        return access_egress

    def get_line_ridership(
        self,
        lines: str | list[str] | None = None,
    ) -> pd.DataFrame:
        raise NotImplementedError

    def get_line_ridership_day(
        self, lines: str | list[str] | None = None, time_interval: int = 60
    ) -> pd.DataFrame:
        raise NotImplementedError

    def get_line_occupancy(
        self,
        lines: str | list[str] | None = None,
    ) -> pd.DataFrame:
        raise NotImplementedError

    def get_line_occupancy_day(
        self, lines: str | list[str] | None = None, time_interval: int = 60
    ) -> pd.DataFrame:
        raise NotImplementedError

    def get_line_stops(
        self,
        lines: str | list[str] | None = None,
    ) -> gpd.GeoDataFrame:
        raise NotImplementedError

    def get_line_stops_day(
        self, lines: str | list[str] | None = None, time_interval: int = 60
    ) -> gpd.GeoDataFrame:
        raise NotImplementedError

    def get_line_links_occupancy(
        self, lines: str | list[str] | None = None
    ) -> gpd.GeoDataFrame:
        raise NotImplementedError

    def get_line_links_occupancy_day(
        self, lines: str | list[str] | None = None, time_interval: int = 60
    ) -> gpd.GeoDataFrame:
        raise NotImplementedError

    def get_line_links(self, lines: str | list[str] | None = None) -> gpd.GeoDataFrame:
        # get links a line travels on as gdf
        raise NotImplementedError

    def get_settings(self) -> dict:
        warnings.warn(
            "Use Scenario.get_setting(setting) instead", category=DeprecationWarning
        )
        return self._settings

    def get_setting(self, setting: str):
        return self._settings[setting]

    def set_setting(self, setting: str, value) -> None:
        self._settings[setting] = value

    @staticmethod
    def calc_descriptive_statistics(
        df: pd.DataFrame | gpd.GeoDataFrame, value_col: str
    ) -> pd.DataFrame | gpd.GeoDataFrame:
        # TODO: Be able to configure percentiles
        # // Consider using pandas.describe() instead

        df_res = df.agg(
            mean=(value_col, "mean"),
            median=(value_col, "median"),
            min=(value_col, "min"),
            max=(value_col, "max"),
            p_5=(value_col, lambda x: np.percentile(x, 5)),
            p_95=(value_col, lambda x: np.percentile(x, 95)),
            std=(value_col, "std"),
        ).reset_index()

        return df_res

    def _check_specification_compliance(
        self, df: pd.DataFrame, table_name: str
    ) -> bool:
        """
        Checks a given `DataFrame` for compliance with the table specifications defined in `tables_specification.json`
        """
        # TODO: Implement column type checking
        # TODO: Implement column type casting

        cols_existing = [
            col["name"]
            for col in self._tables_specification[table_name]
            if col["name"] in list(df.columns)
        ]
        cols_not_existing = [
            col["name"]
            for col in self._tables_specification[table_name]
            if col["name"] not in list(df.columns)
        ]
        cols_not_used = [
            col
            for col in list(df.columns)
            if col not in [c["name"] for c in self._tables_specification[table_name]]
        ]
        if len(cols_existing) == 0 or df.size == 0:
            raise ValueError(
                f"`{table_name}` DataFrame does not contain any recognized columns or has no entries"
            )
        if cols_not_used:
            print(
                f"The provided `{table_name}` contains the following columns that are not recognized and will not be used:\n{cols_not_used}"
            )

        return True

    def _add_time_indices(
        self,
        df: pd.DataFrame,
        time_interval: int | None = None,
        time_col: str = "start_time",
    ) -> pd.DataFrame:
        if time_interval is None:
            time_interval = self._settings["default_time_agg_interval"]

        return df.assign(time_index=lambda x: x[time_col] // (time_interval * 60))

    def _require_table(self, df_name: str, cols: list[str] | None = None) -> None:
        if df_name == "trips_df":
            assert (
                self._trips_df is not None
            ), "You need to add a `trips_df` to this scenario to use this method"
            if cols is not None:
                assert all(
                    col in list(self._trips_df.columns) for col in cols
                ), f"One of the columns {cols} does not exist in the scenario's `trips_df`"
        elif df_name == "legs_df":
            assert (
                self._legs_df is not None
            ), "You need to add a `legs_df` to this scenario to use this method"
            if cols is not None:
                assert all(
                    col in list(self._legs_df.columns) for col in cols
                ), f"One of the columns {cols} does not exist in the scenario's `legs_df`"
        elif df_name == "links_df":
            assert (
                self._links_df is not None
            ), "You need to add a `links_df` to this scenario to use this method"
            if cols is not None:
                assert all(
                    col in list(self._links_df.columns) for col in cols
                ), f"One of the columns {cols} does not exist in the scenario's `links_df`"
        else:
            raise ValueError(f"Wrong `df_name`: {df_name}")

    def get_operating_zone(self) -> gpd.GeoDataFrame:
        return self._operating_zone
