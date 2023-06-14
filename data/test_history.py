# Created by Baole Fang at 6/12/23
import itertools
import logging

from tqdm import tqdm
from collections import Counter, defaultdict
from util import *
from typing import Any, Generator
from experiences import ExpQueue

logger = logging.getLogger(__name__)

HISTORICAL_TIMESPAN = 4500

with open('tests.txt', 'rb') as f:
    ALL_TESTS = pickle.load(f)


def get_pushes(filename, limit):
    commits = read_file(filename)[:limit]
    return commits


def generate_failing_together_probabilities(
        granularity: str,
        push_data: list,
        up_to: str = None,
) -> None:
    # `task2 failure -> task1 failure` separately, as they could be different.

    count_runs = Counter()
    count_single_failures = Counter()
    count_both_failures = Counter()

    def count_runs_and_failures(tasks):
        for task1, task2 in itertools.combinations(sorted(tasks), 2):
            count_runs[(task1, task2)] += 1

            if task1 in failures:
                if task2 in failures:
                    count_both_failures[(task1, task2)] += 1
                else:
                    count_single_failures[(task1, task2)] += 1
            elif task2 in failures:
                count_single_failures[(task1, task2)] += 1

    all_available_configs = set()

    for commit in tqdm(push_data):
        all_tasks_set = ALL_TESTS
        all_tasks = list(all_tasks_set)
        all_available_configs |= all_tasks_set
        failures = commit['failures']
        count_runs_and_failures(all_tasks)
        if up_to is not None and commit['node'] == up_to:
            break

    stats = {}

    skipped = 0

    for couple, run_count in count_runs.most_common():
        failure_count = count_both_failures[couple]
        single_failure_count = count_single_failures[couple]
        support = failure_count / run_count

        # At manifest-level, don't filter based on support.
        if granularity != "config_group" and support < 1 / 700:
            skipped += 1
            continue

        # At manifest-level, consider failures to be platform independent unless
        # proven otherwise.
        if failure_count != 0:
            confidence = failure_count / (single_failure_count + failure_count)
        elif single_failure_count == 0 and granularity == "config_group":
            confidence = 1.0
        else:
            confidence = 0.0

        stats[couple] = (support, confidence)

    logger.info("%d couples skipped because their support was too low", skipped)

    logger.info("Redundancies with the highest support and confidence:")
    for couple, (support, confidence) in sorted(
            stats.items(), key=lambda k: (-k[1][1], -k[1][0])
    )[:7]:
        failure_count = count_both_failures[couple]
        run_count = count_runs[couple]
        logger.info(
            "%s - %s redundancy confidence %f, support %d (%d over %d).",
            couple[0],
            couple[1],
            confidence,
            support,
            failure_count,
            run_count,
        )

    logger.info("Redundancies with the highest confidence and lowest support:")
    for couple, (support, confidence) in sorted(
            stats.items(), key=lambda k: (-k[1][1], k[1][0])
    )[:7]:
        failure_count = count_both_failures[couple]
        run_count = count_runs[couple]
        logger.info(
            "%s - %s redundancy confidence %f, support %d (%d over %d).",
            couple[0],
            couple[1],
            confidence,
            support,
            failure_count,
            run_count,
        )

    failing_together: dict = {}
    count_redundancies = Counter()
    for couple, (support, confidence) in stats.items():
        if confidence == 1.0:
            count_redundancies["==100%"] += 1
        if confidence > 0.9:
            count_redundancies[">=90%"] += 1
        if confidence > 0.8:
            count_redundancies[">=80%"] += 1
        if confidence > 0.7:
            count_redundancies[">=70%"] += 1
        if confidence > 0.6:
            count_redundancies[">=60%"] += 1
        if confidence > 0.5:
            count_redundancies[">=50%"] += 1
        if confidence > 0.4:
            count_redundancies[">=40%"] += 1
        if confidence > 0.3:
            count_redundancies[">=30%"] += 1
        if confidence > 0.2:
            count_redundancies[">=20%"] += 1
        if confidence > 0.1:
            count_redundancies[">=10%"] += 1
        if confidence > 0.0:
            count_redundancies[">0%"] += 1
        if confidence == 0.0:
            count_redundancies["0%"] += 1

        if granularity == "config_group":
            if couple[0][1] not in failing_together:
                failing_together[couple[0][1]] = {}

            if couple[0][0] not in failing_together[couple[0][1]]:
                failing_together[couple[0][1]][couple[0][0]] = {}

            failing_together[couple[0][1]][couple[0][0]][couple[1][0]] = (
                support,
                confidence,
            )
        else:
            if couple[0] not in failing_together:
                failing_together[couple[0]] = {}

            failing_together[couple[0]][couple[1]] = (support, confidence)

    for percentage, count in count_redundancies.most_common():
        logger.info("%d with %f%% confidence", count, percentage)

    failing_together["$ALL_CONFIGS$"] = all_available_configs

    write_file(failing_together, 'failing_together.gz')


def _read_and_update_past_failures(
        past_failures, type_, runnable, items, push_num, is_regression
):
    values_total = []
    values_prev_700 = []
    values_prev_1400 = []
    values_prev_2800 = []

    key = f"{type_}${runnable}$"

    for item in items:
        full_key = key + item

        is_new = full_key not in past_failures

        if is_new:
            if not is_regression:
                continue

            cur = ExpQueue(round(push_num / 100), int(HISTORICAL_TIMESPAN / 100) + 1, 0)
        else:
            cur = past_failures[full_key]

        value = cur[round(push_num / 100)]

        values_total.append(value)
        values_prev_700.append(value - cur[round((push_num - 700) / 100)])
        values_prev_1400.append(value - cur[round((push_num - 1400) / 100)])
        values_prev_2800.append(value - cur[round((push_num - 2800) / 100)])

        if is_regression:
            cur[round(push_num / 100)] = value + 1
            if is_new:
                past_failures[full_key] = cur

    return (
        sum(values_total),
        sum(values_prev_700),
        sum(values_prev_1400),
        sum(values_prev_2800),
    )


def generate_data(
        past_failures: dict,
        commit: dict,
        push_num: int,
        runnables: list,
        failures: list
):
    for runnable in runnables:
        is_regression = runnable in failures

        (
            total_failures,
            past_700_pushes_failures,
            past_1400_pushes_failures,
            past_2800_pushes_failures,
        ) = _read_and_update_past_failures(
            past_failures, "all", runnable, ("all",), push_num, is_regression
        )

        (
            total_types_failures,
            past_700_pushes_types_failures,
            past_1400_pushes_types_failures,
            past_2800_pushes_types_failures,
        ) = _read_and_update_past_failures(
            past_failures,
            "type",
            runnable,
            commit["types"],
            push_num,
            is_regression,
        )

        (
            total_files_failures,
            past_700_pushes_files_failures,
            past_1400_pushes_files_failures,
            past_2800_pushes_files_failures,
        ) = _read_and_update_past_failures(
            past_failures,
            "file",
            runnable,
            commit["files"],
            push_num,
            is_regression,
        )

        (
            total_directories_failures,
            past_700_pushes_directories_failures,
            past_1400_pushes_directories_failures,
            past_2800_pushes_directories_failures,
        ) = _read_and_update_past_failures(
            past_failures,
            "directory",
            runnable,
            commit["directories"],
            push_num,
            is_regression,
        )

        # (
        #     total_components_failures,
        #     past_700_pushes_components_failures,
        #     past_1400_pushes_components_failures,
        #     past_2800_pushes_components_failures,
        # ) = _read_and_update_past_failures(
        #     past_failures,
        #     "component",
        #     runnable,
        #     commit["components"],
        #     push_num,
        #     is_regression,
        # )

        obj = {
            "name": runnable,
            "failures": total_failures,
            "failures_past_700_pushes": past_700_pushes_failures,
            "failures_past_1400_pushes": past_1400_pushes_failures,
            "failures_past_2800_pushes": past_2800_pushes_failures,
            "failures_in_types": total_types_failures,
            "failures_past_700_pushes_in_types": past_700_pushes_types_failures,
            "failures_past_1400_pushes_in_types": past_1400_pushes_types_failures,
            "failures_past_2800_pushes_in_types": past_2800_pushes_types_failures,
            "failures_in_files": total_files_failures,
            "failures_past_700_pushes_in_files": past_700_pushes_files_failures,
            "failures_past_1400_pushes_in_files": past_1400_pushes_files_failures,
            "failures_past_2800_pushes_in_files": past_2800_pushes_files_failures,
            "failures_in_directories": total_directories_failures,
            "failures_past_700_pushes_in_directories": past_700_pushes_directories_failures,
            "failures_past_1400_pushes_in_directories": past_1400_pushes_directories_failures,
            "failures_past_2800_pushes_in_directories": past_2800_pushes_directories_failures,
            # "failures_in_components": total_components_failures,
            # "failures_past_700_pushes_in_components": past_700_pushes_components_failures,
            # "failures_past_1400_pushes_in_components": past_1400_pushes_components_failures,
            # "failures_past_2800_pushes_in_components": past_2800_pushes_components_failures,
        }

        yield obj


def generate_history(filename, limit=None):
    commits = get_pushes(filename, limit)
    generate_failing_together_probabilities("label", commits)

    def generate_all_data() -> Generator[dict[str, Any], None, None]:
        # global past_failures
        past_failures = {}

        push_num = 0

        # Store all runnables in the past_failures DB so it can be used in the evaluation phase.
        past_failures["all_runnables"] = ALL_TESTS
        # XXX: Should we recreate the DB from scratch if the previous all_runnables are not the
        # same as the current ones?

        skipped_no_commits = 0
        skipped_too_big_commits = 0
        skipped_no_runnables = 0

        for commit in tqdm(commits):
            push_num += 1

            # XXX: For now, skip commits which are too large.
            # In the future we can either:
            #  - Improve shelve perf and go back to consider all files;
            #  - Consider only files which appear with a given frequency, like the "files" feature in commit_features;
            #  - Keep a limit of number of files.
            if len(commit["files"]) > 50:
                skipped_too_big_commits += 1
                continue

            # If we considered all_runnables, we'd generate a huge amount of data.
            # We consider only the runnables which run in this push, and the possible and likely regressions
            # from this push. We can't consider all runnables because we can't be sure that a task that didn't
            # run on a push would have been successful.
            runnables_to_consider = ALL_TESTS

            # Sync DB every 250 pushes, so we cleanup the shelve cache (we'd run OOM otherwise!).
            # if i % 250 == 0:
            #     past_failures.sync()

            result_data = []
            for data in generate_data(
                    past_failures,
                    commit,
                    push_num,
                    runnables_to_consider,
                    commit['failures']
            ):
                result_data.append(data)

            yield {
                "revs": [commit['node']],
                "data": result_data,
            }

        logger.info("saved push data nodes: %d", len(commits))
        logger.info("skipped %d (no commits in our DB)", skipped_no_commits)
        logger.info("skipped %d (too big commits)", skipped_too_big_commits)
        logger.info("skipped %d (no interesting runnables)", skipped_no_runnables)

        past_failures["push_num"] = push_num

    test_scheduling_db = list(generate_all_data())
    write_file(test_scheduling_db, 'test_scheduling.gz')


if __name__ == '__main__':
    generate_history('commits.gz')
