# Created by Baole Fang at 6/3/23

from git import Repo
from commit import *
import rust_code_analysis_server
from tqdm import tqdm
import json
from experiences import calculate_experiences
from multiprocessing import Pool
import concurrent.futures


def write(obj: list[Commit], filename):
    with open(filename, 'w') as f:
        json.dump(obj, f, indent=2)

def _init_process(server) -> None:
    global REPO, SERVER
    REPO=Repo('~/research/libre/libreoffice')
    SERVER = server

def _transform(commit):
    c=REPO.commit(commit.node)
    return commit.transform(c,SERVER)


def get_commits(repo: Repo, limit):
    commits=[]
    for commit in repo.iter_commits(max_count=limit):
        if commit.summary=='Update git submodules':
            continue
        commits.append(Commit(commit))
    return list(reversed(commits))

def get_features(repo_path, limit=None, save=True):
    repo = Repo(repo_path)

    commits = get_commits(repo,limit)
    first_pushdate = commits[0].pushdate
    # output = []
    # global code_analysis_server
    code_analysis_server = rust_code_analysis_server.RustCodeAnalysisServer()
    # with concurrent.futures.ProcessPoolExecutor(
    #         initializer=_init_process,
    #         initargs=(repo,code_analysis_server,),
    #         # Fixing https://github.com/mozilla/bugbug/issues/3131
    #         mp_context=mp.get_context("fork"),
    # ) as executor:
    #     # executor.map(_transform, commits, chunksize=64)
    #     commits_iter = executor.map(_transform, commits)
    #     commits_iter = tqdm(commits_iter, total=len(commits))
    #     output = list(commits_iter)
    # _init_process(repo, code_analysis_server)


    # with Pool(6,initializer=_init_process,initargs=(code_analysis_server,)) as p:
    #     commits=list(tqdm(p.imap(_transform,commits),total=len(commits)))


    for commit in tqdm(commits):
        commit.transform(repo.commit(commit.node),code_analysis_server)


    # for commit in tqdm(commits):
    #     if commit.summary == 'Update git submodules':
    #         continue
    #     output.append(Commit(commit, code_analysis_server))
    code_analysis_server.terminate()
    calculate_experiences(commits, first_pushdate, save)
    for i in range(len(commits)):
        commits[i] = commits[i].to_dict()
    if save:
        write(commits, 'commits.json')
    return commits


if __name__ == '__main__':

    data = get_features('~/research/libre/libreoffice', 64)
