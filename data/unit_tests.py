# Created by Baole Fang at 6/12/23

import pickle

def read_all_unit_tests(filename):
    tests=set()
    tags=['CUT','UIT','JUT','PYT']
    for i in range(len(tags)):
        tags[i]=f'[build {tags[i]}]'
    with open(filename) as f:
        for line in f.readlines():
            if line[:11] in tags:
                tests.add(line.split()[-1])
    return tests

if __name__ == '__main__':
    tests=read_all_unit_tests('')