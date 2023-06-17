# Created by Baole Fang at 6/17/23
import errno
import json
import os
import subprocess

import numpy as np


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