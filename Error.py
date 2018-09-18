from __future__ import print_function
import sys
import logging
logging.basicConfig(filename='LocalLog.txt', level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')

def eprint(*args, **kwargs):
    print('\t*Error Occured*',file=sys.stderr)
    print(*args, file=sys.stderr, **kwargs)
