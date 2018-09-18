import pandas as pd
from Error import *
import datetime as dt
import copy
import configparser

import plotly.plotly  as py
import plotly.offline as offline
import plotly.graph_objs as go

class Elliot_Analyzer:
    DEBUG = True

    def __init__(self, currency_name, swing_file, OHLC_data, config_file="AnalyzerConfig.conf"):
        #read in configFile
        self.config = configparser.ConfigParser()
        self.config.read(config_file)

        self.swing_data = pd.read_csv(swing_file, names=['Date_Time', 'Price', 'Pos', 'Row']).tail(6)
        self.swing_data['Date_Time'] = pd.to_datetime(self.swing_data['Date_Time'])

        if self.DEBUG: print("Date_Time column on self.swing_data:", self.swing_data.Date_Time)
        if self.DEBUG: print("Very first date:", self.swing_data.iloc[0]['Date_Time'])

        self.OHLC_data = OHLC_data
        self.OHLC_data = self.OHLC_data.set_index('Date_Time')

        self.OHLC_data =  self.OHLC_data.truncate(before=self.swing_data.iloc[0]['Date_Time'])

        self.currency_name = currency_name
        self.wave_data = None

    def analyze(self):
        if not self.wave5(self.swing_data.tail(6)):
            if not self.wave4(self.swing_data.tail(5)):
                if not self.wave3(self.swing_data.tail(4)):
                    if not self.wave2(self.swing_data.tail(3)):
                        return False
        return True

    def wave2(self, swings):

        relevant_swings = swings
        my_config = self.config_section_map(self.config, "Wave2")
        wave1_swings = (relevant_swings.iloc[0]['Price'], relevant_swings.iloc[1]['Price'])
        wave2_price = relevant_swings.iloc[2]["Price"]

        wave1_inrets = self.fib_retracement(wave1_swings[0], wave1_swings[1], list(my_config.values()))

        #check for minimum requirements first
        wave_min = self.in_range(wave2_price, wave1_inrets[my_config['inret_wave1_min']], wave1_inrets[my_config['inret_wave1_max']])
        if wave_min:
            wave_typ = self.in_range(wave2_price, wave1_inrets[my_config['inret_wave1_typical_min']], wave1_inrets[my_config['inret_wave1_typical_max']])
            if wave_typ:
                self.wave_data = (relevant_swings, "Typical")
            else:
                self.wave_data = (relevant_swings, "Minimum")

        return wave_min

    def wave3(self, swings):
        relevant_swings = swings
        my_config = self.config_section_map(self.config, "Wave3")

        wave1_swings = (relevant_swings.iloc[0]['Price'], relevant_swings.iloc[1]['Price'])
        wave2_swings = (relevant_swings.iloc[1]['Price'], relevant_swings.iloc[2]['Price'])
        wave3_price = relevant_swings.iloc[3]["Price"]
        wave2_price = relevant_swings.iloc[2]["Price"]

        wave1_app_levels = [level for option,level in my_config.items() if option.startswith('app')]
        wave2_exret_levels = [level for option,level in my_config.items() if option.startswith('exret')]

        wave1_apps = self.fib_projection(wave1_swings[0], wave1_swings[1], wave2_price, wave1_app_levels)
        wave2_exrets = self.fib_retracement(wave2_swings[0], wave2_swings[1], wave2_exret_levels)
        combo = {**wave1_apps, **wave2_exrets}

        #check for minimum requirements first
        wave_min = self.in_range(wave3_price, combo[min(combo, key=combo.get)], combo[max(combo, key=combo.get)])
        if wave_min:
            wave_typ = self.in_range(wave3_price, wave1_apps[my_config['app_wave1_typical']], wave2_exrets[my_config['exret_wave2_typical']])
            if wave_typ:
                self.wave_data = (relevant_swings, "Typical")
            else:
                self.wave_data = (relevant_swings, "Minimum")

        return wave_min

    def wave4(self, swings):
        return False

    def wave5(self, swings):
        return False

    def waveA(self, swings):
        return False

    def waveB(self, swings):
        return False

    def waveC(self, swings):
        return False

    def fib_retracement(self, swing_1, swing_2, fib_levels):
        if self.DEBUG: print("Swing1: ", swing_1, "\nSwing2: ", swing_2)

        wave_length = abs(swing_1 - swing_2)

        fib_retracements = []
        for level in fib_levels:
            fib_retracements.append(swing_2 + (-(wave_length * float(level)) if swing_1 < swing_2 else (wave_length * float(level))))

        if self.DEBUG: print("Fib dictionary returned:\n", dict(zip(fib_levels, fib_retracements)))

        return dict(zip(fib_levels, fib_retracements)) # Return a dictionary of fib levels mapped to their retracments

    def fib_projection(self, swing_1, swing_2, projection_point, fib_levels):
        if self.DEBUG: print("Swing1: ", swing_1, "\nSwing2: ", swing_2, "\nProjection Point: ", projection_point)

        wave_length = abs(swing_1 - swing_2)

        fib_projections = []
        for level in fib_levels:
            fib_projections.append(projection_point + (-(wave_length * float(level)) if swing_1 > swing_2 else (wave_length * float(level))))

        if self.DEBUG: print("Fib dictionary returned:\n", dict(zip(fib_levels, fib_projections)))

        return dict(zip(fib_levels, fib_projections)) # Return a dictionary of fib levels mapped to their retracments

    def in_range(self, x, range_1, range_2):
        bottom = range_1 if range_1 < range_2 else range_2
        top = range_1 if range_1 > range_2 else range_1

        return bottom <= x <= top

    def export_graph(self):
        if self.wave_data is None:
            eprint("Cannot Export graph: There is no Elliot Wave Data")
            return
        my_swing_data = self.wave_data[0]


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

    def config_section_map(self, config, section):
        dict1 = {}
        options = config.options(section)
        for option in options:
            try:
                dict1[option] = config.get(section, option)
                if dict1[option] == -1:
                    print("skip: %s" % option)
            except:
                print("exception on %s!" % option)
                dict1[option] = None
        return dict1
