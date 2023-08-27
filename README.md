# libreoffice-ci

GSoC Project: LibreOffice CI Test Selection with Machine Learning

The goal of this project is to select unit tests based on `(patch,test)` pair. Three models (`testlabelselect`, `testfailure`, `testoverall`) are trained to predict unit tests results given a patch on different levels.

The work is based on Mozilla's [bugbug](https://github.com/mozilla/bugbug) and [rust-code-analysis](https://mozilla.github.io/rust-code-analysis/).

## Models

`testlabelselect` model predicts the failing probability of each unit test given the patch.

|               | Fail (Predicted) | Pass (Predicted) |
|---------------|------------------|------------------|
| Fail (Actual) | 3860             | 203              |
| Pass (Actual) | 191593           | 1109768          |

`testfailure` model predicts the overall failing probability of a patch based on patch features only.

|               | Fail (Predicted)  | Pass (Predicted) |
|---------------|-------------------|------------------|
| Fail (Actual) | 614               | 527              |
| Pass (Actual) | 2155              | 4863             |

`testoverall` model improves upon `testfailure` by using `testlabelselect` predictions to predict whether a patch will fail any unit test.

|               | Fail (Predicted) | Pass (Predicted) |
|---------------|------------------|------------------|
| Fail (Actual) | 810              | 331              |
| Pass (Actual) | 2413             | 4605             |

A smart inference is built based on `testlabelselect` and `testoverall` predictions. By setting a threshold for the number of failed unit tests, 91% of failures can be captured, while reducing computation by 57%.

|               | Fail (Predicted) | Pass (Predicted) |
|---------------|------------------|------------------|
| Fail (Actual) | 10617            | 1054             |
| Pass (Actual) | 30103            | 39815            |

Currently, the smart inference is integrated into [Jenkins](https://ci.libreoffice.org/job/gerrit_master_ml/) to save computation. If a patch is likely to fail any unit test, the sequential [fast track](https://ci.libreoffice.org/job/gerrit_master_seq/) will be run because it is assumed that the patch will fail some unit tests and there is no need to run everything. If it is likely to pass, the [normal track]((https://ci.libreoffice.org/job/gerrit_master/)) will be run to ensure code correctness.

`testlabelselect` is not directly used to select unit tests because it is not able to capture all failures, about 5% failures will escape and it could cause severe problem.

## Environment

Install `build-essential` and `zstd`:
```shell
sudo apt install build-essential
sudo apt install zstd
```

Clone [libreoffice](https://www.libreoffice.org/):
```shell
git clone https://gerrit.libreoffice.org/core libreoffice
```

Install [rust](https://www.rust-lang.org/):
```shell
curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh
export PATH="~/.cargo/bin:$PATH"
```

Install [rust-code-analysis](https://mozilla.github.io/rust-code-analysis/):
```shell
cargo install rust-code-analysis-cli rust-code-analysis-web
```

Install [conda](https://docs.conda.io/en/latest/miniconda.html):
```shell
wget https://repo.anaconda.com/miniconda/Miniconda3-latest-Linux-x86_64.sh
bash Miniconda3-latest-Linux-x86_64.sh
```

Clone [libreoffice-ci](https://github.com/baolef/libreoffice-ci):
```shell
git clone https://github.com/baolef/libreoffice-ci.git
cd libreoffice-ci
```

Install [Python](https://www.python.org/) dependencies:
```shell
conda env create -f environment.yml
conda activate libreoffice-ci
```

## Data

To extract features for past gerrit pushes, extract `data/jenkinsfullstats.csv` from `data/jenkinsfullstats.csv.xz` first, and then run:
```shell
python dataset/mining.py --path ../libreoffice
```

To extract all unit tests, extract pushes features `data/commits.json` first, and then run:
```shell
python dataset/mapping.py
```

To extract features for unit tests, extract pushes features `data/commits.json` and `data/tests.json` first, and then run:
```shell
python dataset/test_history.py --path data/commits.json
```

To convert one database format (eg. `data/commits.json`) into another (eg. `data/commits.pickle.zstd`):
```shell
python dataset/convert.py data/commits.json data/commits.pickle.zstd
```

## Training

To train a model (eg. `testlabelselect`, `testoverall`) after extracting necessary data:
```shell
python train.py testlabelselect
python train.py testoverall
```

Training a model with full dataset may be time and memory consuming, `--limit` argument can be used to train a subset:
```shell
python train.py testlabelselect --limit 16384
```

Detailed training scripts are available for ungrouped data `scripts/train.sh` and grouped data `scripts/train_group.sh`.

## Inference

To inference a model (eg. `testlabelselect`) after training necessary models (eg.`testlabelselect`, `testoverall`) for a commit hash (eg. `a772976f047882918d5386a3ef9226c4aa2aa118`):
```shell
python test.py testlabelselect --revision a772976f047882918d5386a3ef9226c4aa2aa118
```

If a commit hash is not specified, it will perform inference on the last commit.

Detailed inference script is available in `scripts/test.sh`.
