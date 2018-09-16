import pandas as pd
from Swings import *

sg = Swing_Generator("testData.csv")
sg.generate_swings("Swings.csv")
