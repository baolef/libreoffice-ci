# Created by Baole Fang at 6/17/23
import errno
import json
import os
import subprocess
from collections import deque
from dataset import db
import numpy as np
import scipy
from sklearn.base import BaseEstimator, TransformerMixin


def cast_type(container, from_types, to_types):
    if isinstance(container, dict):
        # cast all contents of dictionary
        return {cast_type(k, from_types, to_types): cast_type(v, from_types, to_types) for k, v in container.items()}
    elif isinstance(container, list):
        # cast all contents of list
        return [cast_type(item, from_types, to_types) for item in container]
    else:
        for f, t in zip(from_types, to_types):
            # if item is of a type mentioned in from_types,
            # cast it to the corresponding to_types class
            if isinstance(container, f):
                return t(container)
        # None of the above, return without casting
        return container


class CustomJsonEncoder(json.JSONEncoder):
    """A custom Json Encoder to support Numpy types."""

    def default(self, obj):
        try:
            return np.asscalar(obj)
        except (ValueError, IndexError, AttributeError, TypeError):
            pass

        return super().default(obj)


def zstd_compress(path: str) -> None:
    if not os.path.exists(path):
        raise FileNotFoundError(errno.ENOENT, os.strerror(errno.ENOENT), path)

    subprocess.run(["zstd", "-f", path], check=True)


def split_tuple_generator(generator):
    second_filled = False
    q = deque()

    def first_iter():
        nonlocal second_filled

        for first, second in generator():
            yield first
            if not second_filled:
                q.append(second)

        second_filled = True

    return first_iter, q


def to_array(val):
    if isinstance(val, scipy.sparse.csr_matrix):
        return val.toarray()

    return val


def get_physical_cpu_count() -> int:
    return os.cpu_count() // 2


def read_commits(path='data/commits.json'):
    return db.read(path)


class Converter(BaseEstimator, TransformerMixin):
    def __init__(self, dtype=np.float32):
        self.dtype = dtype

    def fit(self, x, y=None):
        return self

    def transform(self, data):
        return data.astype(self.dtype)
