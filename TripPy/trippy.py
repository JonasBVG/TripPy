import pandas as pd
import geopandas as gpd
import json


class Scenario:
    """
    Class that models a transport planning scenario holding one or more different
    `(geo)pandas` `(Geo)DataFrames` containing data on trips, legs and/or network links
    """

    def __init__(
        self,
        code: str = None,
        name: str = "my scenario",
        description: str = None,
        trips_df: pd.DataFrame = None,
        legs_df: pd.DataFrame = None,
        links_df: pd.DataFrame | gpd.GeoDataFrame = None,
    ):
        # TODO: Argument type checking
        # TODO: Docstring
        # TODO: Implement settings
        # TODO: Implement mode dict

        self.code = code
        self.name = name
        self.description = description

        self.__settings = {"default_time_agg_interval": 60}

        with open("tables_specification.json") as file:
            self.__tables_specification = json.load(file)
        self.__trips_df = None
        self.__legs_df = None
        self.__links_df = None

        self.__linked_df = None

        if trips_df:
            self.add_trips_df(trips_df)
        if legs_df:
            self.add_legs_df(legs_df)
        if links_df:
            self.add_links_df(links_df)

    def __check_specification_compliance(
        self, df: pd.DataFrame, table_name: str
    ) -> bool:
        """
        Checks a given `DataFrame` for compliance with table specifications defined in `tables_specification.json`
        """
        # TODO: Implement column type checking
        # TODO: Implement column type casting

        cols_existing = [
            col["name"]
            for col in self.__tables_specification[table_name]
            if col["name"] in list(df.columns)
        ]
        cols_not_existing = [
            col["name"]
            for col in self.__tables_specification[table_name]
            if col["name"] not in list(df.columns)
        ]
        cols_not_used = [
            col
            for col in list(df.columns)
            if col not in [c["name"] for c in self.__tables_specification[table_name]]
        ]
        if len(cols_existing) == 0 or df.size == 0:
            raise ValueError(
                f"`{table_name}` DataFrame does not contain any recognized columns or has no entries"
            )
        if cols_not_used:
            raise UserWarning(
                f"The provided `{table_name}` contains the following columns that are not recognized and will not be used:\n{cols_not_used}"
            )

        return True

    def add_trips_df(self, trips_df: pd.DataFrame) -> None:
        """
        Add a trip `DataFrame` to the scenario
        ---
        Arguments:
        - `trips_df`: a `pandas` `DataFrame` containing at least one trip
        """

        if self.__check_specification_compliance(trips_df, "trips_df"):
            self.__trips_df = trips_df

            if "trip_id" not in list(self.__trips_df.columns):
                self.__trips_df["trip_id"] = self.__trips_df.index.astype(str)

    def add_legs_df(self, legs_df: pd.DataFrame) -> None:
        """
        Add a leg `DataFrame` to the scenario
        ---
        Arguments:
        - legs_df: a `pandas` `DataFrame` containing at least one leg
        """

        if self.__check_specification_compliance(legs_df, "legs_df"):
            self.__legs_df = legs_df

            if "leg_id" not in list(self.__legs_df.columns):
                self.__legs_df["leg_id"] = self.__legs_df.index.astype(str)

    def add_links_df(self, links_df: pd.DataFrame | gpd.GeoDataFrame) -> None:
        """
        Add a link `DataFrame` to the scenario
        ---
        Arguments:
        - `links_df`: a `pandas` `DataFrame` or a `geopandas` `GeoDataFrame` containing at least one link
        """

        if self.__check_specification_compliance(links_df, "links_df"):
            self.__links_df = links_df

            if "link_id" not in list(self.__links_df.columns):
                self.__links_df["link_id"] = self.__links_df.index.astype(str)

    def get_trips_df(self) -> pd.DataFrame:
        """
        Get the trips `DataFrame` stored in the scenario
        ---
        """
        return self.__trips_df

    def get_legs_df(self) -> pd.DataFrame:
        """
        Get the legs `DataFrame` stored in the scenario
        ---
        """
        return self.__legs_df

    def get_links_df(self) -> gpd.GeoDataFrame:
        """
        Get the links `DataFrame` stored in the scenario
        ---
        """
        return self.__links_df

    def __generate_linked_df(self) -> None:
        """
        Generate a linked df consisting of trips, legs, links. Not sure if this will be used
        ---
        """
        raise NotImplementedError

    def get_n_trips(self) -> int:
        """
        Get the total number of trips
        ---
        """
        raise NotImplementedError

    def get_n_persons(self) -> int:
        """
        Get the number of unique persons
        ---
        """
        raise NotImplementedError

    def get_person_km(self) -> float:
        """
        Get the total number of person kilometers performed
        ---
        """
        raise NotImplementedError

    def get_trips_day(self, time_interval: int = 60) -> pd.DataFrame:
        """
        Get a `DataFrame` containing the number of trips over the course of the day
        ---
        Arguments:
        - `time_interval`: number of minutes one time bin consists of

        Columns of `DataFrame` returned:
        - `time_index`: Index of the time interval bin. Example: If `time_interval` was set to 60 mins, there will be indices 0-23
        - `n`: Number of trips starting in this time bin
        """
        raise NotImplementedError

    def get_modal_split(self, type: str = "volume") -> pd.DataFrame:
        """
        Get a `DataFrame` containing the number of trips or the number of person kilometers per mode of transport
        ---
        Arguments:
        - `type`: 'volume' or 'performance'. Using 'volume' will return the number of trips, using 'performance' will return person kilometers

        Columns of `DataFrame` returned:
        - `mode`: mode of transport
        - `n`: Number of trips OR Number of person kilometers travelled
        """
        raise NotImplementedError

    # Might consider consolidating all these non-time-related/time-bin-related pairs of methods into one method respectively.
    # Setting time_interval=None then might just lead to aggregating across the whole day
    def get_modal_split_day(
        self, type: str = "volume", time_interval: int = 60
    ) -> pd.DataFrame:
        """
        Get a `DataFrame` containing the number of trips or the number of person kilometers per mode of transport
        ---
        Arguments:
        - `type`: 'volume' or 'performance'. Using 'volume' will return the number of trips, using 'performance' will return person kilometers
        - `time_interval`: number of minutes one time bin consists of

        Columns of DataFrame returned:
        - `mode`: mode of transport
        - `time_index`: Index of the time interval bin. Example: If `time_interval` = 60 mins, there will be indices 0-23
        - `n`: Number of trips starting in this time bin OR Number of person kilometers travelled on trips starting in this time bin
        """
        # This should probably not function as described above, but should actually count the person kilometers in the time bin, not of trips starting in this time bin
        # A long 2h trip starting at 7:59 will completely fall into time bin 6-7 for example

        raise NotImplementedError

    def get_vehicle_km(self) -> pd.DataFrame:
        """
        Get a `DataFrame` containing the total number of vehicle kilometers performed per (vehicle-using) mode
        ---

        Columns of `DataFrame` returned:
        - `mode`: mode of transport
        - `n`: Number of vehicle kilometers performed
        """
        raise NotImplementedError

    def get_travel_time_stats(self) -> pd.DataFrame:
        """
        Get a `DataFrame` containing a collection of travel time statistics
        ---

        Columns of `DataFrame` returned:
        - `travel_part`: part of travel time the minutes value stands for. Example: 'waiting'
        - `minutes`: Minutes the travel time part took on average
        """
        raise NotImplementedError

    def get_n_vehicles_day(self, time_interval: int = 60) -> pd.DataFrame:
        """
        Get a `DataFrame` containing the number of unique vehicles travelling on the network per time interval
        ---
        Arguments:
        - `time_interval`: number of minutes one time bin consists of

        Columns of `DataFrame` returned:
        - `mode`: mode of transport
        - `time_index`: Index of the time interval bin. Example: If `time_interval` = 60 mins, there will be indices 0-23
        - `n`: Number of vehicles entering at least one link in the respective time bin
        """
        raise NotImplementedError

    def get_peak_interval(
        self, time_interval: int = 60, modes: str | list[str] | None = None
    ) -> int:
        """
        Get the index of the time bin with the highest number of trips starting, summarised over the specified mode(s)
        ---
        Arguments:
        - `time_interval`: number of minutes one time bin consists of
        - `modes`: name of a single mode, a list of mode names or None. If mode(s) are specified, the peak time bin for those modes combined will be calculated. If None, all modes will be summarised
        """
        raise NotImplementedError

    def get_od_agg(
        self,
        agg_gdf: gpd.GeoDataFrame,
        distinguish_modes=True,
        pt_lines: str | list[str] | None = None,
    ) -> gpd.GeoDataFrame:
        """
        Get a `GeoDataFrame` containing the number of trips originating/ending in specified zones the trips are aggregated to, optionally per mode and only for specified pt lines
        ---
        Arguments:
        - `agg_gdf`: multipolygon `GeoDataFrame` containing zones the trips will be aggregated to. Must contain a column called `zone_id`
        - `distinguish_modes`: whether or not to distinguish between modes in the resulting `GeoDataFrame`. Must be set to `True` to use `pt_lines`
        - `pt_lines`: line id, list of line ids or `None`. If line id(s) are specified, the pt mode(s) will only contain OD data for those lines. If set to `None`, all lines will be included

        Columns of `GeoDataFrame` returned:
        - `zone_id`: id of the respective zone
        - `mode`: mode of transport. If `distinguish_modes` is set to `False` this column will contain `nan`s
        - `n_origin`: Number of trips originating from this zone
        - `n_destination`: Number of trips ending in this zone
        """
        raise NotImplementedError

    def get_od_agg_day(
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
        - `time_index`: Index of the time interval bin. Example: If `time_interval` = 60 mins, there will be indices 0-23
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


# TESTS
if __name__ == "__main__":
    myscen = Scenario()
    thedf = pd.DataFrame(data={"person_id": ["1", "2"]})
    print(thedf)
    myscen.add_trips_df(thedf)
    print(myscen.get_trips_df())
