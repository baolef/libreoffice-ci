# libreoffice-ci

GSoC Project: LibreOffice CI Test Selection with Machine Learning

The work is based on Mozilla's [bugbug](https://github.com/mozilla/bugbug) and [rust-code-analysis](https://mozilla.github.io/rust-code-analysis/).

## Environment

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

To extract features for unit tests, extract pushes features `data/commits.json` first, and then run:
```shell
python dataset/test_history.py --path data/commits.json
```

To convert one database format (eg. `data/commits.json`) into another (eg. `data/commits.pickle.zstd`):
```shell
python dataset/convert.py data/commits.json data/commits.pickle.zstd
```

## Model

To train a model (eg. `testlabelselect`) after extracting necessary data:
```shell
python train.py testlabelselect
```

Training a model with full dataset may be time and memory consuming, `--limit` argument can be used to train a subset:
```shell
python train.py testlabelselect --limit 16384
```