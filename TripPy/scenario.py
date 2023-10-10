import os
import json
import numpy as np
import pandas as pd
import geopandas as gpd


class Scenario:
    """
    Class that models a transport planning scenario holding one or more different
    `(geo)pandas` `(Geo)DataFrames` containing data on trips, legs and/or network links
    """

    # TODO: Add methods for data to be used for visualizations like heatmaps and linestring stuff (precise coordinates)
    # TODO: Add ability to add a matsim timetable for the line related methods

    def __init__(
        self,
        code: str | None = None,
        name: str | None = "my scenario",
        description: str | None = None,
        trips_df: pd.DataFrame | None = None,
        legs_df: pd.DataFrame | None = None,
        links_df: pd.DataFrame | gpd.GeoDataFrame | None = None,
        network_df: gpd.GeoDataFrame | None = None,
    ):
        # TODO: Argument type checking 
        # TODO: Docstring
        # TODO: Implement settings to be loaded from a json file as well

        self.code = code
        self.name = name
        self.description = description

        self._settings = {
            "default_time_agg_interval": 60,
            "drt_mode": "drt",
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
            "legs_table_person_id_filter": "^((?!^pt).)*$",  # only selects person_ids that do not start with "pt"
            # TODO: for release: replace with {}
            "mode_aggregation_rules": {
                "100": "pt",
                "300": "pt",
                "500": "pt",
                "600": "pt",
                "700": "pt",
                "800": "pt",
                "BVB10": "pt",
                "BVB10M": "pt",
                "BVT30": "pt",
                "BVT30M": "pt",
                "BVB10X": "pt",
                "BVU20": "pt",
                "BVF100": "pt",
            },
        }

        with open("tables_specification.json", encoding = 'utf-8') as file:
            self._tables_specification = json.load(file)

        self._trips_df: pd.DataFrame = None
        self._legs_df: pd.DataFrame = None
        self._links_df: pd.DataFrame | gpd.GeoDataFrame = None
        self._network_df: gpd.GeoDataFrame = None

        if trips_df is not None:
            self.add_data(trips_df=trips_df)
        if legs_df is not None:
            self.add_data(legs_df=legs_df)
        if links_df is not None:
            self.add_data(links_df=links_df)
        if network_df is not None:
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
        """

        for key, value in kwargs.items():
            if key == "trips_df" and self._check_specification_compliance(
                value, "trips_df"
            ):
                self._trips_df = value
                if "trip_id" not in list(self._trips_df.columns):
                    self._trips_df["trip_id"] = self._trips_df.index.astype(str)

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

    def get_person_km(self) -> float:
        """
        Get the total number of person kilometers performed
        ---
        """

        self._require_table("legs_df", ["person_id", "routed_distance"])

        # filter out ptDriverAgents
        pkm = (
            self._legs_df["routed_distance"]
            # //[self._legs_df["person_id"]
            # match a regex string defined in settings(e.g. no ptDriverAgents)
            # // .str.match(self._settings["legs_table_person_id_filter"])][
            # //     "routed_distance"
            # // ]
            .sum()
        )

        return pkm

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
        agg_modes: bool = True,
    ) -> pd.DataFrame:
        """
        Get a `DataFrame` containing the number of trips or the number of person kilometers per mode of transport
        ---
        Arguments:
        - `split_type`: 'volume', 'performance'. Using 'volume' will return the number of trips based on their `main_mode` and needs `trips_df`, using 'performance' will return person kilometers based on the `legs_df`
        - `exclude_modes`: specify a list of mode names to be disregarded in the modal split. Note that these modes have to be supplied in the form they exist in the `trips_df`, not any aggregated form
        - `agg_modes`: whether to aggregate the modes in the `trips_df` and `legs_df` according to the assignment in the settings (key `mode_aggregation_rules`)

        Columns of `DataFrame` returned:
        - `mode`: mode of transport
        - `n`: number of trips OR number of person kilometers travelled
        """

        if split_type == "volume":
            self._require_table("trips_df", ["main_mode"])

            df_filtered = self._trips_df[
                ~self._trips_df["main_mode"].isin(exclude_modes)
            ]

            if agg_modes:
                df_filtered["main_mode"] = df_filtered["main_mode"].replace(
                    self._settings["mode_aggregation_rules"]
                )

            df_split = (
                df_filtered.groupby("main_mode")
                .size()
                .reset_index(name="n")
                .rename(columns={"main_mode": "mode"})
                .assign(prc=lambda x: (x["n"] / x["n"].sum()))
            )
        elif split_type == "performance":
            self._require_table("legs_df", ["mode"])

            df_filtered = self._legs_df[~self._legs_df["mode"].isin(exclude_modes)]

            if agg_modes:
                df_filtered["mode"] = df_filtered["mode"].replace(
                    self._settings["mode_aggregation_rules"]
                )

            df_split = (
                df_filtered.groupby("mode")
                .agg(n=("routed_distance", "sum"))
                .reset_index(name="n")
                .assign(prc=lambda x: (x["n"] / x["n"].sum()))
            )
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
        agg_modes: bool = True,
    ) -> pd.DataFrame:
        """
        Get a `DataFrame` containing the number of trips or the number of person kilometers per mode of transport
        ---
        Arguments:
        - `split_type`: currently, only 'volume' is supported
        - `time_interval`: number of minutes one time bin consists of
        - `time_col`: name of the column containing the time information to be binned
        - `exclude_modes`: specify a list of mode names to be disregarded in the modal split. Note that these modes have to be supplied in the form they exist in the `trips_df`, not any aggregated form
        - `agg_modes`: whether to aggregate the modes in the `trips_df` according to the assignment in the settings (key `mode_aggregation_rules`)

        Columns of DataFrame returned:
        - `mode`: mode of transport
        - `time_index`: Index of the time interval bin. Example: if `time_interval` = 60 mins, there will be indices 0-23
        - `n`: Number of trips starting in this time bin OR Number of person kilometers travelled on trips starting in this time bin
        """

        # TODO: performance

        if split_type == "volume":
            self._require_table("trips_df", ["main_mode"])

            df_filtered = self._trips_df[
                ~self._trips_df["main_mode"].isin(exclude_modes)
            ]

            if agg_modes:
                df_filtered["main_mode"] = df_filtered["main_mode"].replace(
                    self._settings["mode_aggregation_rules"]
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
        agg_modes: bool = True,
    ) -> pd.DataFrame:
        """
        Get a `DataFrame` containing the total number of vehicle kilometers performed per (vehicle-using) mode
        ---
        Arguments:
        - `exclude_modes`: specify a list of mode names to be disregarded. Note that these modes have to be supplied in the form they exist in the `links_df`, not any aggregated form
        - `agg_modes`: whether to aggregate the modes in the `links_df` according to the assignment in the settings (key `mode_aggregation_rules`)

        Columns of `DataFrame` returned:
        - `mode`: mode of transport
        - `n`: Number of vehicle kilometers performed
        """

        # TODO: filter out ptDriverAgents

        self._require_table("links_df", ["vehicle_id", "mode"])

        df_links_without_excluded_modes = self._links_df[~self._links_df["mode"].isin(exclude_modes)]

        if agg_modes:
            df_links_without_excluded_modes["mode"] = df_links_without_excluded_modes["mode"].replace(
                self._settings["mode_aggregation_rules"]
            )

        df_veh_km = (
            df_links_without_excluded_modes.groupby("mode")
            .agg(n=("link_travel_distance", "sum"))
            .reset_index(name="n")
        )

        return df_veh_km

    def get_travel_time_stats(self) -> pd.DataFrame:
        """
        Get a `DataFrame` containing a collection of travel time statistics
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

        # TODO: travel time stats per mode!

        self._require_table("trips_df", ["travel_time"])

        # Melt the DataFrame to stack travel_parts into rows
        df_ttime = Scenario.calc_descriptive_statistics(
            self._trips_df.melt(
                id_vars=["trip_id"],
                var_name="travel_part",
                value_name="minutes",
            ).groupby("travel_part"),
            "minutes",
        )

        return df_ttime

    def get_n_vehicles_day(
        self,
        time_interval: int = 60,
        exclude_modes: list[str] = [],
        agg_modes: bool = True,
    ) -> pd.DataFrame:
        """
        Get a `DataFrame` containing the number of unique vehicles travelling on the network per mode and time interval
        ---
        Arguments:
        - `time_interval`: number of minutes one time bin consists of

        Columns of `DataFrame` returned:
        - `mode`: mode of transport
        - `time_index`: Index of the time interval bin. Example: if `time_interval` = 60 mins, there will be indices 0-23
        - `n`: Number of vehicles entering at least one link in the respective time bin
        """

        self._require_table("links_df", ["vehicle_id", "mode"])

        df_filtered = self._links_df[~self._links_df["main_mode"].isin(exclude_modes)]

        if agg_modes:
            df_filtered["main_mode"] = df_filtered["main_mode"].replace(
                self._settings["mode_aggregation_rules"]
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
        agg_modes: bool = True,
    ) -> pd.DataFrame:
        """
        Get the index of the time bin with the highest number of trips starting/ending, summarised over the specified mode(s)
        ---
        Arguments:
        - `time_interval`: number of minutes one time bin consists of
        - `time_col`: name of the column containing the time information to be binned
        - `exclude_modes`: specify a list of mode names to be disregarded. Note that these modes have to be supplied in the form they exist in the `links_df`, not any aggregated form
        - `agg_modes`: whether to aggregate the modes in the `links_df` according to the assignment in the settings (key `mode_aggregation_rules`)
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

    def get_zone_trips(
        self,
        agg_gdf: gpd.GeoDataFrame,
        distinguish_modes=True,
        exclude_modes: list[str] = [],
        agg_modes: bool = True,
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
        - `agg_modes`: whether to aggregate the modes in the `links_df` according to the assignment in the settings (key `mode_aggregation_rules`). This happens after filtering for provided `pt_lines`
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
        # TODO: Separate aggreations for origin / destination

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

            if agg_modes:
                trips_filtered["main_mode"] = trips_filtered["main_mode"].replace(
                    self._settings["mode_aggregation_rules"]
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

    @staticmethod
    def calc_descriptive_statistics(
        df: pd.DataFrame | gpd.GeoDataFrame, value_col: str
    ) -> pd.DataFrame | gpd.GeoDataFrame:
        
        # TODO: Be able to configure percentiles
        #// Consider using pandas.describe() instead

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

