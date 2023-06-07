# Created by Baole Fang at 6/3/23

from git import Repo
from commit import Commit
import rust_code_analysis_server
from tqdm import tqdm
from experiences import calculate_experiences


def get_commits(repo_path, limit=None, save=True):
    repo = Repo(repo_path)
    commits = list(repo.iter_commits(max_count=limit))
    first_pushdate = commits[-1].committed_datetime
    output = []
    for commit in tqdm(commits):
        if commit.summary == 'Update git submodules':
            continue
        output.append(Commit(commit, code_analysis_server))
    code_analysis_server.terminate()
    calculate_experiences(output, first_pushdate, save)
    for i in range(len(output)):
        output[i] = output[i].to_dict()
    return output


if __name__ == '__main__':
    code_analysis_server = rust_code_analysis_server.RustCodeAnalysisServer()
    data = get_commits('~/research/libre/libreoffice', 1024)
