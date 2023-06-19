# Created by Baole Fang at 6/17/23
import errno
import json
import os
import subprocess
from collections import deque
from dataset import db
import numpy as np
import scipy


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
    return os.cpu_count()//2


def read_commits(path='data/commits.json'):
    return db.read(path)
