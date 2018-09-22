import pandas as pd
import collections
import copy
import csv
from Error import *
import numpy as np

import plotly.plotly  as py
import plotly.offline as offline
import plotly.graph_objs as go
from datetime import datetime

Pivot_Point = collections.namedtuple('Pivot_Point', ['data', 'row', 'pos'])
Swing_Line = collections.namedtuple('Swing_Line', ['date_time', 'pos', 'row'])

DT_FORMAT = "%Y-%m-%d %H:%M:%S"
class Swing_Generator:
    DEBUG = False

    def __init__(self, data_file, swing_file, configfile="SwingConfig.conf"):
        self.swing_file = swing_file
        self.swing_writer = None
        self.data_file = data_file
        self.ref_column = "NA"
        self.ATR_period = 0
        self.time_factor = -1
        self.price_factor = 0
        self.update = False
        swing_column = None
        if self.DEBUG: print(self.OHLC_data.tail())

        infile = open(configfile, 'r', newline='')
        config_reader = csv.reader(infile, delimiter=',')
        next(config_reader)
        for row in config_reader:
            if row[0] == "reference_column":
                self.ref_column = row[1]
            elif row[0] == "ATR_period":
                self.ATR_period = int(row[1])
            elif row[0] == "time_factor":
                self.time_factor = int(row[1])
            elif row[0] == "price_factor":
                self.price_factor = float(row[1])
            elif row[0] == "swing_column":
                swing_column = row[1]

        if self.DEBUG:
            print("Reference Column:", self.ref_column)
            print("Swing Column:", swing_column)
            print("ATR period:", self.ATR_period)
            print("Time Factor:", self.time_factor)
            print("Price Factor:", self.price_factor)

        self.swings_column_high = swing_column if swing_column == "Close" else "High"
        self.swings_column_low = swing_column if swing_column == "Close" else "Low"

        if self.ref_column == "NA" or self.ATR_period == 0 or self.time_factor == -1 or self.price_factor == 0 or swing_column == "NA":
            raise ValueError("One or more required attributes not found in configuration file: " + configfile)
        infile.close()

    def generate_swings(self):
        self.OHLC_data = pd.read_csv(self.data_file, names=['Date_Time', 'Open', 'High', 'Low', 'Close'])
        self.OHLC_data['Date_Time'] = pd.to_datetime(self.OHLC_data['Date_Time'], format=DT_FORMAT)
        self.OHLC_data = self.OHLC_data.set_index('Date_Time', drop=False)
        self.OHLC_data = self.Average_True_Range(self.OHLC_data, self.ATR_period)

        #Setup Stuff
        swing_file = open(self.swing_file, 'w', newline='')
        self.swing_writer = csv.writer(swing_file, delimiter=',')
        total_rows = len(self.OHLC_data.index)

        if total_rows < self.ATR_period:
            eprint("Not enough data to calculate ATR")
            return False

        row_count = 0
        reg_point = Pivot_Point(0,0,0)
        swing_point = Pivot_Point(0,0,0)
        temp_close_var = "Close"
        ####Find first Swing point####

        HH = (self.OHLC_data.iloc[0], 0)
        LL = (self.OHLC_data.iloc[0], 0)
        HH_ATR_Limit = HH[0][temp_close_var] - (HH[0]["ATR"]*self.price_factor)
        LL_ATR_Limit = LL[0][temp_close_var] + (LL[0]["ATR"]*self.price_factor)

        found_first_swing = False
        while not found_first_swing and row_count < total_rows:
            current_row = self.OHLC_data.iloc[row_count]

            if current_row[temp_close_var] >= LL_ATR_Limit and (row_count - self.time_factor) > LL[1]:
                self.swing_writer.writerow([LL[0]['Date_Time'], LL[0][self.swings_column_low], "Low", LL[1]]) #write out first swing point
                swing_point = copy.deepcopy(reg_point)
                reg_point = Pivot_Point(current_row, row_count, "High")
                found_first_swing = True
            elif current_row[temp_close_var] <= HH_ATR_Limit and (row_count - self.time_factor) > HH[1]:
                self.swing_writer.writerow([HH[0]['Date_Time'], HH[0][self.swings_column_high], "High", HH[1]]) #write out first swing point
                swing_point = copy.deepcopy(reg_point)
                reg_point = Pivot_Point(current_row, row_count, "Low")
                found_first_swing = True
            elif current_row[temp_close_var] < LL[0][temp_close_var]:
                LL = (current_row, row_count)
                LL_ATR_Limit = LL[0][temp_close_var] + (LL[0]["ATR"]*self.price_factor)
            elif current_row[temp_close_var] > HH[0][temp_close_var]:
                HH = (current_row, row_count)
                HH_ATR_Limit = HH[0][temp_close_var] - (HH[0]["ATR"]*self.price_factor)
            row_count += 1

        if not found_first_swing:
            eprint("Never found a swing")
            return False

        if self.DEBUG:
            print("First Registerd Point", reg_point)
            print("Current Row Count:", row_count, "\t Total Rows:", total_rows)


        #######Find all swings following first swing by looping through prices until finding new RP#######
        self.calculate_remaining_swings(swing_point, reg_point, row_count, total_rows)

        swing_file.close()

        return True

    def update_swings(self):
        swing_file = open(self.swing_file, 'r', newline='')
        lines = swing_file.readlines()
        swing_file.close()

        # Read in the last swing and last reg point
        data_tup = lines[-2].split(',')
        last_swing = Swing_Line(date_time=data_tup[0], pos=data_tup[2], row=int(data_tup[3]))
        data_tup = lines[-1].split(',')
        last_reg = Swing_Line(date_time=data_tup[0], pos=data_tup[2], row=int(data_tup[3]))

        # Read in only necessary OHLC data
        self.OHLC_data = pd.read_csv(self.data_file, names=['Date_Time', 'Open', 'High', 'Low', 'Close'], skiprows=(last_swing.row - self.ATR_period))
        self.OHLC_data['Date_Time'] = pd.to_datetime(self.OHLC_data['Date_Time'], format=DT_FORMAT)
        self.OHLC_data = self.OHLC_data.set_index('Date_Time', drop=False)
        self.OHLC_data = self.Average_True_Range(self.OHLC_data, self.ATR_period)

        # Set swing_point and reg_point
        datetime_swing = datetime.strptime(last_swing.date_time, DT_FORMAT)
        swing_point = Pivot_Point(self.OHLC_data.loc[datetime_swing], int(last_swing.row), last_swing.pos)
        datetime_reg = datetime.strptime(last_reg.date_time, DT_FORMAT)
        reg_point = Pivot_Point(self.OHLC_data.loc[datetime_reg], int(last_reg.row), last_reg.pos)

        # Check for any update at all.
        print(self.OHLC_data.loc[datetime_reg]["Date_Time"])
        print(self.OHLC_data.tail(1).iloc[0]["Date_Time"])
        if (self.OHLC_data.loc[datetime_reg]["Date_Time"]) == (self.OHLC_data.tail(1).iloc[0]["Date_Time"]):
            return
        #Set up all vars for remaning swings calculation
        row_count = reg_point.row + 1
        total_rows = row_count + len(self.OHLC_data.index) - 1
        swing_file = open(self.swing_file, 'a', newline='')
        self.swing_writer = csv.writer(swing_file, delimiter=',')

        self.calculate_remaining_swings(swing_point, reg_point, row_count, total_rows)

        swing_file.close()

    def calculate_remaining_swings(self, swing_point, reg_point, row_count, total_rows):

        ref_column_low = self.ref_column if self.ref_column == "Close" else "Low"
        ref_column_high = self.ref_column if self.ref_column == "Close" else "High"


        first_reg_date = reg_point.data["Date_Time"]
        my_OHLC_data = self.OHLC_data.loc[first_reg_date:].iloc[1:]

        for index, current_row in my_OHLC_data.iterrows():
            if reg_point.pos == "High":
                violation_price = reg_point.data[ref_column_high] - (reg_point.data["ATR"]*self.price_factor)
                if current_row[ref_column_high] > reg_point.data[ref_column_high]: #new extreme with direction
                    reg_point = reg_point._replace(data = current_row, row = row_count)
                elif current_row[ref_column_low] < violation_price and (row_count - self.time_factor) > swing_point.row: #Violated ATR range in opposite direction
                    if self.DEBUG:
                        print("Violated ATR in the Low direction. Register a new Low, write out previous RP High as Swing High")
                        print("Previous REgisted Point: ", reg_point)

                    self.swing_writer.writerow([reg_point.data["Date_Time"], reg_point.data[self.swings_column_high if reg_point.pos == "High" else self.swings_column_low], reg_point.pos, reg_point.row]) #write out previous RP as SP
                    swing_point = copy.deepcopy(reg_point)
                    reg_point = Pivot_Point(current_row, row_count, "Low") #re-regsiter RP

                    if self.DEBUG:
                        print("New Registed Point: ", reg_point)

            elif reg_point.pos == "Low":
                violation_price = reg_point.data[ref_column_low] + (reg_point.data["ATR"]*self.price_factor)

                if current_row[ref_column_low] < reg_point.data[ref_column_low]: #new extreme with direction
                    reg_point = reg_point._replace(data = current_row, row = row_count)
                elif current_row[ref_column_high] > violation_price and (row_count - self.time_factor) > swing_point.row: #Violated ATR range in opposite direction
                    if self.DEBUG:
                        print("Violated ATR in the High direction. Register a new High, write out previous RP low as Swing low")
                        print("Previous REgisted Point: ", reg_point)

                    self.swing_writer.writerow([reg_point.data["Date_Time"], reg_point.data[self.swings_column_high if reg_point.pos == "High" else self.swings_column_low], reg_point.pos, reg_point.row]) #write out previous RP as SP
                    swing_point = copy.deepcopy(reg_point)
                    reg_point = Pivot_Point(current_row, row_count, "High") #re-regsiter RP

                    if self.DEBUG:
                        print("New Registed Point: ", reg_point)
            else:
                eprint("Registered point posistion is something other than \"High\" or \"Low\"")
                return False

            row_count += 1


        if not first_reg_date == reg_point.data["Date_Time"]:
            self.swing_writer.writerow([reg_point.data["Date_Time"], reg_point.data[self.swings_column_high if reg_point.pos == "High" else self.swings_column_low], reg_point.pos, reg_point.row]) #set last RP as a SP

        ###############################################################################################################

    def reverse_file(self):
        swing_file = open(self.swing_file, 'r')
        reversed_lines = []
        for line in reversed(swing_file.readlines()):
            reversed_lines.append(line)
        swing_file.close()

        swing_file = open(self.swing_file, 'w')
        for line in reversed_lines:
            swing_file.write(line)
        swing_file.close()

    def Average_True_Range(self, df, n):
        """
        :param df: pandas.DataFrame
        :param n:
        :return: pandas.DataFrame
        """
        i = 1
        TR_l = [df.iloc[0]['High'] - df.iloc[0]['Low']]
        rows = len(df.index)
        while i < rows:
            TR = max(df.iloc[i]['High'] - df.iloc[i]['Low'], abs(df.iloc[i]['High'] - df.iloc[i-1]['Close']), abs(df.iloc[i]['Low'] - df.iloc[i-1]['Close']))
            TR_l.append(TR)
            i += 1
        ATR_df = pd.DataFrame({'col':TR_l})
        ATR_l = []
        for i in range(len(TR_l)):
            if i < n:
                if i == (n - 1):
                    ATR_l.append(np.mean(TR_l[:n]))
                else:
                    ATR_l.append(0)
            else:
                ATR_l.append((ATR_l[i - 1] * (n - 1) + TR_l[i]) / n)

        return df.assign(ATR=ATR_l)

    def graph_OHLC(self):
        #not quite there, but the other one works, which is what i really care about
        OHLC_trace = go.Ohlc(x=self.OHLC_data.Date_Time,
                open=self.OHLC_data.Open,
                high=self.OHLC_data.High,
                low=self.OHLC_data.Low,
                close=self.OHLC_data.Close,
                name="OHLC Data",
                increasing=dict(line=dict(color= '#408e4a')),
                decreasing=dict(line=dict(color= '#cc2718')))

        swing_data = pd.read_csv(self.swing_file, names=['Date_Time', 'Price', 'Direction', 'Row'], parse_dates=True)
        swing_trace = go.Scatter(
            x = swing_data.Date_Time,
            y = swing_data.Price,
            mode = 'lines+markers',
            name = 'Swings',
            line = dict(
                color = ('rgb(111, 126, 130)'),
                width = 3)
        )

        data = [OHLC_trace, swing_trace]
        layout = go.Layout(xaxis = dict(rangeslider = dict(visible = False)), title= self.data_file[:-4])

        fig = go.Figure(data=data, layout=layout)
        py.plot(fig, filename=self.data_file + ".html", output_type='file')

    def export_OHLC_graph(self):

        if self.update:
            print("Did update, graph is screwy")
        OHLC_trace = go.Ohlc(x=self.OHLC_data.Date_Time,
                open=self.OHLC_data.Open,
                high=self.OHLC_data.High,
                low=self.OHLC_data.Low,
                close=self.OHLC_data.Close,
                name="OHLC Data",
                increasing=dict(line=dict(color= '#408e4a')),
                decreasing=dict(line=dict(color= '#cc2718')))

        swing_data = pd.read_csv(self.swing_file, names=['Date_Time', 'Price', 'Direction', 'Row'], parse_dates=True)
        swing_trace = go.Scatter(
            x = swing_data.Date_Time,
            y = swing_data.Price,
            mode = 'lines+markers',
            name = 'Swings',
            line = dict(
                color = ('rgb(111, 126, 130)'),
                width = 3)
        )

        data = [OHLC_trace, swing_trace]

        layout = {
            'title': self.data_file[:-4],
            'yaxis': {'title': 'Price'},
        }
        fig = go.Figure(data=data, layout=layout)
        offline.plot(fig, output_type='file',filename=self.data_file + ".html", image='png', image_filename=self.data_file)
