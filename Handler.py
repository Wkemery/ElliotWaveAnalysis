import pandas as pd
from Swings import *
from ElliotAnalyzer import *

sg = Swing_Generator("C:\\Users\\wyatt\\Documents\\ForexData\\CHFJPY\\CHFJPY_H1.csv", "swings.csv")
# sg = Swing_Generator("testData.csv", "swings.csv")
sg.generate_swings(backwards=False)
sg.export_OHLC_graph()

ea = Elliot_Analyzer("CHFJPY_H1", "swings.csv", sg.OHLC_data)
if(ea.analyze()):
    ea.export_graph()
