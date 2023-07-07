#!/bin/bash
source ~/miniconda3/etc/profile.d/conda.sh
conda activate libreoffice-ci

cd ~/libreoffice-ci/data || exit
xz -kd jenkinsfullstats.csv.xz
cd ~/libreoffice-ci || exit
export PYTHONPATH=${PYTHONPATH}:${pwd}
export PATH=~/.cargo/bin:${PATH}
python dataset/mining.py --path $1
python dataset/test_history.py
python train.py testlabelselect
python train.py testfailure
