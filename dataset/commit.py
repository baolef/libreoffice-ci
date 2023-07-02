# Created by Baole Fang at 6/3/23
import copy
import os
import logging

import pandas as pd
from git import Commit
from typing import *
from dataset import rust_code_analysis_server

METRIC_NAMES = [
    "cyclomatic",
    "halstead_N1",
    "halstead_n1",
    "halstead_N2",
    "halstead_n2",
    "halstead_length",
    "halstead_estimated_program_length",
    "halstead_purity_ratio",
    "halstead_vocabulary",
    "halstead_volume",
    "halstead_difficulty",
    "halstead_level",
    "halstead_effort",
    "halstead_time",
    "halstead_bugs",
    "functions",
    "closures",
    "sloc",
    "ploc",
    "lloc",
    "cloc",
    "blank",
    "nargs",
    "nexits",
    "cognitive",
    "mi_original",
    "mi_sei",
    "mi_visual_studio",
]

SOURCE_CODE_TYPES_TO_EXT = {
    "Assembly": [".asm", ".S"],
    "Javascript": [".js", ".jsm", ".sjs", ".mjs", ".jsx"],
    "C/C++": [".c", ".cpp", ".cc", ".cxx", ".h", ".hh", ".hpp", ".hxx"],
    "Objective-C/C++": [".mm", ".m"],
    "Java": [".java"],
    "Python": [".py"],
    "Rust": [".rs"],
    "Kotlin": [".kt"],
    "HTML/XHTML/XUL": [".html", ".htm", ".xhtml", ".xht", ".xul"],
    "IDL/IPDL/WebIDL": [".idl", ".ipdl", ".webidl"],
}

OTHER_TYPES_TO_EXT = {
    "YAML": [".yaml", ".yml"],
    "Image": [
        ".png",
        ".jpg",
        ".jpeg",
        ".gif",
        ".bmp",
        ".ico",
        ".icns",
        ".psd",
        ".tiff",
        ".ttf",
        ".bcmap",
        ".webp",
    ],
    "Archive": [".zip", ".gz", ".bz2", ".tar", ".xpi", ".jar"],
    "Video": [".mp4", ".webm", ".ogv", ".avi", ".mov", ".m4s", ".mgif"],
    "Audio": [".mp3", ".ogg", ".wav", ".flac", ".opus"],
    "Executable": [".exe", ".dll", ".so", ".class"],
    "Document": [".pdf", ".doc", ".otf"],
    "Documentation": [".rst", ".md"],
    "Build System File": [".build", ".mk", ".in"],
}

TYPES_TO_EXT = {**SOURCE_CODE_TYPES_TO_EXT, **OTHER_TYPES_TO_EXT}

EXT_TO_TYPES = {ext: typ for typ, exts in TYPES_TO_EXT.items() for ext in exts}

logger = logging.getLogger(__name__)


def get_type(path: str) -> str:
    if "qa" in path.split('/'):
        return 'Test'
    ext = os.path.splitext(path)[1].lower()
    return EXT_TO_TYPES.get(ext, ext)


def get_total_metrics_dict() -> dict:
    return {f"{metric}_total": 0 for metric in METRIC_NAMES}


def get_metrics_dict() -> dict:
    metrics = get_total_metrics_dict()
    for metric in METRIC_NAMES:
        metrics.update(
            {
                f"{metric}_avg": 0.0,
                f"{metric}_max": 0,
                f"{metric}_min": float('inf'),
            }
        )
    return metrics


def get_directories(files):
    if isinstance(files, str):
        files = [files]

    directories = set()
    for path in files:
        path_dirs = (
            os.path.dirname(path).split("/", 2)[:2] if os.path.dirname(path) else []
        )
        if path_dirs:
            directories.update([path_dirs[0], "/".join(path_dirs)])
    return list(directories)


class AnalysisException(Exception):
    """Raised when rust-code-analysis failed to analyze a file."""
    pass


def get_summary_metrics(obj, metrics_space):
    if metrics_space["kind"] in {"unit", "function"} and metrics_space["name"] == "":
        raise AnalysisException("Analysis error")

    if metrics_space["kind"] == "function":
        metrics = metrics_space["metrics"]

        obj["cyclomatic_max"] = max(obj["cyclomatic_max"], metrics["cyclomatic"]["sum"])
        obj["halstead_n2_max"] = max(obj["halstead_n2_max"], metrics["halstead"]["n2"])
        obj["halstead_N2_max"] = max(obj["halstead_N2_max"], metrics["halstead"]["N2"])
        obj["halstead_n1_max"] = max(obj["halstead_n1_max"], metrics["halstead"]["n1"])
        obj["halstead_N1_max"] = max(obj["halstead_N1_max"], metrics["halstead"]["N1"])
        if metrics["halstead"]["length"] is not None:
            obj["halstead_length_max"] = max(
                obj["halstead_length_max"], metrics["halstead"]["length"]
            )
        if metrics["halstead"]["estimated_program_length"] is not None:
            obj["halstead_estimated_program_length_max"] = max(
                obj["halstead_estimated_program_length_max"],
                metrics["halstead"]["estimated_program_length"],
            )
        if metrics["halstead"]["purity_ratio"] is not None:
            obj["halstead_purity_ratio_max"] = max(
                obj["halstead_purity_ratio_max"], metrics["halstead"]["purity_ratio"]
            )
        if metrics["halstead"]["vocabulary"] is not None:
            obj["halstead_vocabulary_max"] = max(
                obj["halstead_vocabulary_max"], metrics["halstead"]["vocabulary"]
            )
        if metrics["halstead"]["volume"] is not None:
            obj["halstead_volume_max"] = max(
                obj["halstead_volume_max"], metrics["halstead"]["volume"]
            )
        if metrics["halstead"]["difficulty"] is not None:
            obj["halstead_difficulty_max"] = max(
                obj["halstead_difficulty_max"], metrics["halstead"]["difficulty"]
            )
        if metrics["halstead"]["level"] is not None:
            obj["halstead_level_max"] = max(
                obj["halstead_level_max"], metrics["halstead"]["level"]
            )
        if metrics["halstead"]["effort"] is not None:
            obj["halstead_effort_max"] = max(
                obj["halstead_effort_max"], metrics["halstead"]["effort"]
            )
        if metrics["halstead"]["time"] is not None:
            obj["halstead_time_max"] = max(
                obj["halstead_time_max"], metrics["halstead"]["time"]
            )
        if metrics["halstead"]["bugs"] is not None:
            obj["halstead_bugs_max"] = max(
                obj["halstead_bugs_max"], metrics["halstead"]["bugs"]
            )
        obj["functions_max"] = max(obj["functions_max"], metrics["nom"]["functions"])
        obj["closures_max"] = max(obj["closures_max"], metrics["nom"]["closures"])
        obj["sloc_max"] = max(obj["sloc_max"], metrics["loc"]["sloc"])
        obj["ploc_max"] = max(obj["ploc_max"], metrics["loc"]["ploc"])
        obj["lloc_max"] = max(obj["lloc_max"], metrics["loc"]["lloc"])
        obj["cloc_max"] = max(obj["cloc_max"], metrics["loc"]["cloc"])
        obj["blank_max"] = max(obj["blank_max"], metrics["loc"]["blank"])
        obj["nargs_max"] = max(obj["nargs_max"], metrics["nargs"]["total"])
        obj["nexits_max"] = max(obj["nexits_max"], metrics["nexits"]["sum"])
        obj["cognitive_max"] = max(obj["cognitive_max"], metrics["cognitive"]["sum"])

        if metrics["mi"]["mi_original"] is not None:
            obj["mi_original_max"] = max(
                obj["mi_original_max"], metrics["mi"]["mi_original"]
            )
        if metrics["mi"]["mi_sei"] is not None:
            obj["mi_sei_max"] = max(obj["mi_sei_max"], metrics["mi"]["mi_sei"])
        if metrics["mi"]["mi_visual_studio"] is not None:
            obj["mi_visual_studio_max"] = max(
                obj["mi_visual_studio_max"], metrics["mi"]["mi_visual_studio"]
            )

        obj["cyclomatic_min"] = min(obj["cyclomatic_min"], metrics["cyclomatic"]["sum"])
        obj["halstead_n2_min"] = min(obj["halstead_n2_min"], metrics["halstead"]["n2"])
        obj["halstead_N2_min"] = min(obj["halstead_N2_min"], metrics["halstead"]["N2"])
        obj["halstead_n1_min"] = min(obj["halstead_n1_min"], metrics["halstead"]["n1"])
        obj["halstead_N1_min"] = min(obj["halstead_N1_min"], metrics["halstead"]["N1"])

        if metrics["halstead"]["length"] is not None:
            obj["halstead_length_min"] = min(
                obj["halstead_length_min"], metrics["halstead"]["length"]
            )
        if metrics["halstead"]["estimated_program_length"] is not None:
            obj["halstead_estimated_program_length_min"] = min(
                obj["halstead_estimated_program_length_min"],
                metrics["halstead"]["estimated_program_length"],
            )
        if metrics["halstead"]["purity_ratio"] is not None:
            obj["halstead_purity_ratio_min"] = min(
                obj["halstead_purity_ratio_min"], metrics["halstead"]["purity_ratio"]
            )
        if metrics["halstead"]["vocabulary"] is not None:
            obj["halstead_vocabulary_min"] = min(
                obj["halstead_vocabulary_min"], metrics["halstead"]["vocabulary"]
            )
        if metrics["halstead"]["volume"] is not None:
            obj["halstead_volume_min"] = min(
                obj["halstead_volume_min"], metrics["halstead"]["volume"]
            )
        if metrics["halstead"]["difficulty"] is not None:
            obj["halstead_difficulty_min"] = min(
                obj["halstead_difficulty_min"], metrics["halstead"]["difficulty"]
            )
        if metrics["halstead"]["level"] is not None:
            obj["halstead_level_min"] = min(
                obj["halstead_level_min"], metrics["halstead"]["level"]
            )
        if metrics["halstead"]["effort"] is not None:
            obj["halstead_effort_min"] = min(
                obj["halstead_effort_min"], metrics["halstead"]["effort"]
            )
        if metrics["halstead"]["time"] is not None:
            obj["halstead_time_min"] = min(
                obj["halstead_time_min"], metrics["halstead"]["time"]
            )
        if metrics["halstead"]["bugs"] is not None:
            obj["halstead_bugs_min"] = min(
                obj["halstead_bugs_min"], metrics["halstead"]["bugs"]
            )
        obj["functions_min"] = min(obj["functions_min"], metrics["nom"]["functions"])
        obj["closures_min"] = min(obj["closures_min"], metrics["nom"]["closures"])
        obj["sloc_min"] = min(obj["sloc_min"], metrics["loc"]["sloc"])
        obj["ploc_min"] = min(obj["ploc_min"], metrics["loc"]["ploc"])
        obj["lloc_min"] = min(obj["lloc_min"], metrics["loc"]["lloc"])
        obj["cloc_min"] = min(obj["cloc_min"], metrics["loc"]["cloc"])
        obj["blank_min"] = min(obj["blank_min"], metrics["loc"]["blank"])
        obj["nargs_min"] = min(obj["nargs_min"], metrics["nargs"]["total"])
        obj["nexits_min"] = min(obj["nexits_min"], metrics["nexits"]["sum"])
        obj["cognitive_min"] = min(obj["cognitive_min"], metrics["cognitive"]["sum"])

        if metrics["mi"]["mi_original"] is not None:
            obj["mi_original_min"] = min(
                obj["mi_original_min"], metrics["mi"]["mi_original"]
            )
        if metrics["mi"]["mi_sei"] is not None:
            obj["mi_sei_min"] = min(obj["mi_sei_min"], metrics["mi"]["mi_sei"])
        if metrics["mi"]["mi_visual_studio"] is not None:
            obj["mi_visual_studio_min"] = min(
                obj["mi_visual_studio_min"], metrics["mi"]["mi_visual_studio"]
            )

    for space in metrics_space["spaces"]:
        get_summary_metrics(obj, space)

    return obj


def get_space_metrics(
        obj: dict, metrics_space: dict, calc_summaries: bool = True
) -> None:
    if metrics_space["kind"] in {"unit", "function"} and metrics_space["name"] == "":
        raise AnalysisException("Analysis error")

    metrics = metrics_space["metrics"]
    obj["cyclomatic_total"] += metrics["cyclomatic"]["sum"]
    obj["halstead_n2_total"] += metrics["halstead"]["n2"]
    obj["halstead_N2_total"] += metrics["halstead"]["N2"]
    obj["halstead_n1_total"] += metrics["halstead"]["n1"]
    obj["halstead_N1_total"] += metrics["halstead"]["N1"]
    if metrics["halstead"]["length"] is not None:
        obj["halstead_length_total"] += metrics["halstead"]["length"]
    if metrics["halstead"]["estimated_program_length"] is not None:
        obj["halstead_estimated_program_length_total"] += metrics["halstead"][
            "estimated_program_length"
        ]
    if metrics["halstead"]["purity_ratio"] is not None:
        obj["halstead_purity_ratio_total"] += metrics["halstead"]["purity_ratio"]
    if metrics["halstead"]["vocabulary"] is not None:
        obj["halstead_vocabulary_total"] += metrics["halstead"]["vocabulary"]
    if metrics["halstead"]["volume"] is not None:
        obj["halstead_volume_total"] += metrics["halstead"]["volume"]
    if metrics["halstead"]["difficulty"] is not None:
        obj["halstead_difficulty_total"] += metrics["halstead"]["difficulty"]
    if metrics["halstead"]["level"] is not None:
        obj["halstead_level_total"] += metrics["halstead"]["level"]
    if metrics["halstead"]["effort"] is not None:
        obj["halstead_effort_total"] += metrics["halstead"]["effort"]
    if metrics["halstead"]["time"] is not None:
        obj["halstead_time_total"] += metrics["halstead"]["time"]
    if metrics["halstead"]["bugs"] is not None:
        obj["halstead_bugs_total"] += metrics["halstead"]["bugs"]
    obj["functions_total"] += metrics["nom"]["functions"]
    obj["closures_total"] += metrics["nom"]["closures"]
    obj["sloc_total"] += metrics["loc"]["sloc"]
    obj["ploc_total"] += metrics["loc"]["ploc"]
    obj["lloc_total"] += metrics["loc"]["lloc"]
    obj["cloc_total"] += metrics["loc"]["cloc"]
    obj["blank_total"] += metrics["loc"]["blank"]
    obj["nargs_total"] += metrics["nargs"]["total"]
    obj["nexits_total"] += metrics["nexits"]["sum"]
    obj["cognitive_total"] += metrics["cognitive"]["sum"]

    if metrics["mi"]["mi_original"] is not None:
        obj["mi_original_total"] += metrics["mi"]["mi_original"]
    if metrics["mi"]["mi_sei"] is not None:
        obj["mi_sei_total"] += metrics["mi"]["mi_sei"]
    if metrics["mi"]["mi_visual_studio"] is not None:
        obj["mi_visual_studio_total"] += metrics["mi"]["mi_visual_studio"]

    if calc_summaries:
        for space in metrics_space["spaces"]:
            get_summary_metrics(obj, space)


def get_functions_from_metrics(metrics_space):
    functions = []

    if (
            metrics_space["kind"] == "function"
    ):
        functions.append(metrics_space)

    for space in metrics_space["spaces"]:
        functions += get_functions_from_metrics(space)

    return functions


def get_touched_functions(
        metrics_space: dict, deleted_lines: Iterable[int], added_lines: Iterable[int]
) -> list[dict]:
    touched_functions_indexes = set()

    functions = get_functions_from_metrics(metrics_space)

    def get_touched(functions, lines):
        last_f = 0
        for line in lines:
            for function in functions[last_f:]:
                # Skip functions which we already passed.
                if function["end_line"] < line:
                    last_f += 1

                # If the line belongs to this function, add the function to the set of touched functions.
                elif function["start_line"] <= line:
                    touched_functions_indexes.add(functions.index(function))
                    last_f += 1

    # Get functions touched by added lines.
    get_touched(functions, added_lines)

    # Map functions to their positions before the patch.
    prev_functions = copy.deepcopy(functions)

    for line in added_lines:
        for func in prev_functions:
            if line < func["start_line"]:
                func["start_line"] -= 1

            if line < func["end_line"]:
                func["end_line"] -= 1

    for line in deleted_lines:
        for func in prev_functions:
            if line <= func["start_line"]:
                func["start_line"] += 1

            if line < func["end_line"]:
                func["end_line"] += 1

    # Get functions touched by removed lines.
    get_touched(prev_functions, deleted_lines)

    # Return touched functions, with their new positions.
    return [functions[i] for i in touched_functions_indexes]


def calculate_lines(commit, file):
    diff = commit.parents[0].diff(commit, paths=[file], create_patch=True)[0]
    if diff.new_file:
        return [], [], True
    patch = diff.diff.decode('utf-8').splitlines()
    delete_lines = []
    add_lines = []
    delete = None
    add = None
    for line in patch:
        if line.startswith("@@"):
            l = line.split()
            delete = abs(int(l[1].split(',')[0]))
            add = abs(int(l[2].split(',')[0]))
        elif line.startswith('+'):
            add_lines.append(add)
            add += 1
        elif line.startswith('-'):
            delete_lines.append(delete)
            delete += 1
        else:
            add += 1
            delete += 1
    return delete_lines, add_lines, False


def get_component_dict(path='data/bz_data.csv'):
    result={}
    data=pd.read_csv(path)
    for bug_id,component in zip(data['id'],data['component']):
        result[bug_id]=component
    return result

COMPONENT=get_component_dict()

class Commit:
    def __init__(
            self,
            commit: Commit,
            failures=[]
    ) -> None:
        self.set_files(list(commit.stats.files.keys()), {})
        self.node = commit.hexsha
        self.author = commit.author.name
        self.bug_id = None
        for word in commit.summary.split(' '):
            if word.startswith("tdf#"):
                i = 4
                while i < len(word) and word[i].isdigit():
                    i += 1
                try:
                    self.bug_id = int(word[4:i])
                except:
                    self.bug_id = None
        self.desc = commit.summary
        self.pushdate = commit.committed_datetime.astimezone()
        self.author_email = commit.author.email
        self.reviewers = [commit.committer.name]
        self.ignored = False
        self.source_code_added = 0
        self.other_added = 0
        self.test_added = 0
        self.source_code_deleted = 0
        self.other_deleted = 0
        self.test_deleted = 0
        self.metrics = get_metrics_dict()
        self.metrics_diff = get_total_metrics_dict()
        self.types: Set[str] = set()
        self.functions: dict[str, list[dict]] = {}
        self.failures = failures

    def __eq__(self, other):
        assert isinstance(other, Commit)
        return self.node == other.node

    def __hash__(self):
        return hash(self.node)

    def __repr__(self):
        return str(self.__dict__)

    def set_files(self, files, file_copies):
        self.files = files
        self.file_copies = file_copies
        # self.components = list(
        #     set(
        #         path_to_component[path.encode("utf-8")].tobytes().decode("utf-8")
        #         for path in files
        #         if path.encode("utf-8") in path_to_component
        #     )
        # )
        self.directories = get_directories(files)
        return self

    def set_experience(
            self, exp_type, commit_type, timespan, exp_sum, exp_max, exp_min
    ):
        exp_str = f"touched_prev_{timespan}_{exp_type}_"
        if commit_type:
            exp_str += f"{commit_type}_"
        setattr(self, f"{exp_str}sum", exp_sum)
        if exp_type != "author":
            setattr(self, f"{exp_str}max", exp_max)
            setattr(self, f"{exp_str}min", exp_min)

    def set_commit_metrics(
            self: Commit,
            path: str,
            deleted_lines: list[int],
            added_lines: list[int],
            before_metrics: dict,
            after_metrics: dict,
    ) -> None:
        try:
            get_space_metrics(self.metrics, after_metrics["spaces"])
        except AnalysisException:
            logger.debug(f"rust-code-analysis error on commit {self.node}, path {path}")

        before_metrics_dict = get_total_metrics_dict()
        try:
            if before_metrics.get("spaces"):
                get_space_metrics(
                    before_metrics_dict, before_metrics["spaces"], calc_summaries=False
                )
        except AnalysisException:
            logger.debug(f"rust-code-analysis error on commit {self.node}, path {path}")

        self.metrics_diff = {
            f"{metric}_total": self.metrics[f"{metric}_total"]
                               - before_metrics_dict[f"{metric}_total"]
            for metric in METRIC_NAMES
        }

        touched_functions = get_touched_functions(
            after_metrics["spaces"],
            deleted_lines,
            added_lines,
        )
        if len(touched_functions) == 0:
            return

        self.functions[path] = []

        for func in touched_functions:
            metrics_dict = get_total_metrics_dict()

            try:
                get_space_metrics(metrics_dict, func, calc_summaries=False)
            except AnalysisException:
                logger.debug(
                    f"rust-code-analysis error on commit {self.node}, path {path}, function {func['name']}"
                )

            self.functions[path].append(
                {
                    "name": func["name"],
                    "start": func["start_line"],
                    "end": func["end_line"],
                    "metrics": metrics_dict,
                }
            )

    def to_dict(self) -> dict:
        d = self.__dict__
        for f in ["file_copies"]:
            del d[f]
        d["types"] = list(d["types"])
        d["pushdate"] = str(d["pushdate"])
        return dict(d)

    def transform(self, commit, code_analysis_server: rust_code_analysis_server.RustCodeAnalysisServer):
        source_code_sizes = []
        other_sizes = []
        test_sizes = []
        metrics_file_count = 0

        for file, count in commit.stats.files.items():
            diff = commit.parents[0].diff(commit, paths=[file], create_patch=True)[0]
            after = None
            size = None
            if not diff.deleted_file:
                after = (commit.tree / file).data_stream.read()
                size = after.count(b'\n')

            type_ = get_type(file)
            self.types.add(type_)
            if type_ == "Test":
                self.test_added += count['insertions']
                self.test_deleted += count['deletions']
                if size:
                    test_sizes.append(size)
            elif type_ in SOURCE_CODE_TYPES_TO_EXT:
                self.source_code_added += count['insertions']
                self.source_code_deleted += count['deletions']
                if size:
                    source_code_sizes.append(size)

                after_metrics = code_analysis_server.metrics(file, after, unit=False)
                if after_metrics.get("spaces"):
                    metrics_file_count += 1
                    deleted_lines, added_lines, new_file = calculate_lines(commit, file)
                    before_metrics = {}
                    if not new_file:
                        before = (commit.parents[0].tree / file).data_stream.read()
                        before_metrics = code_analysis_server.metrics(file, before, unit=False)

                    self.set_commit_metrics(
                        file,
                        deleted_lines,
                        added_lines,
                        before_metrics,
                        after_metrics,
                    )

            else:
                self.other_added += count['insertions']
                self.other_deleted += count['deletions']
                if size:
                    other_sizes.append(size)

        self.seniority_author = 0.0
        self.total_source_code_file_size = sum(source_code_sizes)
        self.average_source_code_file_size = self.total_source_code_file_size / len(
            source_code_sizes) if source_code_sizes else 0
        self.maximum_source_code_file_size = max(source_code_sizes, default=0)
        self.minimum_source_code_file_size = min(source_code_sizes, default=0)
        self.source_code_files_modified_num = len(source_code_sizes)
        self.total_other_file_size = sum(other_sizes)
        self.average_other_file_size = self.total_other_file_size / len(other_sizes) if other_sizes else 0
        self.maximum_other_file_size = max(other_sizes, default=0)
        self.minimum_other_file_size = min(other_sizes, default=0)
        self.other_files_modified_num = len(other_sizes)
        self.total_test_file_size = sum(test_sizes)
        self.average_test_file_size = self.total_test_file_size / len(test_sizes) if test_sizes else 0
        self.maximum_test_file_size = max(test_sizes, default=0)
        self.minimum_test_file_size = min(test_sizes, default=0)
        self.test_files_modified_num = len(test_sizes)

        if metrics_file_count:
            for metric in METRIC_NAMES:
                self.metrics[f"{metric}_avg"] = (
                        self.metrics[f"{metric}_total"] / metrics_file_count
                )
        else:
            # these values are initialized with sys.maxsize (because we take the min)
            # if no files, then reset them to 0 (it'd be stupid to have min > max)
            for metric in METRIC_NAMES:
                self.metrics[f"{metric}_min"] = 0
        return self
