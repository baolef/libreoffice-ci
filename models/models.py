# Created by Baole Fang at 6/17/23

from .base import Model
from typing import Type

models = {}


def register(name):
    def decorator(cls):
        models[name] = cls
        return cls

    return decorator


def get_model_class(name) -> Type[Model]:
    if name not in models:
        err_msg = f"Invalid name {name}, not in {list(models.keys())}"
        raise ValueError(err_msg)

    model = models[name]
    return model
