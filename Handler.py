import pandas as pd
from Swings import *

def read_in_data(filename):
    data_frame = pd.read_csv(filename, names=['Date_Time', 'Open', 'High', 'Low', 'Close'], parse_dates=True)
    return data_frame

generate_swings(read_in_data("testData.csv"), "Swings.csv")
