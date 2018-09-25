import pandas as pd
from Swings import *
from ElliotAnalyzer import *
import os
import time
import configparser
import shutil

FOREX_DATA_PATH = "C:\\Users\\wyatt\\Documents\\ForexData"
GRAPHS_PATH = "C:\\Users\\wyatt\\Documents\\ForexGraphs"
ANALYSIS_SUMMARY_FILE = "summary_analysis.txt"
CONFIG_FILE= "Handler_Config.conf"
PAIRS_FILE = "Pair_Analysis.txt"
TYPICAL = True

#TODO: add support for other config options to do big multiconfig, multitimeframe analysis at once
########################################################################################################################

def config_section_map(config, section):
    dict1 = {}
    options = config.options(section)
    for option in options:
        try:
            dict1[option] = config.get(section, option)
            if dict1[option] == -1:
                print("skip: %s" % option)
        except:
            print("exception on %s!" % option)
            dict1[option] = None
    return dict1

#Read in config
config = configparser.ConfigParser()
config.read(CONFIG_FILE)
ST_config = config_section_map(config, "Short_Term")
print(ST_config)
IT_config = config_section_map(config, "Intermediate_Term")
LT_config = config_section_map(config, "Long_Term")
MT_config = config_section_map(config, "Major_Term")
config_list = [(ST_config, "ST"), (IT_config, "IT"), (LT_config, "LT"), (MT_config, "MT")] #TODO: determine which configs to use this time

#Set up analysis parameters
typical = config_section_map(config, "Other")["typical"]

########################################################################################################################

#Get the pairs to analyze
with open(PAIRS_FILE, 'r') as infile:
    pairs_to_analyze = infile.read().splitlines()

outfile = open(ANALYSIS_SUMMARY_FILE, 'w')

#Clear old graphs
for file in os.listdir(GRAPHS_PATH):
    os.remove(GRAPHS_PATH + "\\" + file)

########################################################################################################################
#Begin analyzing Pairs
for pair in pairs_to_analyze:
    pairname, pairtime = pair.split("_")
    forex_name_template = FOREX_DATA_PATH + "\\" + pairname + "\\"
    forex_data_file = forex_name_template + pair + ".csv"

    for current_config, config_name in config_list:
        forex_swing_file =  forex_name_template + pair + "_swings_" + current_config["atr_period"] + "_" + current_config["time_factor"] + "_" + current_config["price_factor"] + ".csv"

        sg = Swing_Generator(forex_data_file,forex_swing_file, current_config)
        if(os.path.isfile(forex_swing_file)):
            sg.update_swings()
        else:
            sg.generate_swings()

        ea = Elliot_Analyzer(pair, forex_swing_file, forex_data_file)
        analysis_summary = ea.analyze()
        for result in analysis_summary:
            if typical == "1":
                if ea.wave_data[result][1] != "Minimum":
                    ea.export_graphs(GRAPHS_PATH + "\\" + pair + "_" + config_name)
                    outfile.write(pair + "\t" + result + "\t" + ea.wave_data[result][1] + "\t" + config_name + "\n")
            else:
                ea.export_graphs(GRAPHS_PATH + "\\" + pair + "_" + config_name)
                outfile.write(pair + "\t" + result + "\t" + ea.wave_data[result][1] + "\t" + config_name + "\n")

        print('.', end='', flush=True)

outfile.close()

print("Total Time: ", time.process_time())
