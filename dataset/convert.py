# Created by Baole Fang at 6/15/23
import argparse

from db import *


def convert(a, b):
    obj = read(a)
    write(obj, b)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Convert database format')
    parser.add_argument("input", type=str, help="Input file")
    parser.add_argument("output", type=str, help="Output file")
    args = parser.parse_args()
    convert(args.input, args.output)
