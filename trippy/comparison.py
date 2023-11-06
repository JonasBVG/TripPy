import numpy as np
import pandas as pd
from .scenario import Scenario
from .drtscenario import DRTScenario


class Comparison:
    # TODO: Docstring
    def __init__(
        self, base_scenario: Scenario | DRTScenario, policy_scenarios: Scenario | DRTScenario | list[Scenario|DRTScenario]
    ):
        # TODO: Better make this configurable:
        self._settings = base_scenario._settings

        self._base_scenario = base_scenario

        if isinstance(policy_scenarios, list):
            self._policy_scenarios = {sc.code: sc for sc in policy_scenarios}
        else:
            self._policy_scenarios = {policy_scenarios.code: policy_scenarios}

    def get_modal_shift(
        self,
        policy_scenario_code: str | None = None,
        agg_modes_ruleset: str | None = None,
    ):
        # TODO: Docstring
        if policy_scenario_code is not None:
            try:
                policy_scenario = self._policy_scenarios[policy_scenario_code]
            except IndexError as exc:
                raise ValueError(
                    f"Scenario with code '{policy_scenario_code}' is not contained in the provided policy scenarios"
                ) from exc
        else:
            policy_scenario = list(self._policy_scenarios.values())[0]
            print(f"Using scenario with code '{policy_scenario.code}'")

        policy_scenario._require_table("trips_df", ["trip_id", "person_id", "main_mode"])
        self._base_scenario._require_table("trips_df", ["trip_id", "person_id", "main_mode"])

        df_modal_shift = (
            policy_scenario._trips_df[["trip_id", "person_id", "main_mode"]]
            .merge(
                self._base_scenario._trips_df[["trip_id", "person_id", "main_mode"]],
                how="left",
                on=["trip_id", "person_id"],
                suffixes=["_policy", "_base"],
            )
            .replace(
                self._settings["mode_aggregation_rulesets"][agg_modes_ruleset]
                if agg_modes_ruleset is not None
                else {}
            )
            .groupby(["main_mode_base", "main_mode_policy"])
            .size()
            .reset_index(name="n")
        )

        return df_modal_shift
