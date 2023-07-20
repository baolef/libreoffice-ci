#!/bin/bash
source ~/miniconda3/etc/profile.d/conda.sh
conda activate libreoffice-ci

cd ~/libreoffice-ci || exit
export PYTHONPATH=${PYTHONPATH}:${pwd}
export PATH=~/.cargo/bin:${PATH}
python -W "ignore" test.py testlabelselect --confidence_threshold -1 --path $1 --csv $1
