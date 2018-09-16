import pandas as pd
import collections
import copy
import csv
from Error import *

DEBUG = True

def generate_swings(OHLC_data, outfile):
    #Setup Stuff
    swing_file = open(outfile, 'w')
    swing_writer = csv.writer(swing_file, delimiter=',')

    reference_price = "Close"
    ATR_period = 2
    time_factor = 5


    OHLC_data = Average_True_Range(OHLC_data, ATR_period).dropna()
    OHLC_data = OHLC_data.rename(columns = {'ATR_' + str(ATR_period) : 'ATR'})
    total_rows = len(OHLC_data.index)
    if total_rows is 0:
        eprint("Not enough data to calculate ATR")
        return False

########################################################################################################################
    #Find first Swing point

    row_count = 0

    Pivot_Point = collections.namedtuple('Pivot_Point', ['date_time', 'price', 'atr', 'pos'])
    first_swing_point = Pivot_Point("", 0, 0, "")
    reg_point = Pivot_Point("", 0, 0, "")

    HH = (OHLC_data.iloc[0], 0)
    LL = (OHLC_data.iloc[0], 0)
    HH_ATR_Limit = HH[0][reference_price] - HH[0]["ATR"]
    LL_ATR_Limit = LL[0][reference_price] + LL[0]["ATR"]

    found_first_swing = False
    while not found_first_swing and row_count < total_rows:
        current_row = OHLC_data.iloc[row_count]

        if current_row[reference_price] >= LL_ATR_Limit and (row_count - time_factor) > LL[1]:
            swing_writer.writerow([LL[0]['Date_Time'], LL[0][reference_price], "Low"]) #write out first swing point
            reg_point = Pivot_Point(current_row["Date_Time"], current_row[reference_price],  current_row["ATR"], "High")
            found_first_swing = True
        elif current_row[reference_price] <= HH_ATR_Limit and (row_count - time_factor) > HH[1]:
            swing_writer.writerow([LL[0]['Date_Time'], LL[0][reference_price], "High"]) #write out first swing point
            reg_point = Pivot_Point(current_row["Date_Time"], current_row[reference_price],  current_row["ATR"], "Low")
            found_first_swing = True
        elif current_row[reference_price] < LL[0][reference_price]:
            LL = (current_row, row_count)
            LL_ATR_Limit = LL[0][reference_price] + LL[0]["ATR"]
        elif current_row[reference_price] > HH[0][reference_price]:
            HH = (current_row, row_count)
            HH_ATR_Limit = HH[0][reference_price] - HH[0]["ATR"]
        row_count += 1

    if not found_first_swing:
        eprint("Never found a swing")
        return False

    if DEBUG:
        print(reg_point)
        print(row_count, total_rows)

########################################################################################################################

    #Find all swings following first swing by looping through prices until finding new RP
    while row_count < total_rows:
        current_row = OHLC_data.iloc[row_count]

        if reg_point.pos is "High":
            violation_price = reg_point.price - reg_point.atr

            if current_row[reference_price] > reg_point.price: #new extreme with direction
                reg_point = reg_point._replace(price = current_row[reference_price], date_time = current_row["Date_Time"], atr = current_row["ATR"])
            elif current_row[reference_price] < violation_price: #Violated ATR range in opposite direction
                swing_writer.writerow([reg_point.date_time, reg_point.price, reg_point.pos]) #write out previous RP as SP
                reg_point = Pivot_Point(current_row["Date_Time"], current_row[reference_price], current_row["ATR"], "Low") #re-regsiter RP
                row_count = row_count + time_factor - 1 #Skip X bars

        elif reg_point.pos is "Low":
            violation_price = reg_point.price + reg_point.atr

            if current_row[reference_price] < reg_point.price: #new extreme with direction
                reg_point = reg_point._replace(price = current_row[reference_price], date_time = current_row["Date_Time"], atr = current_row["ATR"])
            elif current_row[reference_price] > violation_price: #Violated ATR range in opposite direction
                swing_writer.writerow([reg_point.date_time, reg_point.price, reg_point.pos]) #write out previous RP as SP
                reg_point = Pivot_Point(current_row["Date_Time"], current_row[reference_price], current_row["ATR"], "High") #re-regsiter RP
                row_count = row_count + time_factor - 1 #Skip X bars
        else:
            eprint("Registered point posistion is something other than \"High\" or \"Low\"")
            return False

        row_count = row_count + 1
########################################################################################################################

        #set last RP as a SP
    swing_writer.writerow([reg_point.date_time, reg_point.price, reg_point.pos])
    swing_file.close()
    return True
########################################################################################################################

def Average_True_Range(df, n):
    """
    :param df: pandas.DataFrame
    :param n:
    :return: pandas.DataFrame
    """
    i = 0
    TR_l = [0]
    while i < df.index[-1]:
        TR = max(df.loc[i + 1, 'High'], df.loc[i, 'Close']) - min(df.loc[i + 1, 'Low'], df.loc[i, 'Close'])
        TR_l.append(TR)
        i = i + 1
    TR_s = pd.Series(TR_l)
    ATR = pd.Series(TR_s.ewm(span=n, min_periods=n).mean(), name='ATR_' + str(n))
    df = df.join(ATR)
    return df
