# Created by Baole Fang at 7/31/23

import argparse
import os
from collections import defaultdict
from dataset.db import *


def get_mapping(root, group=False):
    tests = ['CppunitTest', 'JunitTest', 'UITest', 'PythonTest']
    test2parent = {}
    parent2test = defaultdict(list)
    all_tests = set()
    for subdir, dirs, files in os.walk(os.path.expanduser(root)):
        for file in files:
            prefix = file.split('_')[0]
            if prefix in tests:
                parent = os.path.basename(subdir)
                test = file.removeprefix(prefix + '_').removesuffix('.mk')
                test2parent[test] = parent
                parent2test[parent].append(test)
                if group:
                    all_tests.add(parent)
                else:
                    all_tests.add(test)
    return all_tests, test2parent, parent2test


def grouping(a, b, root, group=False):
    all_tests, test2parent, parent2test = get_mapping(root, group)
    if group:
        commits = list(read(a))
        for i in range(len(commits)):
            failures = set()
            for failure in commits[i]['failures']:
                try:
                    failures.add(test2parent[failure])
                except KeyError:
                    parent = failure.split('_')[0]
                    failures.add(parent)
                    all_tests.add(parent)
                finally:
                    commits[i]['failures'] = list(failures)
        write(commits, b)
    write(sorted(all_tests), 'data/tests.json')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Extract mappings of unit tests')
    parser.add_argument("--path", type=str, default="~/libreoffice", help="Path to libreoffice repository")
    parser.add_argument("--input", type=str, default="data/commits.json", help="Input path of ")
    parser.add_argument("--output", type=str, default="data/commits_group.json",
                        help="Output path of grouped commits.json")
    parser.add_argument("--group", action='store_true', help="Whether to group unit tests")
    args = parser.parse_args()
    grouping(args.input, args.output, args.path, args.group)
