import pandas as pd
import geopandas as gpd
import numpy as np
from shapely.geometry import Point, LineString
import plotly.express as px


class TripTable():
    def __init__(self, id, start,end,geometry, starttime, endtime, routedistance, travelmode, number_of_stages=None):
        
        self.id = id
        self.start= start
        self.end = end
        self.geometry = geometry
        self.starttime = starttime
        self.endtime = endtime
        self.routedistance = routedistance
        self.travelmode = travelmode

    def create_DataFrame(self):

        df = pd.DataFrame()
        df['trip_id'] = self.id
        df['travel_mode'] = self.travelmode
        df['start_point'] = self.start
        df['end_point'] = self.end
        df['start_time'] = self.starttime
        df['end_time'] = self.endtime
        df['duration'] = df['end_time'] - df['start_time']
        df['routed_distance'] = self.routedistance

        return df

    def get_ModalSplit(self):
        df = self.travelmode.value_counts().reset_index()
        df.columns = ['Verkehrsmittel', 'Anzahl']
        return df
    
    def set_Geometry(self, geometry):
        self.geometry = geometry

    def make_LineString(self):
        df=pd.DataFrame(columns=['start' , 'end'])
        df['start'] = self.start
        df['end'] = self.end
        df['line'] = df.apply(lambda x: LineString([x.start, x.end]),axis=1)
        self.geometry = df.line

    def plot_ModalSplit(self, style):
        df = self.get_ModalSplit()
        if style == 'pie':
            fig = px.pie(df, values='Anzahl', names='Verkehrsmittel', title='Modal-Split')
            fig.update_layout(height=700, width=1000,
                font=dict(
                    family="Arial",
                    size=20,
                    color="Black"))
            fig.update_layout()

        elif style == 'bar':
            fig = px.bar(df, x='Verkehrsmittel', y = 'Anzahl', title='Anzahl der Wege pro Verkehrsmittel')
            fig.update_layout(height=700, width=1000,
                font=dict(
                    family="Arial",
                    size=20,
                    color="Black"))
            fig.update_layout()
        return fig
    
    def plot_trip_distance_distribution(self, bins=20):
      
      df = self.create_DataFrame()
      fig = px.histogram(df, x="routed_distance", nbins=bins)
      fig.show()

    

        