import os
from jinja2 import Environment, FileSystemLoader
import plotly.io as pio
from .scenario import Scenario
from .comparison import Comparison
from .visualizer import Visualizer


class Report:
    def __init__(
        self,
        scenario: Scenario | None = None,
        comparison: Comparison | None = None,
    ) -> None:
        self._scenario = scenario
        self._comparison = comparison

        file_loader = FileSystemLoader("templates")
        env = Environment(loader=file_loader)
        self._document_template = env.get_template("report_structure.jinja")

        self._visualizer = Visualizer(scenario, comparison)
        self._blocks = []

    def add_mode_analysis(self):
        file_loader = FileSystemLoader("templates")
        env = Environment(loader=file_loader)
        template = env.get_template("modal_split.jinja")

        df_ms = self._scenario.get_modal_split(agg_modes=False)
        fig_ms = self._visualizer.plot_modal_split()
        fig_ms_html = pio.to_html(fig_ms)

        df_ms_show = df_ms[["mode", "n", "prc"]]
        df_ms_html = df_ms.to_html()

        self._blocks.append(
            {
                "title": "Modal Split",
                "content": template.render(
                    plot_modal_split=fig_ms_html, table_modal_split=df_ms_html
                ),
            }
        )

    def compile_html(self, filepath: str = "reports/report.html"):
        html_res = self._document_template.render(blocks=self._blocks)

        if not os.path.exists(os.path.dirname(filepath)):
            print(
                f"Folder '{os.path.dirname(filepath)}' does not exist. Creating folder."
            )
            os.mkdir(os.path.dirname(filepath))

        with open(os.path.normpath(filepath), "w", encoding="utf8") as f:
            f.write(html_res)
