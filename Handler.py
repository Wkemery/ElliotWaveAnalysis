import pandas as pd
from Swings import *
from ElliotAnalyzer import *
import os
import time


# sg = Swing_Generator("testdatabig.csv", "swings.csv")
# if(os.path.isfile("swings.csv")):
#     sg.update_swings()
# else:
#     sg.generate_swings()
# sg.export_OHLC_graph()

FOREX_DATA_PATH = "C:\\Users\\wyatt\\Documents\\ForexData"
GRAPHS_PATH = "C:\\Users\\wyatt\\Documents\\ForexGraphs"
ANALYSIS_SUMMARY_PATH = ".\\"

with open("Pair_Analysis.txt", 'r') as infile:
    pairs_to_analyze = infile.read().splitlines()

outfile = open(ANALYSIS_SUMMARY_PATH + "summary_analysis.txt", 'w')

for pair in pairs_to_analyze:
    pairname, pairtime = pair.split("_")
    forex_name_template = FOREX_DATA_PATH + "\\" + pairname + "\\"
    forex_data_file = forex_name_template + pair + ".csv"
    forex_swing_file =  forex_name_template + pair + "_swings.csv"

    sg = Swing_Generator(forex_data_file,forex_swing_file)
    if(os.path.isfile(forex_swing_file)):
        sg.update_swings()
    else:
        sg.generate_swings()

    ea = Elliot_Analyzer(pair, forex_swing_file, forex_data_file)
    analysis_summary = ea.analyze()
    if analysis_summary != []:
        ea.export_graph(GRAPHS_PATH + "\\" + pair + "_waves.html")
        outfile.write(pair + "\t" + str(analysis_summary) + "\n")

outfile.close()

print("Total Time: ", time.process_time())
