# -*- coding: utf-8 -*-
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this file,
# You can obtain one at http://mozilla.org/MPL/2.0/.

import logging
import pickle

import numpy as np
import xgboost
from imblearn.under_sampling import RandomUnderSampler
from sklearn.compose import ColumnTransformer
from sklearn.feature_extraction import DictVectorizer
from sklearn.pipeline import Pipeline
from sklearn.neural_network import MLPClassifier
from tqdm import tqdm

from dataset import commit_features, db
from .base import Model
from . import register
import utils

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@register('testoverall')
class TestOverallModel(Model):
    def __init__(self, lemmatization=False,path='data/commits.json',):
        Model.__init__(self, lemmatization,path)

        self.sampler = RandomUnderSampler(random_state=0)

        feature_extractors = [
            commit_features.source_code_file_size(),
            commit_features.other_file_size(),
            commit_features.test_file_size(),
            commit_features.source_code_added(),
            commit_features.other_added(),
            commit_features.test_added(),
            commit_features.source_code_deleted(),
            commit_features.other_deleted(),
            commit_features.test_deleted(),
            # commit_features.author_experience(),
            # commit_features.reviewer_experience(),
            commit_features.reviewers_num(),
            # commit_features.component_touched_prev(),
            # commit_features.directory_touched_prev(),
            # commit_features.file_touched_prev(),
            commit_features.types(),
            commit_features.files(),
            commit_features.components(),
            commit_features.components_modified_num(),
            commit_features.directories(),
            commit_features.directories_modified_num(),
            commit_features.source_code_files_modified_num(),
            commit_features.other_files_modified_num(),
            commit_features.test_files_modified_num(),
            commit_features.probability()
        ]

        self.extraction_pipeline = Pipeline(
            [
                (
                    "commit_extractor",
                    commit_features.CommitExtractor(feature_extractors, []),
                ),
                ("union", ColumnTransformer([("data", DictVectorizer(dtype=np.float32), "data")])),
            ]
        )

        # self.clf=MLPClassifier(hidden_layer_sizes=[1024,1024,1024],verbose=True,max_iter=100)
        self.clf = xgboost.XGBClassifier(n_jobs=utils.get_physical_cpu_count())
        self.clf.set_params(predictor="cpu_predictor")

    def items_gen(self, limit=None):
        with open("testlabelselectmodel_data_y_pred", "rb") as f:
            probability=pickle.load(f)[:,1].reshape(-1,len(list(db.read('data/tests.json'))))

        commit_map = utils.get_commit_map(path=self.commits_path)

        assert len(commit_map) > 0
        i=0

        for item in tqdm(db.read('data/test_scheduling.pickle.zstd'), total=min(limit,len(commit_map)) if limit else len(commit_map), desc='generating data'):
            if limit and i > limit:
                break
            revs, test_datas = item['revs'], item['data']

            commits = tuple(
                commit_map[revision] for revision in revs if revision in commit_map
            )
            if len(commits) == 0:
                continue

            commit_data = commit_features.merge_commits(commits)
            commit_data['probability']=probability[i]
            label=1 if any(commit['failures'] for commit in commits) else 0
            i += 1
            yield commit_data, label

    def get_labels(self):
        classes = {}
        for commit in db.read(self.commits_path):
            if self.limit and len(classes) >= self.limit:
                break
            classes[commit['node']]=1 if commit['failures'] else 0

        logger.info(
            "%d commits failed", sum(1 for label in classes.values() if label == 1)
        )
        logger.info(
            "%d commits did not fail",
            sum(1 for label in classes.values() if label == 0),
        )

        return [0, 1]

    def get_feature_names(self):
        return self.extraction_pipeline.named_steps["union"].get_feature_names_out()
