# Created by Baole Fang at 6/30/23
import argparse
from logging import getLogger

from dataset import rust_code_analysis_server
from models.base import Model
from models.testfailure import TestFailureModel
from models.testselect import TestLabelSelectModel
from git import Repo
from dataset.commit import Commit

logger = getLogger(__name__)


class CommitClassifier:
    def __init__(
            self,
            model_name: str,
            repo_dir: str,
            use_single_process: bool,
            skip_feature_importance: bool,
            confidence_threshold: float,
    ):
        self.model_name = model_name
        self.use_single_process = use_single_process
        self.skip_feature_importance = skip_feature_importance
        self.testfailure_model = TestFailureModel.load('testfailuremodel')
        self.model: TestLabelSelectModel = TestLabelSelectModel.load(model_name)
        self.repo = Repo(repo_dir)
        self.confidence_threshold = confidence_threshold
        self.code_analysis_server = rust_code_analysis_server.RustCodeAnalysisServer()

    def get_commit(self, revision):
        if revision:
            try:
                c = self.repo.commit(revision)
            except:
                self.repo.remotes[0].fetch(revision)
                c = self.repo.commit(revision)
            finally:
                commit = Commit(c)
                commit.transform(c, self.code_analysis_server)
                return commit.to_dict()
        else:
            c = self.repo.head.commit
            commit = Commit(c)
            commit.transform(c, self.code_analysis_server)
            return commit.to_dict()

    def classify(self, revision: str):
        commit = self.get_commit(revision)
        testfailure_probs = self.testfailure_model.classify(commit, probabilities=True)
        logger.info("Test failure risk: %f", testfailure_probs[0][1])
        selected_tasks = self.model.select_tests([commit], self.confidence_threshold)

        with open("failure_risk", "w") as f:
            f.write(
                "1"
                if testfailure_probs[0][1]
                   > self.confidence_threshold
                else "0"
            )
        print(f"overall failure risk: {testfailure_probs[0][1]}")
        with open("selected_tasks", "w") as f:
            f.writelines(
                f"{selected_task}: {prob}\n" for selected_task, prob in selected_tasks.items()
            )
        for selected_task, prob in selected_tasks.items():
            print(f"{selected_task}: {prob}")


def main() -> None:
    description = "Classify a commit"
    parser = argparse.ArgumentParser(description=description)

    parser.add_argument("model", help="Which model to use for evaluation")
    parser.add_argument(
        "--path",
        type=str,
        default="~/libreoffice",
        help="Path to a Gecko repository. If no repository exists, it will be cloned to this location.",
    )

    parser.add_argument("--revision", help="revision to analyze. If not specify, use the last commit.", type=str)
    parser.add_argument(
        "--use-single-process",
        action="store_true",
        help="Whether to use a single process.",
    )
    parser.add_argument(
        "--skip-feature-importance",
        action="store_true",
        help="Whether to skip feature importance calculation.",
    )
    parser.add_argument(
        "--confidence_threshold",
        type=float,
        default=0.5,
        help="Confidence threshold determining whether tests should be run"
    )

    args = parser.parse_args()

    if not args.model.endswith('model'):
        args.model = args.model + 'model'

    classifier = CommitClassifier(
        args.model,
        args.repo_dir,
        args.use_single_process,
        args.skip_feature_importance,
        args.confidence_threshold
    )
    classifier.classify(args.revision)


if __name__ == '__main__':
    main()
