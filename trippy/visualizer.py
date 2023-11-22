import json
import warnings
import folium
import pandas as pd
import geopandas as gpd
import plotly.express as px
import plotly.graph_objects as go
import plotly.io as pio
from folium.plugins import FastMarkerCluster, HeatMap, GroupedLayerControl
from .scenario import Scenario
from .drtscenario import DRTScenario
from .comparison import Comparison


class Visualizer:
    def __init__(
        self,
        scenario: Scenario | DRTScenario | None = None,
        comparison: Comparison | None = None,
    ):
        # TODO: docstring
        # TODO: catch missing scenario/comparison
        self._scenario = scenario
        self._comparison = comparison
        self.__colors = self.__read_colors()

        self._settings = {"modes_colorset": "modes", "lines_colorset": "lines"}

    def __read_colors(self) -> dict:
        try:
            with open("colors.json", encoding="utf-8") as file:
                colors = json.load(file)
            for color_set in colors["colorsets"]:
                for el in colors["colorsets"][color_set]:
                    color_name = colors["colorsets"][color_set][el]
                    color_hex = colors["colors"][color_name]
                    colors["colorsets"][color_set][el] = color_hex
        except FileNotFoundError:
            colors = None
            warnings.warn(
                UserWarning(
                    "No `colors.json` file found. Continuing with random colors..."
                )
            )
        return colors

    def add_comparison(self, comparison: Comparison):
        self._comparison = comparison

    def plot_modal_split(
        self,
        split_type: str = "volume",
        exclude_modes: list[str] = [],
        agg_modes_ruleset: str | None = None,
    ) -> go.Figure:
        """
        Get a `plotly.graph_objects.Figure` bar plot showing the modal split of a scenario or a comparison
        ---
        Arguments:
        - `split_type`: 'volume', 'performance'. Using 'volume' will return the number of trips based on their `main_mode` and needs `trips_df`, using 'performance' will return person kilometers based on the `legs_df`
        - `exclude_modes`: specify a list of mode names to be disregarded in the modal split. Note that these modes have to be supplied in the form they exist in the `trips_df`, not any aggregated form
        - `agg_modes`: whether to aggregate the modes in the `trips_df` and `legs_df` according to the assignment in the scenario's/comparison's settings (key `mode_aggregation_rules`)
        """

        df_modal_split = self._scenario.get_modal_split(
            split_type, exclude_modes, agg_modes_ruleset
        )
        df_modal_split["x_dummy"] = ""
        df_modal_split["share_display"] = df_modal_split.apply(
            lambda x: f"{x['mode']}: {x['share']*100:1.1f}%", axis=1
        )

        fig = px.bar(
            df_modal_split,
            x="x_dummy",
            y="share",
            color="mode",
            color_discrete_map=self.__colors["colorsets"][
                self._settings["modes_colorset"]
            ]
            if self.__colors is not None
            else None,
            text="share_display",
        )

        fig = self.__style_fig(fig, "", "Anteil", x_grid=False)

        fig.update_traces(textfont_size=14, marker=dict(line=dict(width=0)))
        fig.update_layout(uniformtext_minsize=14, uniformtext_mode="show")

        return fig

    def plot_drt_intermodal_connections(self) -> go.Figure:
        """
        Get a `plotly.graph_objects.Figure` sunburst plot showing intermodal connections from/to drt trips
        ---
        """
        df_conns = self._scenario.get_drt_intermodal_analysis(
            agg_modes_ruleset="vsys"
        ).query("order != 'direct'")

        fig = px.sunburst(
            df_conns,
            path=["order", "mode", "line_id"],
            values="n",
            color="order",
            color_discrete_sequence=[
                self.__colors["colors"]["blutorange"],
                self.__colors["colors"]["türkisgrün"],
            ],
        )

        fig = self.__style_fig(fig, None, None)

        return fig

    def plot_drt_occupancy(self, time_interval: int = 60) -> go.Figure:
        """
        Get a `plotly.graph_objects.Figure` stacked area plot showing occupancy of DRT vehicles across the day
        ---
        Arguments:
        - `time_interval`: number of seconds (!) one time bin consists of
        """

        df_occupancy = self._scenario.get_drt_occupancy_day(
            time_interval=time_interval
        ).sort_values("occupancy", ascending=False)

        df_occupancy["time_index"] = df_occupancy["time_index"] * (time_interval / 60)

        fig = px.area(
            df_occupancy,
            x="time_index",
            y="n",
            color="occupancy",
            line_group="occupancy",
            category_orders={
                "occupancy": ["0", "1", "2", "3", "4", "5", "6", "7", "8"]
            },
        )
        fig.for_each_trace(lambda trace: trace.update(fillcolor=trace.line.color))

        fig = self.__style_fig(
            fig, x_title="Uhrzeit (Stunde)", y_title="Anzahl Fahrzeuge"
        )

        return fig

    def plot_modal_shift_sankey(
        self,
        only_from_modes: str | list[str] | None = None,
        only_to_modes: str | list[str] | None = None,
        policy_scenario_code: str | None = None,
        agg_modes_ruleset: str | None = None,
    ) -> go.Figure:
        # TODO: Docstring
        # TODO: In docstring, mention that only_from/to_modes has to be the aggregated version (unlike in some other methods)

        # TODO: Think about moving the only_from_modes (and only_to_modes) functionality into the Comparison.get_modal_shift() method
        # TODO: ... to keep it consistent with other methods that behave the same way

        df_modal_shift: pd.DataFrame = self._comparison.get_modal_shift(
            policy_scenario_code=policy_scenario_code,
            agg_modes_ruleset=agg_modes_ruleset,
        ).rename(
            columns={
                "n": "value",
            }
        )

        if only_from_modes is not None:
            if isinstance(only_from_modes, str):
                df_modal_shift = df_modal_shift[
                    df_modal_shift["main_mode_base"] == only_from_modes
                ]
            elif isinstance(only_from_modes, list):
                df_modal_shift = df_modal_shift[
                    df_modal_shift["main_mode_base"].isin(only_from_modes)
                ]
            else:
                raise ValueError("`only_from_modes` has to be a string or a list")
        if only_to_modes is not None:
            if isinstance(only_to_modes, str):
                df_modal_shift = df_modal_shift[
                    df_modal_shift["main_mode_policy"] == only_to_modes
                ]
            elif isinstance(only_to_modes, list):
                df_modal_shift = df_modal_shift[
                    df_modal_shift["main_mode_policy"].isin(only_to_modes)
                ]
            else:
                raise ValueError("`only_to_modes` has to be a string or a list")

        # The nodes (ie. the modes) have to be unique so we have to rename them
        # to distinguish between base case and policy case
        df_modal_shift["target"] = df_modal_shift["main_mode_policy"] + " (policy)"
        df_modal_shift["source"] = df_modal_shift["main_mode_base"] + " (base)"

        # Now we just extract the unique modes (including the suffixes) as nodes
        # Note that the order will matter
        all_modes_policy = list(pd.unique(df_modal_shift["target"]))
        all_modes_base = list(pd.unique(df_modal_shift["source"]))
        all_modes = all_modes_policy + all_modes_base

        # For the colors we access the mode names without the (after) and (before)
        # so we can match them with the colors
        all_modes_raw = list(pd.unique(df_modal_shift["main_mode_policy"])) + list(
            pd.unique(df_modal_shift["main_mode_base"])
        )
        mode_colors = [
            self.__colors["colorsets"]["modes"][mode] for mode in all_modes_raw
        ]
        mode_indices_to_colors = {
            i: self.__hex_to_rgba(color[1:], 0.5) for i, color in enumerate(mode_colors)
        }

        # Dict to replace modes with numbers
        number_labels = {mode: i for i, mode in enumerate(all_modes)}
        df_modal_shift = df_modal_shift.replace(number_labels)

        df_modal_shift["link_color"] = df_modal_shift["source"].apply(
            lambda mode_index: mode_indices_to_colors[mode_index]
        )

        nodes = dict(
            pad=5, thickness=20, line={"width": 0}, label=all_modes, color=mode_colors
        )
        links = dict(
            source=df_modal_shift["source"],
            target=df_modal_shift["target"],
            value=df_modal_shift["value"],
            color=df_modal_shift["link_color"],
        )

        fig = go.Figure(
            data=[
                go.Sankey(
                    node=nodes,
                    link=links,
                    type="sankey",
                    orientation="h",
                )
            ]
        )

        fig = self.__style_fig(fig, x_title=None, y_title=None)

        return fig

    def plot_eta_day(self, time_interval: int = 60) -> go.Figure:
        # TODO: Docstring

        df_eta_day = self._scenario.get_eta_day(time_interval)
        df_eta_day.iloc[:, 1:] = df_eta_day.iloc[:, 1:].apply(lambda x: x / 60)
        df_eta_day["time_index"] = df_eta_day["time_index"] * (
            time_interval / 60
        )  # transform to hours

        fig = go.Figure()
        # first add max value line
        fig.add_trace(
            go.Scatter(
                x=df_eta_day["time_index"],
                y=df_eta_day["p_95"],
                fill=None,
                mode="lines",
                line_color="lightgrey",
                showlegend=False,
            )
        )
        # then add min value line and fill between the two
        fig.add_trace(
            go.Scatter(
                x=df_eta_day["time_index"],
                y=df_eta_day["p_5"],
                fill="tonexty",
                mode="lines",
                line_color="lightgrey",
                name="5- bis 95-Perzentil",
            )
        )
        # finally add mean line and median line
        fig.add_trace(
            go.Scatter(
                x=df_eta_day["time_index"],
                y=df_eta_day["mean"],
                fill=None,
                mode="lines",
                line_color="blue",
                name="Durchschnitt",
            )
        )
        fig.add_trace(
            go.Scatter(
                x=df_eta_day["time_index"],
                y=df_eta_day["median"],
                fill=None,
                mode="lines",
                line_color="orange",
                name="Median",
            )
        )

        fig = self.__style_fig(fig, x_title="Uhrzeit [Stunde]", y_title="ETA [min]")

        return fig

    def __map_locations(
        self,
        orig_gdf: gpd.GeoDataFrame,
        dest_gdf: gpd.GeoDataFrame,
        zones: gpd.GeoDataFrame | None = None,
    ):
        orig_gdf = orig_gdf.to_crs("EPSG:4326")
        dest_gdf = dest_gdf.to_crs("EPSG:4326")

        m = folium.Map(
            location=[orig_gdf["geometry"].y.mean(), orig_gdf["geometry"].x.mean()],
            zoom_start=12,
            zoomDelta=0.5,
        )

        folium.TileLayer(
            "https://tileserver.memomaps.de/tilegen/{z}/{x}/{y}.png",
            name="ÖPNV Map",
            show=False,
            attr='Map <a href="https://memomaps.de/">memomaps.de</a> <a href="http://creativecommons.org/licenses/by-sa/2.0/">CC-BY-SA</a>, map data &copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors',
        ).add_to(m)
        folium.TileLayer(
            "CartoDB dark_matter",
            name="Dark Map",
            show=False,
        ).add_to(m)

        heatmap_orig = HeatMap(
            name="Startorte: Heatmap",
            data=list(zip(orig_gdf["geometry"].y, orig_gdf["geometry"].x)),
            min_opacity=0.2,
        )
        heatmap_dest = HeatMap(
            name="Zielorte: Heatmap",
            data=list(zip(dest_gdf["geometry"].y, dest_gdf["geometry"].x)),
            min_opacity=0.2,
            show=False,
        )

        marker_cluster_orig = FastMarkerCluster(
            name="Startorte: Punkte",
            data=list(zip(orig_gdf["geometry"].y, orig_gdf["geometry"].x)),
            options=dict(singleMarkerMode=True),
        )
        marker_cluster_dest = FastMarkerCluster(
            name="Zielorte: Punkte",
            data=list(zip(dest_gdf["geometry"].y, dest_gdf["geometry"].x)),
            show=False,
            options=dict(singleMarkerMode=True),
        )

        if zones is not None:
            zones_poly = folium.GeoJson(
                name="Gebiet",
                data=zones["geometry"],
                style_function=lambda feature: {
                    "fillColor": self.__hex_to_rgba("000000", 0),
                    "color": "#0313fc",
                    "weight": 3,
                },
            )
            zones_poly.add_to(m)

        heatmap_orig.add_to(m)
        marker_cluster_orig.add_to(m)
        heatmap_dest.add_to(m)
        marker_cluster_dest.add_to(m)

        folium.LayerControl(collapsed=False, sortLayers=False).add_to(m)

        return m

    def map_drt_ride_locations(self):
        # TODO: Docstring
        orig_legs = self._scenario.get_drt_leg_locations()
        dest_legs = self._scenario.get_drt_leg_locations(direction="destination")

        m = self.__map_locations(
            orig_gdf=orig_legs,
            dest_gdf=dest_legs,
            zones=self._scenario.get_operating_zone(),
        )

        return m

    def map_trip_locations(self):
        # TODO: Docstring
        orig_trips = self._scenario.get_trip_locations()
        orig_trips = orig_trips[
            orig_trips["main_mode"] == self._scenario.get_settings()["drt_mode"]
        ]
        dest_trips = self._scenario.get_trip_locations(direction="destination")
        dest_trips = dest_trips[
            dest_trips["main_mode"] == self._scenario.get_settings()["drt_mode"]
        ]

        m = self.__map_locations(orig_gdf=orig_trips, dest_gdf=dest_trips)

        return m

    def map_zone(self):
        # TODO: Docstring
        m = folium.Map(
            tiles="https://tileserver.memomaps.de/tilegen/{z}/{x}/{y}.png",
            attr='Map <a href="https://memomaps.de/">memomaps.de</a> <a href="http://creativecommons.org/licenses/by-sa/2.0/">CC-BY-SA</a>, map data &copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors',
            location=[
                self._scenario.get_operating_zone().centroid.y.mean(),
                self._scenario.get_operating_zone().centroid.x.mean(),
            ],
            zoom_start=11,
            zoom_control=False,
            scrollWheelZoom=False,
            dragging=False,
        )

        zones_poly = folium.GeoJson(
            name="Gebiet",
            data=self._scenario.get_operating_zone()["geometry"],
            style_function=lambda feature: {
                "fillColor": "#0313fc",
                "color": "#0313fc",
                "weight": 5,
            },
        )
        zones_poly.add_to(m)

        return m

    @staticmethod
    def __hex_to_rgba(hex_code: str, opacity: float = 1) -> str:
        """Use without a # in front of the hex color code"""
        return "rgba" + str(
            tuple(int(hex_code[i : i + 2], 16) for i in (0, 2, 4)) + (opacity,)
        )

    @staticmethod
    def __style_fig(
        fig: go.Figure,
        x_title: str | None = "x",
        y_title: str | None = "y",
        x_grid: bool = True,
        y_grid: bool = True,
        bg_transparent: bool = False,
    ):
        fig = fig.update_layout(
            xaxis_title=x_title,
            yaxis_title=y_title,
            font=dict(family="TransitBackNeg-Normal"),
            plot_bgcolor="white",
            paper_bgcolor="white",
        )

        if bg_transparent:
            fig.update_layout(
                plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)"
            )

        fig.update_xaxes(showgrid=True, gridwidth=1, gridcolor="lightgrey")
        fig.update_yaxes(showgrid=True, gridwidth=1, gridcolor="lightgrey")

        return fig
