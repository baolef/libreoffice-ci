# Created by Baole Fang at 6/13/23
import gzip
import io
import pickle
from contextlib import contextmanager

import orjson
import zstandard
from dataset import experiences

class Store:
    def __init__(self, fh):
        self.fh = fh


class JSONStore(Store):
    def write(self, elems):
        for elem in elems:
            self.fh.write(orjson.dumps(elem) + b"\n")

    def read(self):
        for line in io.TextIOWrapper(self.fh, encoding="utf-8"):
            yield orjson.loads(line)


class PickleStore(Store):
    def write(self, elems):
        for elem in elems:
            self.fh.write(pickle.dumps(elem))

    def read(self):
        try:
            while True:
                yield pickle.load(self.fh)
        except EOFError:
            pass


COMPRESSION_FORMATS = ["gz", "zstd"]
SERIALIZATION_FORMATS = {"json": JSONStore, "pickle": PickleStore}


@contextmanager
def db_open(path: str, mode):
    parts = path.split('.')
    assert len(parts) > 1, "Extension needed to figure out serialization format"
    if len(parts) == 2:
        db_format = parts[-1]
        compression = None
    else:
        db_format = parts[-2]
        compression = parts[-1]

    assert compression is None or compression in COMPRESSION_FORMATS
    assert db_format in SERIALIZATION_FORMATS

    store_constructor = SERIALIZATION_FORMATS[db_format]

    if compression == "gz":
        with gzip.GzipFile(path, mode) as f:
            yield store_constructor(f)
    elif compression == "zstd":
        if "w" in mode or "a" in mode:
            cctx = zstandard.ZstdCompressor()
            with open(path, mode) as f:
                with cctx.stream_writer(f) as writer:
                    yield store_constructor(writer)
        else:
            dctx = zstandard.ZstdDecompressor()
            with open(path, mode) as f:
                with dctx.stream_reader(f) as reader:
                    yield store_constructor(reader)
    else:
        with open(path, mode) as f:
            yield store_constructor(f)


def write(obj, path):
    with db_open(path, 'wb') as db:
        db.write(obj)


def read(path):
    with db_open(path, "rb") as db:
        for elem in db.read():
            yield elem


def append(obj, path):
    with db_open(path, "ab") as db:
        db.write(obj)
