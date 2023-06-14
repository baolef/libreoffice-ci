# Created by Baole Fang at 6/13/23
import gzip
import logging
import pickle


logger = logging.getLogger(__name__)


def write_file(obj, filename: str):
    compressed = gzip.compress(pickle.dumps(obj))
    with open(filename, 'wb') as f:
        f.write(compressed)


def read_file(filename: str):
    with gzip.open(filename) as f:
        content = f.read()
        obj = pickle.loads(content)
    return obj
