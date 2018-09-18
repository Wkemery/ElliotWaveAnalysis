import pandas as pd
from Error import *
import datetime as dt
import copy

import plotly.plotly  as py
import plotly.offline as offline
import plotly.graph_objs as go

class Elliot_Analyzer:
    DEBUG = True

    def __init__(self, currency_name, swing_file, OHLC_data, configfile="AnalyzerConfig.conf"):
        self.swing_data = pd.read_csv(swing_file, names=['Date_Time', 'Price', 'Pos', 'Row']).tail(6)
        self.swing_data['Date_Time'] = pd.to_datetime(self.swing_data['Date_Time'])
        if self.DEBUG: print("DAte_Time column on self.swing_data:", self.swing_data.Date_Time)
        if self.DEBUG: print("Very first date:", self.swing_data.iloc[0]['Date_Time'])

        self.OHLC_data = OHLC_data
        self.OHLC_data = self.OHLC_data.set_index('Date_Time')

        self.OHLC_data =  self.OHLC_data.truncate(before=self.swing_data.iloc[0]['Date_Time'])
        if self.DEBUG: print("Truncated OHLC data: ",self.OHLC_data)

        self.currency_name = currency_name
        self.wave_data = self.swing_data

    def analyze(self):
        if not self.wave5(self.swing_data.tail(6)):
            if not self.wave4(self.swing_data.tail(5)):
                if not self.wave3(self.swing_data.tail(4)):
                    if not self.wave2(self.swing_data.tail(3)):
                        return False
        return True

    def wave2(self, swings=None):
        wave_tracker = True
        relevant_swings = swings.tail(3) if swings is not None else self.swing_data.tail(3)#look at last 3 swings

        #condition2: has wave 2 reached the typical time and price retracment?, Condition1 implicit in Condition 2
        retracements = self.fib_retracement(relevant_swings.iloc[0]['Price'], relevant_swings.iloc[1]['Price'])
        if self.DEBUG: print("retracements: \n", retracements, "\nCurrent Swing Price:\n", relevant_swings.iloc[2]["Price"])
        wave_tracker = wave_tracker and self.in_range(relevant_swings.iloc[2]["Price"], retracements['.50'], retracements['.618'])

        if wave_tracker:
            self.wave_data = relevant_swings
        return wave_tracker

    def wave3(self, swings=None):
        return False

    def wave4(self, swings=None):
        return False

    def wave5(self, swings=None):
        return False

    def waveA(self, swings=None):
        return False

    def waveB(self, swings=None):
        return False

    def waveC(self, swings=None):
        return False

    def fib_retracement(self, swing_1, swing_2):
        #fib values: .382, .50, .618, .786, 1.27, 1.62, 2.62
        if(swing_1 < swing_2):
            direction = "up"
        else:
            direction = "down"
        if self.DEBUG:
            print(swing_1, swing_2)
        wave_length = abs(swing_1 - swing_2)

        fib_values = {}
        fib_values['.382'] =  swing_2 + (-(wave_length * 0.382) if direction == "up" else (wave_length * 0.382))
        fib_values['.50'] =  swing_2 + (-(wave_length * 0.50) if direction == "up" else (wave_length * 0.50))
        fib_values['.618'] =  swing_2 + (-(wave_length * 0.618) if direction == "up" else (wave_length * 0.618))
        fib_values['.786'] =  swing_2 + (-(wave_length * 0.786) if direction == "up" else (wave_length * 0.786))
        fib_values['1.27'] =  swing_2 + (-(wave_length * 1.27) if direction == "up" else (wave_length * 1.27))
        fib_values['1.62'] =  swing_2 + (-(wave_length * 1.62) if direction == "up" else (wave_length * 1.62))
        fib_values['2.62'] =  swing_2 + (-(wave_length * 2.62) if direction == "up" else (wave_length * 2.62))

        return fib_values

    def fib_projection(self, swing_low, swing_high, projection_point):
        return

    def in_range(self, x, range_1, range_2):
        bottom = range_1 if range_1 < range_2 else range_2
        top = range_1 if range_1 > range_2 else range_1

        return bottom <= x <= top

    def export_graph(self, swing_data=None):
        my_swing_data = swing_data if swing_data is not None else self.wave_data
        if self.wave_data is None:
            eprint("Cannot Export graph: There is no Elliot Wave Data")
            return

        OHLC_trace = go.Ohlc(x=self.OHLC_data.index,
                open=self.OHLC_data.Open,
                high=self.OHLC_data.High,
                low=self.OHLC_data.Low,
                close=self.OHLC_data.Close,
                name="OHLC Data",
                increasing=dict(line=dict(color= '#408e4a')),
                decreasing=dict(line=dict(color= '#cc2718')))

        print([str(x) for x in range(1, len(my_swing_data.index))])
        swing_trace = go.Scatter(
            x = my_swing_data.Date_Time,
            y = my_swing_data.Price,
            mode = 'lines+markers+text',
            name = 'Swings',
            line = dict(
                color = ('rgb(111, 126, 130)'),
                width = 3),
            text=[str(x) for x in range(len(my_swing_data.index))],
            textposition='top center',
            textfont=dict(
                family='sans serif',
                size=35,
                color='#2c3035'
            )
        )

        data = [OHLC_trace, swing_trace]


        layout = dict(
                        title=self.currency_name,
                        xaxis = dict(
                        type="category"))

        fig = go.Figure(data=data, layout=layout)
        offline.plot(fig, output_type='file',filename=self.currency_name + ".html", image='png', image_filename=self.currency_name)
