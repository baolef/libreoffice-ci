# Created by Baole Fang at 6/3/23

from git import Repo
from commit import Commit
import rust_code_analysis_server
from tqdm import tqdm
import json
from experiences import calculate_experiences


def write(obj: list[Commit], filename):
    with open(filename, 'w') as f:
        json.dump(obj, f, indent=2)


def get_commits(repo_path, limit=None, save=True):
    repo = Repo(repo_path)
    commits = list(reversed(list(repo.iter_commits(max_count=limit))))
    first_pushdate = commits[0].committed_datetime
    output = []
    for commit in tqdm(commits):
        if commit.summary == 'Update git submodules':
            continue
        output.append(Commit(commit, code_analysis_server))
    code_analysis_server.terminate()
    calculate_experiences(output, first_pushdate, save)
    for i in range(len(output)):
        output[i] = output[i].to_dict()
    if save:
        write(output, 'commits.json')
    return output


if __name__ == '__main__':
    code_analysis_server = rust_code_analysis_server.RustCodeAnalysisServer()
    data = get_commits('~/research/libre/libreoffice', 1024)
