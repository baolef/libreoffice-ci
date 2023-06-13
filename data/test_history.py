# Created by Baole Fang at 6/12/23
import itertools

from tqdm import tqdm

from mining import get_rows, read
from collections import Counter, defaultdict

def get_pushes(filename, limit):
    rows = get_rows(filename, limit)
    raw = read(rows)
    return raw

def generate_failing_together_probabilities(
    granularity: str,
    push_data: dict,
    push_data_count: int,
    up_to: str = None,
) -> None:
    # `task2 failure -> task1 failure` separately, as they could be different.


    count_runs = Counter()
    count_single_failures = Counter()
    count_both_failures= Counter()

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
    available_configs_by_group = defaultdict(set)

    for key, value in tqdm(push_data.items()):
        rev=key[1]
        failures=set(value)


    for (
        revisions,
        fix_revision,
        tasks,
        likely_regressions,
        candidate_regressions,
    ) in tqdm(push_data, total=push_data_count):
        failures = set(likely_regressions + candidate_regressions)
        all_tasks_set = set(tasks) | failures
        all_tasks = list(all_tasks_set)

        # At config/group granularity, only consider redundancy between the same manifest
        # on different configurations, and not between manifests too.
        if granularity == "config_group":
            all_available_configs.update(config for config, group in all_tasks)
            for config, group in all_tasks:
                available_configs_by_group[group].add(config)

            groups = itertools.groupby(
                sorted(all_tasks, key=lambda x: x[1]), key=lambda x: x[1]
            )
            for manifest, group_tasks in groups:
                count_runs_and_failures(group_tasks)
        else:
            all_available_configs |= all_tasks_set
            count_runs_and_failures(all_tasks)

        if up_to is not None and revisions[0] == up_to:
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
    count_redundancies: collections.Counter = collections.Counter()
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

    failing_together_db = get_failing_together_db(granularity, False)

    failing_together_db[b"$ALL_CONFIGS$"] = pickle.dumps(list(all_available_configs))

    if granularity == "config_group":
        failing_together_db[b"$CONFIGS_BY_GROUP$"] = pickle.dumps(
            dict(available_configs_by_group)
        )

    for key, value in failing_together.items():
        failing_together_db[failing_together_key(key)] = pickle.dumps(value)

    close_failing_together_db(granularity)


def generate_history(filename, limit=None):
    pushes=get_pushes(filename,limit)

