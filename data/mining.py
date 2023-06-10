# Created by Baole Fang at 6/3/23

import os
from git import Repo
from commit import Commit
import rust_code_analysis_server
from tqdm import tqdm
import json
from experiences import calculate_experiences
from multiprocessing import Pool
import csv
from collections import defaultdict


def fetch(repo: Repo, lines):
    remote = repo.remotes[0]
    for line in tqdm(lines):
        remote.fetch(line[6])

def _fetch(line):
    REMOTE.fetch(line)

def read(lines):
    mapping=defaultdict(set)
    for line in tqdm(lines):
        if line[7]=='no-githash-info':
            continue
        key = (line[6],line[7])
        if line[10] == 'SUCCESS':
            mapping[key]=mapping[key]
        else:
            for i in range(11, len(line), 2):
                if line[i]=='uitest,tests':
                    mapping[key].add(line[i + 1].split()[2])
                elif line[i] in ['cppunit,tests', 'junit,tests', 'python,tests']:
                    mapping[key].add(line[i + 1].split()[3])
    return mapping

def get_rows(filename, limit):
    with open(filename) as f:
        file = csv.reader(f, delimiter='\t')
        lines = list(file)[1:-1]
    return lines[:limit]


def write(obj: list[Commit], filename):
    with open(filename, 'w') as f:
        json.dump(obj, f, indent=2)


def _init_process(server) -> None:
    global REPO, SERVER
    REPO = Repo(root)
    SERVER = server

def _init_fetch() -> None:
    global REMOTE
    REMOTE = Repo(root).remotes[0]

def _init_repo()  -> None:
    global REPO, REMOTE
    REPO = Repo(root)
    REMOTE = REPO.remotes[0]

def _transform(commit):
    c = REPO.commit(commit.node)
    return commit.transform(c, SERVER)


def _get(item):
    key,value=item
    try:
        commit = Commit(REPO.commit(key[1]),list(value))
    except:
        REMOTE.fetch(key[0])
        commit = Commit(REPO.commit(key[1]), list(value))
    finally:
        return commit


def get_features(repo_path, filename, limit=None, download=False, save=True, single_process=False):
    repo = Repo(repo_path)

    rows = get_rows(filename, limit)
    # hashes=set(row[6] for row in rows)
    # if download:
    #     if single_process:
    #         fetch(repo, hashes)
    #     else:
    #         with Pool(os.cpu_count(), initializer=_init_fetch) as p:
    #             list(tqdm(p.imap(_fetch, hashes), total=len(hashes)))

    raw = read(rows)
    if single_process:
        commits = []
        for item in tqdm(raw.items()):
            commits.append(_get(item))
    else:
        with Pool(os.cpu_count()*2, initializer=_init_repo) as p:
            commits = list(tqdm(p.imap(_get, raw.items()), total=len(raw)))

    commits.sort(key=lambda x: x.pushdate)


    # commits = get_commits(repo, limit)
    first_pushdate = commits[0].pushdate

    if single_process:
        code_analysis_server = rust_code_analysis_server.RustCodeAnalysisServer(1)
        for commit in tqdm(commits):
            commit.transform(repo.commit(commit.node), code_analysis_server)
    else:
        code_analysis_server = rust_code_analysis_server.RustCodeAnalysisServer()
        with Pool(os.cpu_count(), initializer=_init_process, initargs=(code_analysis_server,)) as p:
            commits = list(tqdm(p.imap(_transform, commits), total=len(commits)))

    code_analysis_server.terminate()
    calculate_experiences(commits, first_pushdate, save)
    for i in range(len(commits)):
        commits[i] = commits[i].to_dict()
    if save:
        write(commits, 'commits.json')
    return commits


if __name__ == '__main__':
    root = '~/research/libre/libreoffice'
    data = get_features(root, 'jenkinsfullstats.csv')
