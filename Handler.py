import pandas as pd
from Swings import *
from ElliotAnalyzer import *

sg = Swing_Generator("C:\\Users\\wyatt\\Documents\\ForexData\\AUDCAD\\AUDCAD_H4.csv", "swings.csv")
# sg = Swing_Generator("testData.csv", "swings.csv")
sg.generate_swings()
# sg.export_OHLC_graph()

ea = Elliot_Analyzer("AUDCAD_H4", "swings.csv", sg.OHLC_data)
if(ea.analyze()):
    ea.export_graph()
