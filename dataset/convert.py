# Created by Baole Fang at 6/15/23

from db import *

if __name__ == '__main__':
    obj = read('data/commits.json')
    write(obj, 'data/commits.pickle.zstd')
