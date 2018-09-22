import pandas as pd
from Error import *
import datetime as dt
import copy
import configparser

import plotly.plotly  as py
import plotly.offline as offline
import plotly.graph_objs as go
DT_FORMAT = "%Y-%m-%d %H:%M:%S"
#TODO: change the whole wave_data thing to maybe a list and return that list along with summary_analysis in analyze()

class Elliot_Analyzer:
    DEBUG = False

    def __init__(self, currency_name, swing_file, OHLC_data_file, config_file="AnalyzerConfig.conf"):
        #read in configFile
        self.config = configparser.ConfigParser()
        self.config.read(config_file)

        self.swing_data = pd.read_csv(swing_file, names=['Date_Time', 'Price', 'Pos', 'Row']).tail(6)
        self.swing_data['Date_Time'] = pd.to_datetime(self.swing_data['Date_Time'], format=DT_FORMAT)

        if self.DEBUG: print("All the Swing Data")
        if self.DEBUG: print(self.swing_data)
        last_swing_row = self.swing_data.iloc[0]["Row"]
        self.OHLC_data = pd.read_csv(OHLC_data_file, names=['Date_Time', 'Open', 'High', 'Low', 'Close'], skiprows=last_swing_row)
        self.OHLC_data['Date_Time'] = pd.to_datetime(self.OHLC_data['Date_Time'], format=DT_FORMAT)
        self.OHLC_data = self.OHLC_data.set_index('Date_Time')

        # self.OHLC_data = self.OHLC_data.truncate(before=self.swing_data.iloc[0]['Date_Time'])
        if self.DEBUG: print("OHLCDATA")
        if self.DEBUG: print(self.OHLC_data)
        self.currency_name = currency_name
        self.wave_data = None

    def analyze(self):
        analysis_summary = []

        #Wave 5 analysis
        if self.wave5(self.swing_data.tail(6)):
            analysis_summary.append("Wave 5")
        elif self.wave4(self.swing_data.tail(5)):
            analysis_summary.append("Wave 4")
        elif self.wave3(self.swing_data.tail(4)):
            analysis_summary.append("Wave 3")
        elif self.wave2(self.swing_data.tail(3)):
            analysis_summary.append("Wave 2")

        #wave c
        if self.waveC(self.swing_data.tail(4)):
            analysis_summary.append("Wave C")

        # if self.gartley(self.swing_data.tail(4)) something like this for other analysis
        return analysis_summary

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
        #check for wave 2 requirements
        if not self.wave2(swings.head(3)):
            if self.DEBUG: print("Failed Wave2 on downward call")
            return False

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

        #check for minimum requirements first, then typicaL
        wave_min = self.in_range(wave3_price, combo[min(combo, key=combo.get)], combo[max(combo, key=combo.get)])
        if wave_min:
            wave_typ = self.in_range(wave3_price, wave1_apps[my_config['app_wave1_typical']], wave2_exrets[my_config['exret_wave2_typical']])
            if wave_typ:
                self.wave_data = (relevant_swings, "Typical")
            else:
                self.wave_data = (relevant_swings, "Minimum")

        return wave_min

    def wave4(self, swings):
        #check for wave 3 requirements
        if not self.wave3(swings.head(4)):
            if self.DEBUG: print("Failed Wave3 on downward call")
            return False

        relevant_swings = swings
        my_config = self.config_section_map(self.config, "Wave4")

        wave1_swings = (relevant_swings.iloc[0]['Price'], relevant_swings.iloc[1]['Price'])
        wave3_swings = (relevant_swings.iloc[2]['Price'], relevant_swings.iloc[3]['Price'])

        wave4_price = relevant_swings.iloc[4]["Price"]

        wave3_ret_levels = [level for option,level in my_config.items() if option.startswith('ret_wave3')]
        wave1_3_ret_levels = [level for option,level in my_config.items() if option.startswith('ret_wave1_3')]


        wave3_rets = self.fib_retracement(wave3_swings[0], wave3_swings[1], wave3_ret_levels)
        wave1_3_rets = self.fib_retracement(wave1_swings[0], wave3_swings[1], wave1_3_ret_levels)
        combo = {**wave3_rets, **wave1_3_rets}

        #check for minimum requirements first, then typicaL
        violated = True
        if relevant_swings.iloc[4]["Pos"] == "Low":
            violated = wave4_price < self.OHLC_data.loc[relevant_swings.iloc[1]['Date_Time']]["Close"]
        else:
            violated = wave4_price > self.OHLC_data.loc[relevant_swings.iloc[1]['Date_Time']]["Close"]

        wave_min = self.in_range(wave4_price, combo[min(combo, key=combo.get)], combo[max(combo, key=combo.get)]) and not violated

        if wave_min:
            wave_typ = self.in_range(wave4_price, wave3_rets[my_config['ret_wave3_min']], wave3_rets[my_config['ret_wave3_typical']])
            if wave_typ:
                self.wave_data = (relevant_swings, "Typical")
            else:
                self.wave_data = (relevant_swings, "Minimum")

        return wave_min

    def wave5(self, swings):
        if not self.wave4(swings.head(5)):
            if self.DEBUG : print("Failed Wave4 on downward call")
            return False

        relevant_swings = swings
        my_config = self.config_section_map(self.config, "Wave5")

        wave1_swings = (relevant_swings.iloc[0]['Price'], relevant_swings.iloc[1]['Price'])
        wave3_swings = (relevant_swings.iloc[2]['Price'], relevant_swings.iloc[3]['Price'])
        wave4_swings = (relevant_swings.iloc[3]['Price'], relevant_swings.iloc[4]['Price'])
        wave5_swings = (relevant_swings.iloc[4]['Price'], relevant_swings.iloc[5]['Price'])

        wave4_price = relevant_swings.iloc[4]["Price"]
        wave5_price = relevant_swings.iloc[5]["Price"]

        wave1_3_app_levels = [level for option,level in my_config.items() if option.startswith('app_wave1_3')]
        wave1_app_levels = [level for option,level in my_config.items() if option.startswith('app_wave1')]
        wave4_exret_levels = [level for option,level in my_config.items() if option.startswith('exret_wave4')]

        wave1_3_apps = self.fib_projection(wave1_swings[0], wave3_swings[1], wave4_price, wave1_3_app_levels)
        wave1_apps = self.fib_projection(wave1_swings[0], wave1_swings[1], wave4_price, wave1_app_levels)
        wave4_exrets = self.fib_retracement(wave4_swings[0], wave4_swings[1], wave4_exret_levels)
        combo = {**wave1_3_apps, **wave1_apps, **wave4_exrets}

        #violation condition is wave 3 shortest wave TODO
        violated = False
        wave1_magnitude = abs(wave1_swings[0] - wave1_swings[1])
        wave3_magnitude = abs(wave3_swings[0] - wave3_swings[1])
        wave5_magnitude = abs(wave5_swings[0] - wave5_swings[1])

        if (wave3_magnitude < wave1_magnitude) and (wave3_magnitude < wave5_magnitude):
            violated = True

        wave_min = not violated
        if relevant_swings.iloc[5]["Pos"] == "High":
            wave_min = wave_min and wave5_price > combo[min(combo, key=combo.get)]
        else:
            wave_min = wave_min and wave5_price <  combo[max(combo, key=combo.get)]

        if wave_min:
            price_in_wave1_3 = self.in_range(wave5_price, wave1_3_apps[my_config['app_wave1_3_min']], wave1_3_apps[my_config['app_wave1_3_typical']])
            wave1_in_wave1_3 = self.in_range(wave1_apps[my_config["app_wave_1"]], wave1_3_apps[my_config['app_wave1_3_min']], wave1_3_apps[my_config['app_wave1_3_typical']])
            price_in_wave_4 = self.in_range(wave5_price, wave4_exrets[my_config['exret_wave4_min']], wave4_exrets[my_config['exret_wave4_typical']])
            wave1_in_wave4 = self.in_range(wave1_apps[my_config["app_wave_1"]], wave4_exrets[my_config['exret_wave4_min']], wave4_exrets[my_config['exret_wave4_typical']])
            wave_high_prob = price_in_wave1_3 and price_in_wave_4 and wave1_in_wave1_3 and wave1_in_wave4

            if wave_high_prob:
                self.wave_data = (relevant_swings, "HighProbability")
            else:
                wave_typ = (price_in_wave1_3 and wave1_in_wave1_3) or (price_in_wave1_3 and price_in_wave_4) or (price_in_wave_4 and wave1_in_wave4)
            if wave_typ:
                self.wave_data = (relevant_swings, "Typical")
            else:
                self.wave_data = (relevant_swings, "Minimum")

        return wave_min

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
        top = range_1 if range_1 > range_2 else range_2

        return bottom <= x <= top

    def export_graph(self, output_file):
        if self.wave_data is None:
            eprint("Cannot Export graph: There is no Elliot Wave Data")
            return
        my_swing_data = self.wave_data[0]
        print('my swing data:', my_swing_data)


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
        # offline.plot(fig, output_type='file',filename=self.currency_name + ".html", image='png', image_filename=self.currency_name)
        offline.plot(fig, output_type='file',filename=output_file, auto_open=False)

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
