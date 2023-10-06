import pandas as pd
import plotly.express as px
import plotly.io as pio
from .scenario import Scenario
from .comparison import Comparison


class Visualizer:
    def __init__(
        self,
        scenario: Scenario | None = None,
        comparison: Comparison | None = None,
    ):
        # TODO: docstring
        # TODO: catch missing scenario/comparison
        self._scenario = scenario
        self._comparison = comparison

    def plot_modal_split(
        self,
        split_type: str = "volume",
        exclude_modes: list[str] = [],
        agg_modes: bool = True,
    ):
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
            split_type, exclude_modes, agg_modes
        )
        df_modal_split["x_dummy"] = ""
        df_modal_split["prc_display"] = df_modal_split.apply(
            lambda x: f"{x['mode']}: {x['prc']*100:1.1f}%", axis=1
        )

        fig = px.bar(
            df_modal_split,
            x="x_dummy",
            y="prc",
            color="mode",
            text="prc_display",
        )
        fig.update_traces(textfont_size=14)
        fig.update_layout(uniformtext_minsize=14, uniformtext_mode="show")

        return fig
