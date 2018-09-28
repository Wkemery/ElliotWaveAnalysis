import pandas as pd
from Error import *
import datetime as dt
import copy
import configparser

import plotly.plotly  as py
import plotly.offline as offline
import plotly.graph_objs as go
DT_FORMAT = "%Y-%m-%d %H:%M:%S"
#TODO: change wave data to be a list of datas when adding support for more data patterns

class Elliot_Analyzer:
    DEBUG = False

    def __init__(self, currency_name, swing_file, OHLC_data_file, config_file="AnalyzerConfig.conf"):
        #read in configFile
        self.config = configparser.ConfigParser()
        self.config.read(config_file)

        self.swing_data = pd.read_csv(swing_file, names=['Date_Time', 'Price', 'Pos', 'Row']).tail(9)
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
        self.wave_data = {}

    def analyze(self):
        # Set up Analysis type
        my_config = self.config_section_map(self.config, "Analysis_Type")

        if len(self.swing_data.index) < 6:
            eprint("Not enough swing data to do Wave 5 Analysis!")
            return []

        analysis_summary = []

        #Wave 5 analysis
        if my_config["wave5"] == "1" and self.wave5(self.swing_data.tail(6)):
            analysis_summary.append("Wave5")
        elif my_config["wave4"] == "1" and self.wave4(self.swing_data.tail(5)):
            analysis_summary.append("Wave4")
        elif my_config["wave3"] == "1" and self.wave3(self.swing_data.tail(4)):
            analysis_summary.append("Wave3")
        elif my_config["wave2"] == "1" and self.wave2(self.swing_data.tail(3)):
            analysis_summary.append("Wave2")

        #wave c
        if my_config["wavec"] == "1"  and len(self.swing_data.index) < 9:
            eprint("Not enough swing data to do Wave C Analysis!")
            return []

        if my_config["wavec"] == "1" and self.waveC(self.swing_data.tail(9)):
            analysis_summary.append("WaveC")

        # if self.gartley(self.swing_data.tail(4)) something like this for other analysis
        return analysis_summary

    def wave2(self, swings, downward_call=False):

        relevant_swings = swings
        my_config = self.config_section_map(self.config, "Wave2")
        wave1_swings = (relevant_swings.iloc[0]['Price'], relevant_swings.iloc[1]['Price'])
        wave2_price = relevant_swings.iloc[2]["Price"]

        wave1_inrets = self.fib_retracement(wave1_swings[0], wave1_swings[1], list(my_config.values()))

        #Ensure Wave 2 has not gone past start of wave 1
        violated = True
        if relevant_swings.iloc[2]["Pos"] == "Low":
            violated = wave2_price < self.OHLC_data.loc[relevant_swings.iloc[0]['Date_Time']]["Close"]
        else:
            violated = wave2_price > self.OHLC_data.loc[relevant_swings.iloc[0]['Date_Time']]["Close"]

        #check for minimum requirements first
        wave_min = self.in_range(wave2_price, wave1_inrets[my_config['inret_wave1_min']], wave1_inrets[my_config['inret_wave1_max']]) and not violated
        if wave_min:
            wave_typ = self.in_range(wave2_price, wave1_inrets[my_config['inret_wave1_typical_min']], wave1_inrets[my_config['inret_wave1_typical_max']])
            if not downward_call:
                if wave_typ:
                    self.wave_data["Wave2"] = (relevant_swings, "Typical")
                else:
                    self.wave_data["Wave2"] = (relevant_swings, "Minimum")

        return wave_min

    def wave3(self, swings, downward_call=False):
        #check for wave 2 requirements
        if not self.wave2(swings.head(3), True):
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
            if not downward_call:
                if wave_typ:
                    self.wave_data["Wave3"] = (relevant_swings, "Typical")
                else:
                    self.wave_data["Wave3"] = (relevant_swings, "Minimum")

        return wave_min

    def wave4(self, swings, downward_call=False):
        #check for wave 3 requirements
        if not self.wave3(swings.head(4), True):
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

        #Ensure Wave 4 has not gone into closing range of wave 1
        violated = True
        if relevant_swings.iloc[4]["Pos"] == "Low":
            violated = wave4_price < self.OHLC_data.loc[relevant_swings.iloc[1]['Date_Time']]["Close"]
        else:
            violated = wave4_price > self.OHLC_data.loc[relevant_swings.iloc[1]['Date_Time']]["Close"]

        #check for minimum requirements first, then typicaL
        wave_min = self.in_range(wave4_price, combo[min(combo, key=combo.get)], combo[max(combo, key=combo.get)]) and not violated

        if wave_min:
            wave_typ = self.in_range(wave4_price, wave3_rets[my_config['ret_wave3_min']], wave3_rets[my_config['ret_wave3_typical']])
            if not downward_call:
                if wave_typ:
                    self.wave_data["Wave4"] = (relevant_swings, "Typical")
                else:
                    self.wave_data["Wave4"] = (relevant_swings, "Minimum")

        return wave_min

    def wave5(self, swings):
        if not self.wave4(swings.head(5), True):
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

        # Ensure wave 3 is not shortest wave of 1,3 and 5
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
                self.wave_data["Wave5"] = (relevant_swings, "HighProbability")
            else:
                wave_typ = (price_in_wave1_3 and wave1_in_wave1_3) or (price_in_wave1_3 and price_in_wave_4) or (price_in_wave_4 and wave1_in_wave4)
                if wave_typ:
                    self.wave_data["Wave5"] = (relevant_swings, "Typical")
                else:
                    self.wave_data["Wave5"] = (relevant_swings, "Minimum")

        return wave_min

    def waveC(self, swings):
        relevant_swings = swings.tail(4)
        my_config = self.config_section_map(self.config, "WaveC")

        #Ensure corrective pattern is following some kind of trend
        following_trend, trend_swings = self.trending(swings.head(6), my_config["proper_trend"], my_config["mini_trend"], my_config["little_trend"])
        if not following_trend: return False

        waveA_swings = (relevant_swings.iloc[0]['Price'], relevant_swings.iloc[1]['Price'])
        waveB_swings = (relevant_swings.iloc[1]['Price'], relevant_swings.iloc[2]['Price'])
        waveB_price = relevant_swings.iloc[2]['Price']
        waveC_price = relevant_swings.iloc[3]['Price']


        prior_trend_levels = [level for option,level in my_config.items() if option.startswith('inret_prior_trend')]
        waveA_app_levels = [level for option,level in my_config.items() if option.startswith('app_wavea')]
        waveB_exret_levels = [level for option,level in my_config.items() if option.startswith('exret_waveb')]

        prior_trend_rets = self.fib_retracement(trend_swings[0], trend_swings[1], prior_trend_levels)
        wavea_apps = self.fib_projection(waveA_swings[0], waveA_swings[1], waveB_price, waveA_app_levels)
        waveb_exrets = self.fib_retracement(waveB_swings[0], waveB_swings[1], waveB_exret_levels)
        combo = {**wavea_apps, **waveb_exrets}


        wave_min = self.in_range(waveC_price, prior_trend_rets[my_config['inret_prior_trend_min']], prior_trend_rets[my_config['inret_prior_trend_max']])
        wave_min = wave_min and self.in_range(waveC_price, combo[min(combo, key=combo.get)], combo[max(combo, key=combo.get)])
        #Ensure Wave B does not trade past start of wave A
        #Ensure Wave C Trades past Wave A
        if relevant_swings.iloc[0]["Pos"] == "High":
            wave_min = wave_min and self.OHLC_data.loc[relevant_swings.iloc[2]['Date_Time']]["High"] < self.OHLC_data.loc[relevant_swings.iloc[0]['Date_Time']]["Low"]
            wave_min = wave_min and self.OHLC_data.loc[relevant_swings.iloc[3]['Date_Time']]["Close"] < relevant_swings.iloc[1]['Price']
        else:
            wave_min = wave_min and self.OHLC_data.loc[relevant_swings.iloc[2]['Date_Time']]["High"] > self.OHLC_data.loc[relevant_swings.iloc[0]['Date_Time']]["Low"]
            wave_min = wave_min and self.OHLC_data.loc[relevant_swings.iloc[3]['Date_Time']]["Close"] > relevant_swings.iloc[1]['Price']

        if wave_min:
            wave_typ = self.in_range(waveC_price, prior_trend_rets[my_config['inret_prior_trend_typical_min']], prior_trend_rets[my_config['inret_prior_trend_typical_max']])
            if wave_typ: self.wave_data["WaveC"] = (swings, "Typical")
            else: self.wave_data["WaveC"] = (swings, "Minimum")

        return wave_min

    def trending(self, swings, proper, mini, little):
        mini_trend = False
        little_trend = False
        if mini == "1":
            mini_trend = True

        if little == "1":
            little_trend = True

        swing_5_3 = False
        swing_3_1 = False
        swing_4_2 = False
        swing_2_0 = False

        if swings.iloc[0]['Pos'] == "Low":
            swing_5_3 = swings.iloc[5]['Price'] > swings.iloc[3]['Price']
            swing_3_1 = swings.iloc[3]['Price'] > swings.iloc[1]['Price']
            swing_4_2 = swings.iloc[4]['Price'] > swings.iloc[2]['Price']
            swing_2_0 = swings.iloc[2]['Price'] > swings.iloc[0]['Price']
            swing_4_1 = swings.iloc[4]['Price'] > swings.iloc[1]['Price']
        else:
            swing_5_3 = swings.iloc[5]['Price'] < swings.iloc[3]['Price']
            swing_3_1 = swings.iloc[3]['Price'] < swings.iloc[1]['Price']
            swing_4_2 = swings.iloc[4]['Price'] < swings.iloc[2]['Price']
            swing_2_0 = swings.iloc[2]['Price'] < swings.iloc[0]['Price']
            swing_4_1 = swings.iloc[4]['Price'] < swings.iloc[1]['Price']


        little_trend = little_trend and swing_5_3 and swing_4_2
        big_trend = little_trend and swing_3_1 and swing_2_0

        if proper == "1":
            big_trend = big_trend and swing_4_1

        swing_1 = swings.iloc[4]['Price']
        swing_2 = swings.iloc[5]['Price']
        if big_trend:
            swing_1 = swings.iloc[0]['Price']
        elif little_trend:
            swing_1 = swings.iloc[2]['Price']

        return big_trend or little_trend or mini_trend, (swing_1, swing_2)

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

    def export_graphs(self, output_path):
        for key,value in self.wave_data.items():
            my_swing_data = value[0]
            print("My Swing Data:", my_swing_data)

            lables = []
            if key == "WaveC":
                lables = ["","","","","","","A", "B", "C"]
            else:
                lables = [str(x) for x in range(len(my_swing_data.index))]

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
                text=lables,
                textposition='top center',
                textfont=dict(
                    family='sans serif',
                    size=35,
                    color='#2c3035'
                )
            )

            data = [OHLC_trace, swing_trace]

            time_frame = output_path.split("_")[-1]

            layout = dict(
                            title=self.currency_name + " " + key + " " + time_frame + ": " + value[1],
                            xaxis = dict(
                            type="category"))

            fig = go.Figure(data=data, layout=layout)
            # offline.plot(fig, output_type='file',filename=self.currency_name + ".html", image='png', image_filename=self.currency_name)
            offline.plot(fig, output_type='file',filename=output_path + "_" + key + ".html", auto_open=False)

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
