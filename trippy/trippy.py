import os
import json
import numpy as np
import pandas as pd

import re #! This is only neccessary for bvg_line_renamer()
# from scenario import Scenario
# from drtscenario import DRTScenario
# from reporter import Report


# In case VS Code's semantic syntax highlighting (i.e. coloring module names, methods etc.) does not work anymore,
# try switching to an a few weeks older version of the Pylance extension. This worked for me.

def bvg_line_renamer(line_id: str, mode: str):
    if mode == "100":  # Nicht-BVG-Bus
        if re.search("---", line_id):
            return re.search(r'---(.*)', line_id).group(1)
        elif re.search("___", line_id):
            return re.search(r'___(.*)', line_id).group(1)
        else:
            return re.search(r'^[0-9]*', line_id).group(0)
    elif mode == "300" or mode == "400":  # Nicht-BVG-Tram or Fähre
        return re.search(r'---([a-zA-Z0-9]+)$', line_id).group(1)
    elif mode == "500":  # S-Bahn
        return re.search(r'(S[a-zA-Z0-9]+)', line_id).group(1)
    elif mode == "600":  # RV
        return re.search(r'[a-zA-Z]+[0-9]*', line_id).group(0)
    elif mode in ["700", "800"]:  # FV (for unknown modes)
        return "FV"
    elif mode == "BVB10":  # normale + Nachtbusse
        prefix = re.search(r'^[A-Z]*', line_id).group(0)
        number = re.search(r'[0-9]+', line_id).group(0)
        return prefix + str(int(number))
    elif mode == "BVB10M":  # Metrobusse
        return re.search(r'^M[0-9]+', line_id).group(0)
    elif mode == "BVB10X":  # Expressbusse
        number = re.search(r'[0-9]+', line_id).group(0)
        return "X" + str(int(number))
    elif mode == "BVT30":  # Normale Tram
        return re.search(r'^[0-9]+', line_id).group(0)
    elif mode == "BVT30M":  # Metrotram
        return re.search(r'^M[0-9]+', line_id).group(0)
    elif mode == "BVU20":  # U-Bahn
        return re.search(r'^[a-zA-Z0-9]+', line_id).group(0)
    elif mode == "BVF100":  # Fähre
        return re.search(r'F[0-9]+', line_id).group(0)
    elif mode == "walk":
        return mode

def convert_senozon_to_trippy(df: pd.DataFrame, table_type="tripTable"):
    """
    Convert the Senozon column names to the trippy standard.

    """
    if table_type == "tripTable":
        # TODO: mainMode + otherModes -> all_modes

        rename_dict = {
            "id": "trip_id",
            "personId": "person_id",
            "mainMode": "main_mode",
            "containsDrt": "contains_drt",
            "fromActType": "from_act_type",
            "toActType": "to_act_type",
            "tripStartTime": "start_time",
            "tripEndTime": "end_time",
            "beelinDistance": "beeline_distance",
            "routedDistance": "routed_distance",
            "travelTime": "travel_time",
            "totalWaitingTime": "waiting_time",
            "accessTravelTime": "access_time",
            "accessDistance": "access_distance",
            "accessWaitingTime": "access_waiting_time",
            "egressTravelTime": "egress_time",
            "egressDistance": "egress_distance",
            "egressWaitingTime": "egress_waiting_time",
            "fromX": "from_x",
            "fromY": "from_y",
            "toX": "to_x",
            "toY": "to_y",
            "numStages": "legs_count",
        }
    elif table_type == "legTable":
        rename_dict = {
            "stageId": "leg_id",
            "tripId": "trip_id",
            "personId": "person_id",
            "fromActType": "from_act_type",
            "toActType": "to_act_type",
            "startTime": "start_time",
            "endTime": "end_time",
            "lineId": "line_id",
            "beelineDistance": "beeline_distance",
            "routedDistance": "routed_distance",
            "travelTime": "travel_time",
            "waitingTime": "waiting_time",
            "fromX": "from_x",
            "fromY": "from_y",
            "toX": "to_x",
            "toY": "to_y",
        }
    elif table_type == "linksTable":
        rename_dict = {
            "personId": "person_id",
            "vehicleId": "vehicle_id",
            "agentType": "agent_type",
            "linkId": "link_id",
            "lineId": "line_id",
            "linkEnterTime": "link_enter_time",
            "linkLeaveTime": "link_leave_time",
            "fromStopId": "from_stop_id",
            "toStopId": "to_stop_id",
            "distanceTravelledOnLink": "distance_travelled",
            "linkEnterX": "link_enter_x",
            "linkEnterY": "link_enter_y",
            "linkLeaveX": "link_leave_x",
            "linkLeaveY": "link_leave_y"
        }
    else:
        raise NotImplementedError
    return df.rename(columns=rename_dict)

def format_number(num: float|int, percent: bool = False, dec_places: int = 0) -> str:
        """
        Returns a number as a string formatted with German number notation using dot as thousands separator and comma as decimal separator
        ---
        Arguments:
        - num: the number to format
        - percent: whether to use percent notation num*100%
        - dec_places: the number of decimal places after the comma to round to
        """
        if percent:
            format_str = "{:,." + str(dec_places) + "%}"
        else:
            format_str = "{:,." + str(dec_places) + "f}"
            
        formatted_num = format_str.format(num).replace(".", "_").replace(",", ".").replace("_", ",")
        return formatted_num