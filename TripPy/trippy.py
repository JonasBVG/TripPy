import pandas as pd
import geopandas as gpd
import json


class Scenario:
    """
    Class that models a transport planning scenario holding one or more different
    (geo)pandas (Geo)DataFrames containing data on trips, legs and/or network links
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
        Checks a given DataFrame for compliance with table specifications defined in tables_specification.json
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
        Add a trip table to the scenario
        ---
        trips_df: a pandas DataFrame containing at least one trip
        """

        if self.__check_specification_compliance(trips_df, "trips_df"):
            self.__trips_df = trips_df

            if "trip_id" not in list(self.__trips_df.columns):
                self.__trips_df["trip_id"] = self.__trips_df.index.astype(str)

    def add_legs_df(self, legs_df: pd.DataFrame) -> None:
        """
        Add a leg table to the scenario
        ---
        legs_df: a pandas DataFrame containing at least one leg
        """

        if self.__check_specification_compliance(legs_df, "legs_df"):
            self.__legs_df = legs_df

            if "leg_id" not in list(self.__legs_df.columns):
                self.__legs_df["leg_id"] = self.__legs_df.index.astype(str)

    def add_links_df(self, links_df: pd.DataFrame | gpd.GeoDataFrame) -> None:
        """
        Add a link table to the scenario
        ---
        links_df: a pandas DataFrame containing at least one link
        """

        if self.__check_specification_compliance(links_df, "links_df"):
            self.__links_df = links_df

            if "link_id" not in list(self.__links_df.columns):
                self.__links_df["link_id"] = self.__links_df.index.astype(str)

    def get_trips_df(self) -> pd.DataFrame:
        return self.__trips_df

    def get_legs_df(self) -> pd.DataFrame:
        return self.__legs_df

    def get_links_df(self) -> gpd.GeoDataFrame:
        return self.__links_df

    def __generate_linked_df(self) -> None:
        raise NotImplementedError

    def get_n_trips(self) -> int:
        raise NotImplementedError

    def get_n_persons(self) -> int:
        raise NotImplementedError

    def get_person_km(self) -> float:
        raise NotImplementedError

    def get_trips_day(self, time_interval: int = 60) -> pd.DataFrame:
        raise NotImplementedError

    def get_modal_split(self, type: str = "volume") -> pd.DataFrame:
        raise NotImplementedError

    def get_vehicle_km(self) -> pd.DataFrame:
        raise NotImplementedError

    def get_travel_time_stats(self) -> pd.DataFrame:
        raise NotImplementedError

    def get_n_vehicles_day(self, time_interval: int = 60) -> pd.DataFrame:
        raise NotImplementedError

    def get_peak_interval(self, time_interval: int = 60, modes: str | list[str] | None = None) -> int:
        raise NotImplementedError

    def get_od_agg(
        self,
        agg_gdf: gpd.GeoDataFrame,
        pt_lines: str | list[str] | None = None,
    ) -> pd.DataFrame:
        raise NotImplementedError

    def get_od_agg_day(
        self,
        agg_gdf: gpd.GeoDataFrame,
        pt_lines: str | list[str] | None = None,
        time_interval: int = 60
    ) -> pd.DataFrame:
        raise NotImplementedError

    def get_line_ridership(self, lines: str | list[str] | None = None,) -> pd.DataFrame:
        raise NotImplementedError

    def get_line_ridership_day(self, lines: str | list[str] | None = None, time_interval: int = 60) -> pd.DataFrame:
        raise NotImplementedError

    def get_line_occupancy(self, lines: str | list[str] | None = None,) -> pd.DataFrame:
        raise NotImplementedError

    def get_line_occupancy_day(self, lines: str | list[str] | None = None, time_interval: int = 60) -> pd.DataFrame:
        raise NotImplementedError

    def get_line_stops(self, lines: str | list[str] | None = None,) -> gpd.GeoDataFrame:
        raise NotImplementedError

    def get_line_stops_day(self, lines: str | list[str] | None = None, time_interval: int = 60) -> gpd.GeoDataFrame:
        raise NotImplementedError

    def get_line_links_occupancy(self,  lines: str | list[str] | None = None) -> gpd.GeoDataFrame:
        raise NotImplementedError

    def get_line_links_occupancy_day(self, lines: str | list[str] | None = None, time_interval: int = 60) -> gpd.GeoDataFrame:
        raise NotImplementedError


# TESTS
if __name__ == "__main__":
    myscen = Scenario()
    thedf = pd.DataFrame(data={"person_id": ["1", "2"]})
    print(thedf)
    myscen.add_trips_df(thedf)
    print(myscen.get_trips_df())
