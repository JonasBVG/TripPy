import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import plotly.io as pio
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

    def _require_comparison(self, func):
        def wrapper():
            assert (
                self._comparison is not None
            ), "You need to add a `comparison` to the Visualizer to use this method"
            func()

        return wrapper

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
        # TODO: Need a way to supply user-configured colors

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
            text="share_display",
        )
        fig.update_traces(textfont_size=14)
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

        fig = px.sunburst(df_conns, path=["order", "mode", "line_id"], values="n")

        return fig

    def plot_drt_occupancy(self, time_interval=60) -> go.Figure:
        """
        Get a `plotly.graph_objects.Figure` stacked area plot showing occupancy of DRT vehicles across the day
        ---
        Arguments:
        - `time_interval`: number of seconds (!) one time bin consists of
        """
        df_occupancy = self._scenario.get_drt_occupancy_day(time_interval=time_interval)

        fig = px.area(
            df_occupancy,
            x="time_index",
            y="n",
            color="occupancy",
            line_group="occupancy",
        )
        return fig

    @_require_comparison
    def plot_modal_shift_sankey(
        self,
        only_to_modes: str | list[str] | None = None,
        policy_scenario_code: str | None = None,
        agg_modes_ruleset: str | None = None,
    ) -> go.Figure:
        
        df_modal_shift: pd.DataFrame = self._comparison(
            policy_scenario_code=policy_scenario_code,
            agg_modes_ruleset=agg_modes_ruleset,
        ).rename(
            columns={
                "main_mode_policy": "target",
                "main_mode_base": "source",
                "n": "value",
            }
        )
        #! Not done!
        # Have to mix things again, we need numbers that replace the modes
        # but at the same time we need labels as well that label the numbers (modes)
        # These labels have to be unique for base and policy, e.g. "car (before)" and "car (after)"
        # which makes things very awkward to handle. Cf. Kenngrößen neu script
        # ~JG

        df_modal_shift["target"] = df_modal_shift["target"] + "_policy"
        df_modal_shift["source"] = df_modal_shift["source"] + "_base"

        all_modes_policy = list(pd.unique(df_modal_shift["target"]))
        all_modes_base = list(pd.unique(df_modal_shift["source"]))
        all_modes = all_modes_policy + all_modes_base
        modes_dict = {i: mode for i, mode in enumerate(all_modes)}
        # mode_labels = all_modes_policy + [l + " →" for l in mode_labels]

        nodes = dict(

        )

        raise NotImplementedError
