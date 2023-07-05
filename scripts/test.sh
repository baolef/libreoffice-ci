source ~/miniconda3/etc/profile.d/conda.sh
conda activate libreoffice-ci

cd ~/libreoffice-ci || exit
export PYTHONPATH=${PYTHONPATH}:${pwd}
python test.py testlabelselect --path $1
