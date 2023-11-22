import os
import plotly.io as pio
import pandas as pd
from jinja2 import Environment, FileSystemLoader
from .scenario import Scenario
from .drtscenario import DRTScenario
from .comparison import Comparison
from .visualizer import Visualizer


class Report:
    def __init__(
        self,
        scenario: Scenario | DRTScenario | None = None,
        comparison: Comparison | None = None,
    ) -> None:
        self._scenario = scenario
        self._comparison = comparison

        file_loader = FileSystemLoader("templates")
        self._env = Environment(loader=file_loader)

        self._visualizer = Visualizer(scenario, comparison)
        self._blocks = []

    def _add_block(self, title: str, content: str):
        self._blocks.append({"title": title, "content": content})

    def add_mode_analysis(self):
        template_modal_split = self._env.get_template("modal_split.jinja")
        template_modal_shift = self._env.get_template("modal_shift.jinja")

        # get modal split DataFrame and Figure
        df_ms = self._scenario.get_modal_split(agg_modes_ruleset="all_pt")
        fig_ms = self._visualizer.plot_modal_split(agg_modes_ruleset="all_pt")
        fig_ms_html = pio.to_html(fig_ms)

        df_ms_show = df_ms[["mode", "n", "share"]].rename(
            columns={
                "mode": "Verkehrsmittel",
                "n": "Anzahl Trips",
                "share": "Anteil",
            }
        )
        df_ms_html = df_ms_show.to_html()

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
            all_veh_km["mode"] == self._scenario.get_settings()["drt_mode"]
        ]["n"].values[0]
        drt_km_per_veh = drt_veh_km / fleet_size
        # TODO: km empty, km occupied
        all_person_km = self._scenario.get_person_km()
        drt_person_km = all_person_km[
            all_person_km["mode"] == self._scenario.get_settings()["drt_mode"]
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
                    fleet_size,
                    n_drt_rides,
                    drt_occupancy,
                    drt_veh_km,
                    drt_km_per_veh,
                    drt_person_km,
                ],
            }
        )

        table_operator_stats = df_operator_stats.to_html()
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

        self._add_block("DRT-Betreibersicht", content)

    def __add_passenger_perspective_analysis(self) -> None:
        # TODO: Histograms (also todo in visualizer)

        template_eta = self._env.get_template("drt_eta.jinja")
        template_travel_time = self._env.get_template("drt_travel_time.jinja")
        template_travel_distance = self._env.get_template("drt_travel_distance.jinja")
        # template_access_egress = self._env.get_template("drt_access_egress.jinja")

        content = ""

        # ETA module
        df_eta = self._scenario.get_eta()
        df_eta_html = df_eta.melt(
            value_vars=df_eta.columns, var_name="ETA", value_name="Minuten"
        ).to_html()
        fig_eta_html = self._visualizer.plot_eta_day().to_html()

        content += template_eta.render(plot_eta=fig_eta_html, table_eta=df_eta_html)

        # travel time module
        df_travel_time = self._scenario.get_travel_time_stats(stats_for="legs")
        df_travel_time_drt = df_travel_time[
            (df_travel_time["mode"] == self._scenario.get_setting("drt_mode"))
            & (df_travel_time["travel_part"] == "travel_time")
        ].drop(columns=["mode", "travel_part"])
        df_travel_time_drt_html = df_travel_time_drt.melt(
            value_vars=df_travel_time_drt.columns,
            var_name="Fahrtzeit",
            value_name="Minuten",
        ).to_html()

        content += template_travel_time.render(
            table_travel_time=df_travel_time_drt_html
        )

        # travel distance module
        df_travel_distance = self._scenario.get_travel_distance_stats(stats_for="legs")
        df_travel_distance_drt = df_travel_distance[
            df_travel_distance["mode"] == self._scenario.get_setting("drt_mode")
        ].drop(columns=["mode"])
        df_travel_distance_drt_html = df_travel_distance_drt.melt(
            value_vars=df_travel_distance_drt.columns,
            var_name="Fahrtdistanz",
            value_name="Kilometer",
        )
        df_travel_distance_drt_html["Kilometer"] = (
            df_travel_distance_drt_html["Kilometer"] / 1000
        )
        df_travel_distance_drt_html = df_travel_distance_drt_html.to_html()

        content += template_travel_distance.render(
            table_travel_distance=df_travel_distance_drt_html
        )

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

        self._add_block("DRT-Intermodalität", content)

    def compile_html(self, filepath: str = "reports/report.html"):
        template = self._env.get_template("report_structure.jinja")
        html_res = template.render(blocks=self._blocks)

        if not os.path.exists(os.path.dirname(filepath)):
            print(
                f"Folder '{os.path.dirname(filepath)}' does not exist. Creating folder."
            )
            os.mkdir(os.path.dirname(filepath))

        with open(os.path.normpath(filepath), "w", encoding="utf8") as f:
            f.write(html_res)
