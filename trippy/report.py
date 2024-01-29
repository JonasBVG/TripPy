import os
import plotly.io as pio
import pandas as pd
from jinja2 import Environment, FileSystemLoader
from .trippy import format_number
from .scenario import Scenario
from .drtscenario import DRTScenario
from .comparison import Comparison
from .visualizer import Visualizer


class Report:
    # TODO: Make this usable for non-drt scenarios

    # TODO: Refine structure and methods
    # Right now it's pretty static and only allows carefully pre-designed blocks
    # Need to make this more flexible and create verbose methods to add modules to blocks
    # A way to configure the report via a configuration file would be very convenient
    # Also the whole language thing needs configurability, rn it's only German

    def __init__(
        self,
        title: str = "My Report",
        scenario: Scenario | DRTScenario | None = None,
        comparison: Comparison | None = None,
    ) -> None:
        self.title = title

        self._scenario = scenario
        self._comparison = comparison

        file_loader = FileSystemLoader("templates")
        self._env = Environment(loader=file_loader)

        self._visualizer = Visualizer(scenario, comparison)
        self._blocks = []

    def _add_block(self, title: str, content: str):
        self._blocks.append({"title": title, "content": content})

    def add_overview(self):
        template_overview = self._env.get_template("drt_overview.jinja")
        content = template_overview.render(
            scenario_name=self._scenario.name,
            scenario_description=self._scenario.description,
            fleet_size=format_number(self._scenario.fleet_size),
            drt_rides=format_number(self._scenario.get_n_drt_rides()),
            eta=format_number(self._scenario.get_eta().iloc[0]["mean"], False, 2),
            map_operating_zone = self._visualizer.map_zone()._repr_html_()
        )
        self._add_block("Szenario", content)


    def add_mode_analysis(self):
        template_modal_split = self._env.get_template("modal_split.jinja")
        template_modal_shift = self._env.get_template("modal_shift.jinja")

        # get modal split DataFrame and Figure
        df_ms_vol = self._scenario.get_modal_split(agg_modes_ruleset="all_pt")
        df_ms_perf = self._scenario.get_modal_split(split_type="performance", agg_modes_ruleset="all_pt")
        df_ms_perf["n"] = df_ms_perf["n"] / 1000 # m -> km
        fig_ms = self._visualizer.plot_modal_split(split_type="both", agg_modes_ruleset="all_pt")
        fig_ms_html = pio.to_html(fig_ms)

        df_ms = (df_ms_vol
                 .merge(df_ms_perf, "left", "mode", suffixes=["_vol", "_perf"]))

        df_ms_show = df_ms[["mode", "n_vol", "share_vol", "n_perf", "share_perf"]].rename(
            columns={
                "mode": "Verkehrsmittel",
                "n_vol": "Anzahl Trips",
                "share_vol": "Anteil Trips",
                "n_perf": "Personenkilometer",
                "share_perf": "Anteil Pkm",
            }
        )
        df_ms_show["Anzahl Trips"] = df_ms_show["Anzahl Trips"].apply(lambda x: format_number(x, False, 0))
        df_ms_show["Anteil Trips"] = df_ms_show["Anteil Trips"].apply(lambda x: format_number(x, True, 1))
        df_ms_show["Personenkilometer"] = df_ms_show["Personenkilometer"].apply(lambda x: format_number(x, dec_places=0))
        df_ms_show["Anteil Pkm"] = df_ms_show["Anteil Pkm"].apply(lambda x: format_number(x, True, 1))
        df_ms_html = df_ms_show.to_html(index=False)

        content = template_modal_split.render(
            plot_modal_split=fig_ms_html, table_modal_split=df_ms_html
        )

        if self._comparison is not None:
            fig_mshift = self._visualizer.plot_modal_shift_sankey(
                agg_modes_ruleset="all_pt"
            )
            fig_mshift_html = pio.to_html(fig_mshift)
            content += template_modal_shift.render(plot_modal_shift=fig_mshift_html)

        self._add_block("Verkehrsmodi", content)

    def add_drt_analysis(self):
        assert isinstance(
            self._scenario, DRTScenario
        ), "Scenario in this Visualizer is not a DRTScenario"

        self.__add_operator_perspective_analysis()
        self.__add_passenger_perspective_analysis()
        # self.__add_holistic_perspective_analysis() #! Not yet implemented

    def __add_operator_perspective_analysis(self) -> None:
        template_operator_stats = self._env.get_template("drt_operator_stats.jinja")
        template_occupancy = self._env.get_template("drt_occupancy.jinja")
        template_heatmap = self._env.get_template("drt_heatmap.jinja")

        # KPIs
        fleet_size = self._scenario.fleet_size
        n_drt_rides = self._scenario.get_n_drt_rides()
        drt_occupancy = self._scenario.get_mean_drt_occupancy()
        all_veh_km = self._scenario.get_vehicle_km()
        drt_veh_km = all_veh_km[
            all_veh_km["mode"] == self._scenario.get_setting("drt_mode")
        ]["n"].values[0]
        drt_km_per_veh = drt_veh_km / fleet_size
        # TODO: km empty, km occupied
        all_person_km = self._scenario.get_person_km()
        drt_person_km = all_person_km[
            all_person_km["mode"] == self._scenario.get_setting("drt_mode")
        ]["n"].values[0]

        # TODO: Make this more elegant and dynamic
        df_operator_stats = pd.DataFrame(
            data={
                "KPI": [
                    "Flottengröße",
                    "Anzahl Beförderungen",
                    "Mittlerer Besetzungsgrad",
                    "DRT-Fahrzeugkilometer",
                    "km pro Fahrzeug",
                    "DRT-Personenkilometer",
                ],
                "Wert": [
                    format_number(fleet_size, False, 0),
                    format_number(n_drt_rides, False, 0),
                    format_number(drt_occupancy, False, 2),
                    format_number(drt_veh_km, False, 0),
                    format_number(drt_km_per_veh, False, 1),
                    format_number(drt_person_km, False, 0),
                ],
            }
        )

        table_operator_stats = df_operator_stats.to_html(index=False)
        fig_occupancy_day = pio.to_html(self._visualizer.plot_drt_occupancy())
        map_od = self._visualizer.map_drt_ride_locations()._repr_html_()

        content = (
            template_operator_stats.render(
                table_operator_stats=table_operator_stats,
            )
            + template_occupancy.render(
                plot_occupancy_day=fig_occupancy_day,
            )
            + template_heatmap.render(map_od=map_od)
        )

        self._add_block("Betreibersicht", content)

    def __add_passenger_perspective_analysis(self) -> None:
        # TODO: Histograms (also todo in visualizer)

        template_passenger_stats = self._env.get_template("drt_passenger_stats.jinja")
        template_eta = self._env.get_template("drt_eta.jinja")
        template_travel_time = self._env.get_template("drt_travel_time.jinja")
        template_travel_distance = self._env.get_template("drt_travel_distance.jinja")
        # template_access_egress = self._env.get_template("drt_access_egress.jinja")

        content = ""

        # passenger stats module
        df_eta = self._scenario.get_eta().drop(columns=["mode", "travel_part"])
        df_eta["KPI"] = "Wartezeit (ETA) [min]"

        df_travel_time = self._scenario.get_travel_time_stats(stats_for="legs")
        df_travel_time_drt = df_travel_time[
            (df_travel_time["mode"] == self._scenario.get_setting("drt_mode"))
            & (df_travel_time["travel_part"] == "travel_time")
        ].drop(columns=["mode", "travel_part"])
        df_travel_time_drt["KPI"] = "DRT-Fahrtzeit [min]"

        df_travel_distance = self._scenario.get_travel_distance_stats(stats_for="legs")
        df_travel_distance_drt = df_travel_distance[
            df_travel_distance["mode"] == self._scenario.get_setting("drt_mode")
        ].drop(columns=["mode"])
        df_travel_distance_drt.iloc[[0]] = (
            df_travel_distance_drt.iloc[[0]] / 1000
        )  # TODO: don't hardcode this
        df_travel_distance_drt["KPI"] = "DRT-Fahrtdistanz [km]"

        df_passenger_stats = pd.concat(
            [df_eta, df_travel_time_drt, df_travel_distance_drt]
        )
        new_column_order = (
            [list(df_passenger_stats.columns)[-1]]
            + list(df_passenger_stats.columns)[0:-1]
        )  # move KPI column to first position
        df_passenger_stats_html = df_passenger_stats.reindex(
            new_column_order, axis=1
        ).to_html(index=False)
        content += template_passenger_stats.render(
            table_passenger_stats=df_passenger_stats_html
        )

        # ETA module
        fig_eta_day_html = self._visualizer.plot_eta_day().to_html()
        content += template_eta.render(plot_eta_day=fig_eta_day_html)

        # travel time module
        content += template_travel_time.render()

        # travel distance module
        content += template_travel_distance.render()

        # access/egress module
        #! Problem: This method currently return access/egress distances for the whole trip
        #! including potential pt legs in the same trip if it is intermodal.
        # TODO: Need a dedicated DRTScenario version of this that is based on legs -> more complicated
        # df_access_egress = self._scenario.get_access_egress_distances()

        self._add_block("Kund*innen-Sicht", content)

    def __add_holistic_perspective_analysis(self) -> None:
        # gesamtverkehrsplanerisch
        raise NotImplementedError

    def add_drt_intermodal_analysis(self):
        # TODO: Integrate this with another block. This should only be a module

        assert isinstance(
            self._scenario, DRTScenario
        ), "Scenario in this Visualizer is not a DRTScenario"

        template = self._env.get_template("intermodal.jinja")

        fig_intermodal = self._visualizer.plot_drt_intermodal_connections()

        content = template.render(plot_intermodal=pio.to_html(fig_intermodal))

        self._add_block("Intermodalität", content)

    def compile_html(self, filepath: str = "reports/report.html"):
        template = self._env.get_template("report_structure.jinja")
        html_res = template.render(blocks=self._blocks, title=self.title)

        if not os.path.exists(os.path.dirname(filepath)):
            print(
                f"Folder '{os.path.dirname(filepath)}' does not exist. Creating folder."
            )
            os.mkdir(os.path.dirname(filepath))

        with open(os.path.normpath(filepath), "w", encoding="utf8") as f:
            f.write(html_res)
