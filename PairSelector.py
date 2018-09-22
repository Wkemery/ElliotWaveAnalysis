import os

FOREX_DATA_PATH = "C:\\Users\\wyatt\\Documents\\ForexData"

outfile = open('Pair_Analysis.txt', 'w')
FX_pairs = os.listdir(FOREX_DATA_PATH)

for pair in FX_pairs:
    outfile.write(pair + "_H1" + "\n")
    outfile.write(pair + "_H4" + "\n")
    outfile.write(pair + "_D" + "\n")
