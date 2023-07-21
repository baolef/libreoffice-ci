# Created by Baole Fang at 6/30/23
import argparse
import os.path
from logging import getLogger

from dataset import rust_code_analysis_server
from models.testfailure import TestFailureModel
from models.testselect import TestLabelSelectModel
from git import Repo
from dataset.commit import Commit
import csv
from datetime import datetime

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

    def classify(self, revision: str, save: bool, csv_path: str, id: str):
        commit = self.get_commit(revision)
        testfailure_probs = self.testfailure_model.classify(commit, probabilities=True)
        logger.info("Test failure risk: %f", testfailure_probs[0][1])
        selected_tasks = self.model.select_tests([commit], self.confidence_threshold)
        selected_tasks = dict(sorted(selected_tasks.items()))

        for selected_task, prob in selected_tasks.items():
            print(f"[Unit Test] {selected_task}: {prob}")

        os.environ['PROBABILITY'] = testfailure_probs[0][1]

        with open(os.path.join(csv_path, 'probability.csv'), 'w') as f:
            writer = csv.writer(f)
            writer.writerow(['id', id])
            writer.writerow(['datetime', str(datetime.now())])
            writer.writerow(['overall', testfailure_probs[0][1]])
            writer.writerows(selected_tasks.items())

        if save:
            with open("failure_risk", "w") as f:
                f.write(
                    "1"
                    if testfailure_probs[0][1]
                       > self.confidence_threshold
                    else "0"
                )
            with open("selected_tasks", "w") as f:
                f.writelines(
                    f"{selected_task}: {prob}\n" for selected_task, prob in selected_tasks.items()
                )


def main() -> None:
    description = "Classify a commit"
    parser = argparse.ArgumentParser(description=description)

    parser.add_argument("model", help="Which model to use for evaluation.")
    parser.add_argument(
        "--path",
        type=str,
        default="~/libreoffice",
        help="Path to a Gecko repository. If no repository exists, it will be cloned to this location.",
    )
    parser.add_argument(
        "--csv",
        type=str,
        default='./',
        help="Path to csv.",
    )
    parser.add_argument(
        "--id",
        type=str,
        default='',
        help="Gerrit id.",
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
        help="Confidence threshold determining whether tests should be run."
    )
    parser.add_argument("--save", action="store_true", help="Whether to write results to file.")

    args = parser.parse_args()

    if not args.model.endswith('model'):
        args.model = args.model + 'model'

    classifier = CommitClassifier(
        args.model,
        args.path,
        args.use_single_process,
        args.skip_feature_importance,
        args.confidence_threshold
    )
    classifier.classify(args.revision, args.save, args.csv, args.id)


if __name__ == '__main__':
    main()
