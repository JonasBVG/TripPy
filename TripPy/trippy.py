import pandas as pd
import json


class Scenario:
    """
    Class that models a transport planning scenario that holds one or more different
    (geo)pandas (Geo)DataFrames containing data on trips, legs and/or network links
    """

    def __init__(
        self,
        code: str = None,
        name: str = "my scenario",
        description: str = None,
        trip_table: pd.DataFrame = None,
        leg_table: pd.DataFrame = None,
        link_table: pd.DataFrame = None,
    ):
        # TODO: Argument type checking
        # TODO: Docstring

        self.code = code
        self.name = name
        self.description = description

        with open("tables_specification.json") as file:
            self.tables_specification = json.load(file)
        self.__trip_table = None
        self.__leg_table = None
        self.__link_table = None

        if trip_table:
            self.add_trip_table(trip_table)
        if leg_table:
            self.add_leg_table(leg_table)
        if link_table:
            self.add_link_table(link_table)

    def add_trip_table(self, trip_table: pd.DataFrame):
        """
        Add a trip table to the scenario
        ---
        trip_table: a pandas DataFrame containing at least one trip
        """
        # TODO: Implement column type checking

        cols_existing = [
            col["name"]
            for col in self.tables_specification["trip_table"]
            if col["name"] in list(trip_table.columns)
        ]
        cols_not_existing = [
            col["name"]
            for col in self.tables_specification["trip_table"]
            if col["name"] not in list(trip_table.columns)
        ]
        cols_not_used = [
            col
            for col in list(trip_table.columns)
            if col not in [c["name"] for c in self.tables_specification["trip_table"]]
        ]
        if len(cols_existing) == 0 or trip_table.size == 0:
            print(list(trip_table.columns))
            raise ValueError(
                "`trip_table` DataFrame does not contain any recognized columns or has no entries"
            )
        if cols_not_used:
            raise UserWarning(
                f"The provided `trip_table` contains the following columns that are not recognized and will not be used:\n{cols_not_used}"
            )

        self.__trip_table = trip_table

        if "trip_id" in cols_not_existing:
            self.__trip_table["trip_id"] = self.__trip_table.index.astype(str)

    def get_trip_table(self):
        return self.__trip_table



# TESTS
if __name__ == "__main__":
    myscen = Scenario()
    thedf = pd.DataFrame(data={"person_id": ["1", "2"]})
    print(thedf)
    myscen.add_trip_table(thedf)
    print(myscen.get_trip_table())
