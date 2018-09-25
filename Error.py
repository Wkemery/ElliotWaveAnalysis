from __future__ import print_function
import sys


def eprint(*args, **kwargs):
    print('\t*Error Occured*',file=sys.stderr)
    print(*args, file=sys.stderr, **kwargs)
