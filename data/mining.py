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


def fetch(repo: Repo, lines):
    remote = repo.remotes[0]
    for line in tqdm(lines):
        remote.fetch(line[6])


def read(repo: Repo, lines):
    commits = []
    for line in tqdm(lines):
        hash = line[7]
        if line[10] == 'SUCCESS':
            commits.append(Commit(repo.commit(hash)))
        else:
            tests = []
            for i in range(11, len(line), 2):
                if line[i] in ['cppunit,tests', 'junit,tests', 'python,tests']:
                    tests.append(line[i + 1].split()[2])
            if tests:
                commits.append(Commit(repo.commit(hash), tests))
    commits.sort(key=lambda x: x.pushdate)
    return commits
    # return list(reversed(commits))


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


def _transform(commit):
    c = REPO.commit(commit.node)
    return commit.transform(c, SERVER)


def get_commits(repo: Repo, limit):
    commits = []
    for commit in repo.iter_commits(max_count=limit):
        if commit.summary == 'Update git submodules':
            continue
        commits.append(Commit(commit))
    return list(reversed(commits))


def get_features(repo_path, filename, limit=None, download=False, save=True, single_process=False):
    repo = Repo(repo_path)

    rows = get_rows(filename, limit)
    if download:
        fetch(repo, rows)

    commits = read(repo, rows)

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
    data = get_features(root, 'jenkinsfullstats.csv', 1024)
