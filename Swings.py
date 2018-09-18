import pandas as pd
import collections
import copy
import csv
from Error import *

import plotly.plotly  as py
import plotly.offline as offline
import plotly.graph_objs as go
from datetime import datetime

class Swing_Generator:
    DEBUG = False

    def __init__(self, data_file, swing_file, configfile="SwingConfig.conf"):
        self.swing_file = swing_file
        self.data_file = data_file
        self.OHLC_data = pd.read_csv(self.data_file, names=['Date_Time', 'Open', 'High', 'Low', 'Close'])
        self.OHLC_data = self.OHLC_data.reset_index(drop=False)
        self.OHLC_data['Date_Time'] = pd.to_datetime(self.OHLC_data['index'] + ' ' + self.OHLC_data['Date_Time'])
        self.OHLC_data = self.OHLC_data.drop(columns=['index'])
        self.ref_column = "NA"
        self.ATR_period = 0
        self.time_factor = -1
        self.price_factor = 0

        if self.DEBUG: logging.debug(self.OHLC_data.tail())

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
                self.price_factor = int(row[1])

        if self.DEBUG:
            logging.debug("Reference Column:", self.ref_column)
            logging.debug("ATR period:", self.ATR_period)
            logging.debug("Time Factor:", self.time_factor)
            logging.debug("Price Factor:", self.price_factor)

        if self.ref_column == "NA" or self.ATR_period == 0 or self.time_factor == -1 or self.price_factor == 0:
            raise ValueError("One or more required attributes not found in configuration file: " + configfile)
        infile.close()

    def generate_swings(self):
        #Setup Stuff
        swing_file = open(self.swing_file, 'w', newline='')
        swing_writer = csv.writer(swing_file, delimiter=',')

        OHLC_data = self.Average_True_Range(self.OHLC_data, self.ATR_period).dropna()
        OHLC_data = OHLC_data.rename(columns = {'ATR_' + str(self.ATR_period) : 'ATR'})
        total_rows = len(OHLC_data.index)
        if total_rows == 0:
            eprint("Not enough data to calculate ATR")
            return False


        row_count = 0

        Pivot_Point = collections.namedtuple('Pivot_Point', ['data', 'row', 'pos'])
        reg_point = Pivot_Point(0,0,0)

        ####Find first Swing point####

        HH = (OHLC_data.iloc[0], 0)
        LL = (OHLC_data.iloc[0], 0)
        HH_ATR_Limit = HH[0][self.ref_column] - (HH[0]["ATR"]*self.price_factor)
        LL_ATR_Limit = LL[0][self.ref_column] + (LL[0]["ATR"]*self.price_factor)

        found_first_swing = False
        while not found_first_swing and row_count < total_rows:
            current_row = OHLC_data.iloc[row_count]

            if current_row[self.ref_column] >= LL_ATR_Limit and (row_count - self.time_factor) > LL[1]:
                swing_writer.writerow([LL[0]['Date_Time'], LL[0][self.ref_column], "Low", LL[1]]) #write out first swing point
                reg_point = Pivot_Point(current_row, row_count, "High")
                found_first_swing = True
            elif current_row[self.ref_column] <= HH_ATR_Limit and (row_count - self.time_factor) > HH[1]:
                swing_writer.writerow([HH[0]['Date_Time'], HH[0][self.ref_column], "High", HH[1]]) #write out first swing point
                reg_point = Pivot_Point(current_row, row_count, "Low")
                found_first_swing = True
            elif current_row[self.ref_column] < LL[0][self.ref_column]:
                LL = (current_row, row_count)
                LL_ATR_Limit = LL[0][self.ref_column] + (LL[0]["ATR"]*self.price_factor)
            elif current_row[self.ref_column] > HH[0][self.ref_column]:
                HH = (current_row, row_count)
                HH_ATR_Limit = HH[0][self.ref_column] - (HH[0]["ATR"]*self.price_factor)
            row_count += 1

        if not found_first_swing:
            eprint("Never found a swing")
            return False

        if self.DEBUG:
            logging.debug("First Registerd Point", reg_point)
            logging.debug("Current Row Count:", row_count, "\t Total Rows:", total_rows)


        #######Find all swings following first swing by looping through prices until finding new RP#######
        while row_count < total_rows:
            current_row = OHLC_data.iloc[row_count]

            if reg_point.pos == "High":
                violation_price = reg_point.data[self.ref_column] - (reg_point.data["ATR"]*self.price_factor)

                if current_row[self.ref_column] > reg_point.data[self.ref_column]: #new extreme with direction
                    reg_point = reg_point._replace(data = current_row, row = row_count)
                elif current_row[self.ref_column] < violation_price and (row_count - self.time_factor) > reg_point.row: #Violated ATR range in opposite direction
                    if self.DEBUG:
                        logging.debug("Violated ATR in the Low direction. Register a new Low, write out previous RP High as Swing High")
                        logging.debug("Previous REgisted Point: ", reg_point)

                    swing_writer.writerow([reg_point.data["Date_Time"], reg_point.data[self.ref_column], reg_point.pos, reg_point.row]) #write out previous RP as SP
                    reg_point = Pivot_Point(current_row, row_count, "Low") #re-regsiter RP

                    if self.DEBUG:
                        logging.debug("New Registed Point: ", reg_point)

            elif reg_point.pos == "Low":
                violation_price = reg_point.data[self.ref_column] + (reg_point.data["ATR"]*self.price_factor)

                if current_row[self.ref_column] < reg_point.data[self.ref_column]: #new extreme with direction
                    reg_point = reg_point._replace(data = current_row, row = row_count)
                elif current_row[self.ref_column] > violation_price and (row_count - self.time_factor) > reg_point.row: #Violated ATR range in opposite direction
                    if self.DEBUG:
                        logging.debug("Violated ATR in the High direction. Register a new High, write out previous RP low as Swing low")
                        logging.debug("Previous REgisted Point: ", reg_point)

                    swing_writer.writerow([reg_point.data["Date_Time"], reg_point.data[self.ref_column], reg_point.pos, reg_point.row]) #write out previous RP as SP
                    reg_point = Pivot_Point(current_row, row_count, "High") #re-regsiter RP

                    if self.DEBUG:
                        logging.debug("New Registed Point: ", reg_point)
            else:
                eprint("Registered point posistion is something other than \"High\" or \"Low\"")
                return False

            row_count = row_count + 1
        ###############################################################################################################


        swing_writer.writerow([reg_point.data["Date_Time"], reg_point.data[self.ref_column], reg_point.pos, reg_point.row]) #set last RP as a SP
        swing_file.close()
        return True

    def Average_True_Range(self, df, n):
        """
        :param df: pandas.DataFrame
        :param n:
        :return: pandas.DataFrame
        """
        i = 1
        TR_l = [0]
        rows = len(df.index)
        while i < rows:
            TR = max(df.iloc[i]['High'] - df.iloc[i]['Low'], abs(df.iloc[i]['High'] - df.iloc[i-1]['Close']), abs(df.iloc[i]['Low'] - df.iloc[i-1]['Close']))
            TR_l.append(TR)
            i += 1
        TR_s = pd.Series(TR_l)
        ATR = pd.Series(TR_s.ewm(span=n, min_periods=n).mean(), name='ATR_' + str(n))
        df = df.join(ATR)
        return df

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
