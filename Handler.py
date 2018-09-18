import pandas as pd
from Swings import *
from ElliotAnalyzer import *

sg = Swing_Generator("C:\\Users\\wyatt\\Documents\\ForexData\\EURGBP\\EURGBP_H4.csv", "swings.csv")
# sg = Swing_Generator("testData.csv", "swings.csv")
sg.generate_swings(backwards=False)
sg.export_OHLC_graph()

# ea = Elliot_Analyzer("EURGBP_H4", "swings.csv", sg.OHLC_data)
# if(ea.analyze()):
#     ea.export_graph()
