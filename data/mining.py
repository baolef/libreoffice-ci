# Created by Baole Fang at 6/3/23

from git import Repo
from commit import Commit
import rust_code_analysis_server
from tqdm import tqdm


def get_commits(repo_path, limit):
    repo = Repo(repo_path)
    commits = list(repo.iter_commits(max_count=limit))
    output = []
    for commit in tqdm(commits):
        if commit.summary == 'Update git submodules':
            continue
        output.append(Commit(commit, code_analysis_server))
    code_analysis_server.terminate()
    return output


if __name__ == '__main__':
    code_analysis_server = rust_code_analysis_server.RustCodeAnalysisServer()
    get_commits('~/research/libre/libreoffice', 1024)
