# Created by Baole Fang at 6/3/23

import os
from git import Repo
from commit import Commit
import rust_code_analysis_server
from tqdm import tqdm
from experiences import calculate_experiences
from multiprocessing import Pool
import csv
from collections import defaultdict
from db import *
import logging
import argparse

logger = logging.getLogger(__name__)


def fetch(repo: Repo, lines):
    remote = repo.remotes[0]
    for line in tqdm(lines):
        remote.fetch(line[6])


def _fetch(line):
    REMOTE.fetch(line)


def read(lines, limit):
    mapping = defaultdict(set)
    for line in tqdm(lines, desc='reading csv'):
        if line[7] == 'no-githash-info':
            continue
        key = (line[6], line[7])
        if line[10] == 'SUCCESS':
            mapping[key] = mapping[key]
        else:
            for i in range(11, len(line), 2):
                if line[i] == ['uitest,tests', 'python,tests']:
                    mapping[key].add(line[i + 1].split()[2].split('_', 1)[1])
                elif line[i] in ['cppunit,tests', 'junit,tests']:
                    mapping[key].add(line[i + 1].split()[3].split('_', 1)[1])
    if limit:
        return {k: v for k, v in list(mapping.items())[:limit]}
    return mapping


def get_rows(filename):
    with open(filename) as f:
        file = csv.reader(f, delimiter='\t')
        lines = list(file)[1:-1]
    return lines


def _init_process(server, root) -> None:
    global REPO, SERVER
    REPO = Repo(root)
    SERVER = server


def _init_fetch(root) -> None:
    global REMOTE
    REMOTE = Repo(root).remotes[0]


def _init_repo(root) -> None:
    global REPO, REMOTE
    REPO = Repo(root)
    REMOTE = REPO.remotes[0]


def _transform(commit):
    c = REPO.commit(commit.node)
    try:
        return commit.transform(c, SERVER)
    except:
        logger.debug(f'commit {commit.node} transform error')
        return None


def _get(item):
    key, value = item
    try:
        commit = Commit(REPO.commit(key[1]), list(value))
    except:
        REMOTE.fetch(key[0])
        commit = Commit(REPO.commit(key[1]), list(value))
    finally:
        return commit


def get_features(repo_path, limit=None, save=True, single_process=False):
    repo = Repo(repo_path)

    rows = get_rows('data/jenkinsfullstats.csv')

    raw = read(rows, limit)
    if single_process:
        commits = []
        for item in tqdm(raw.items(), desc='initializing commits'):
            commits.append(_get(item))
    else:
        with Pool(os.cpu_count(), initializer=_init_repo, initargs=(repo_path,)) as p:
            commits = list(tqdm(p.imap(_get, raw.items()), total=len(raw), desc='initializing commits'))

    commits.sort(key=lambda x: x.pushdate)

    first_pushdate = commits[0].pushdate

    if single_process:
        code_analysis_server = rust_code_analysis_server.RustCodeAnalysisServer(1)
        for commit in tqdm(commits, desc='transforming commits'):
            commit.transform(repo.commit(commit.node), code_analysis_server)
    else:
        code_analysis_server = rust_code_analysis_server.RustCodeAnalysisServer()
        with Pool(os.cpu_count(), initializer=_init_process, initargs=(code_analysis_server,repo_path)) as p:
            commits = list(tqdm(p.imap(_transform, commits), total=len(commits), desc='transforming commits'))

    code_analysis_server.terminate()
    commits = [commit for commit in commits if commit]
    calculate_experiences(commits, first_pushdate, save)
    for i in range(len(commits)):
        commits[i] = commits[i].to_dict()
    if save:
        write(commits, 'data/commits.json')
    return commits


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Extract features of gerrit pushes')
    parser.add_argument("--path", type=str, required=True, help="Path to libreoffice repository")
    parser.add_argument("--limit", type=int, default=None, help="Limit of the number of pushes")
    args = parser.parse_args()
    data = get_features(args.path, args.limit)
