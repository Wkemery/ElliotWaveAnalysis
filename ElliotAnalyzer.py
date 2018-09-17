import pandas as pd
from Error import *


class Elliot_Analyzer:
    DEBUG = True

    def __init__(self, swing_file, last_bar, configfile="AnalyzerConfig.conf"):
        self.swing_data = pd.read_csv(swing_file, names=['Date_Time', 'Price', 'Pos', 'Row']).tail(6)
        self.swing_data['Date_Time'] = pd.to_datetime(self.swing_data['Date_Time'])
        print(self.swing_data.Date_Time)
        self.last_bar = last_bar

    #Potential Wave Functions
    def wave2(self):
        wave_tracker = True
        relevant_swings = self.swing_data.tail(3) #look at last 3 swings

        #condition2: has wave 2 reached the typical time and price retracment?, Condition1 implicit in Condition 2
        retracements = self.fib_retracement(relevant_swings.iloc[0]['Price'], relevant_swings.iloc[1]['Price'])
        if self.DEBUG: print(retracements)
        if self.DEBUG: print(relevant_swings.iloc[2]["Price"])
        wave_tracker = wave_tracker and self.in_range(relevant_swings.iloc[2]["Price"], retracements['.50'], retracements['.618'])
        return wave_tracker

    def wave3():
        return False

    def wave4():
        return False

    def wave5():
        return False

    def waveA():
        return False

    def waveB():
        return False

    def waveC():
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
