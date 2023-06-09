# -*- coding: utf-8 -*-

import argparse
import inspect
import json
import os
import sys
from logging import INFO, basicConfig, getLogger

import numpy as np

import utils
from models import get_model_class, models
from utils import CustomJsonEncoder, zstd_compress

MODELS_WITH_TYPE = ("component",)

basicConfig(level=INFO)
logger = getLogger(__name__)


class Trainer(object):
    def go(self, args):
        # Download datasets that were built by bugbug_data.
        os.makedirs("data", exist_ok=True)

        if args.classifier != "default":
            assert (
                    args.model in MODELS_WITH_TYPE
            ), f"{args.classifier} is not a valid classifier type for {args.model}"

            model_name = f"{args.model}_{args.classifier}"
        else:
            model_name = args.model

        model_class = get_model_class(model_name)
        parameter_names = set(inspect.signature(model_class.__init__).parameters)
        parameters = {
            key: value for key, value in vars(args).items() if key in parameter_names
        }
        model_obj = model_class(**parameters)

        logger.info("Training *%s* model", model_name)
        metrics = model_obj.train(limit=args.limit)

        # Save the metrics as a file that can be uploaded as an artifact.
        metric_file_path = f"{model_name}_metrics.json"
        print(metrics)
        with open(metric_file_path, "w") as metric_file:
            json.dump(utils.cast_type(metrics, [np.int64, np.float64], [int, float]), metric_file,
                      cls=CustomJsonEncoder, indent=2)

        logger.info("Training done")

        model_file_name = f"{model_name}model"
        print(model_file_name)
        assert os.path.exists(model_file_name)
        zstd_compress(model_file_name)

        logger.info("Model compressed")

        if model_obj.store_dataset:
            assert os.path.exists(f"{model_file_name}_data_X")
            zstd_compress(f"{model_file_name}_data_X")
            assert os.path.exists(f"{model_file_name}_data_y")
            zstd_compress(f"{model_file_name}_data_y")


def parse_args(args):
    description = "Train the models"
    main_parser = argparse.ArgumentParser(description=description)

    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument(
        "--path",
        type=str,
        default='data/commits.json',
        help="Only train on a subset of the data, used mainly for integrations tests",
    )
    parser.add_argument(
        "--limit",
        type=int,
        help="Only train on a subset of the data, used mainly for integrations tests",
    )
    parser.add_argument(
        "--no-download",
        action="store_false",
        dest="download_db",
        help="Do not download databases, uses whatever is on disk",
    )
    parser.add_argument(
        "--download-eval",
        action="store_true",
        dest="download_eval",
        help="Download databases and database support files required at runtime (e.g. if the model performs custom evaluations)",
    )
    parser.add_argument(
        "--lemmatization",
        help="Perform lemmatization (using spaCy)",
        action="store_true",
    )
    parser.add_argument(
        "--classifier",
        help="Type of the classifier. Only used for component classification.",
        choices=["default", "nn"],
        default="default",
    )

    subparsers = main_parser.add_subparsers(title="model", dest="model", required=True)

    for model_name in models:
        subparser = subparsers.add_parser(
            model_name, parents=[parser], help=f"Train {model_name} model"
        )

        try:
            model_class_init = get_model_class(model_name).__init__
        except ImportError:
            continue

        for parameter in inspect.signature(model_class_init).parameters.values():
            if parameter.name == "self":
                continue

            if parameter.name == "lemmatization":
                continue

            if parameter.name == "path":
                continue

            parameter_type = parameter.annotation
            if parameter_type == inspect._empty:
                parameter_type = type(parameter.default)
            assert parameter_type is not None

            if parameter_type == bool:
                subparser.add_argument(
                    f"--{parameter.name}"
                    if parameter.default is False
                    else f"--no-{parameter.name}",
                    action="store_true"
                    if parameter.default is False
                    else "store_false",
                    dest=parameter.name,
                )
            else:
                subparser.add_argument(
                    f"--{parameter.name}",
                    default=parameter.default,
                    dest=parameter.name,
                    type=int,
                )

    return main_parser.parse_args(args)


def main():
    args = parse_args(sys.argv[1:])

    retriever = Trainer()
    retriever.go(args)


if __name__ == "__main__":
    main()
