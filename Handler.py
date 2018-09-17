import pandas as pd
from Swings import *

sg = Swing_Generator("C:\\Users\\wyatt\\Documents\\ForexData\\AUDCAD\\AUDCAD_D.csv", "swings.csv")
# sg = Swing_Generator("testData.csv", "swings.csv")
sg.generate_swings()
sg.export_OHLC_graph()
