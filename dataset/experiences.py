# Created by Baole Fang at 6/6/23
import logging
from datetime import datetime
from typing import Collection, Any, Union

from tqdm import tqdm
from collections import deque
from dataset.commit import Commit

logger = logging.getLogger(__name__)

EXPERIENCE_TIMESPAN = 90
EXPERIENCE_TIMESPAN_TEXT = f"{EXPERIENCE_TIMESPAN}_days"


class Experiences:
    def __init__(self, save):
        self.save = save
        self.db_experiences = {}

        if not save:
            self.mem_experiences = {}

    def __contains__(self, key):
        if self.save:
            return key in self.db_experiences
        else:
            return key in self.mem_experiences or key in self.db_experiences

    def __getitem__(self, key):
        if self.save:
            return self.db_experiences[key]
        else:
            return (
                self.mem_experiences[key]
                if key in self.mem_experiences
                else self.db_experiences[key]
            )

    def __setitem__(self, key, value):
        if self.save:
            self.db_experiences[key] = value
        else:
            self.mem_experiences[key] = value


class ExpQueue:
    def __init__(self, start_day: int, maxlen: int, default: Any) -> None:
        self.list = deque([default] * maxlen, maxlen=maxlen)
        self.start_day = start_day - (maxlen - 1)
        self.default = default

    def __deepcopy__(self, memo):
        result = ExpQueue.__new__(ExpQueue)

        # We don't need to deepcopy the list, as elements in the list are immutable.
        result.list = self.list.copy()
        result.start_day = self.start_day
        result.default = self.default

        return result

    @property
    def last_day(self) -> int:
        assert self.list.maxlen is not None
        return self.start_day + (self.list.maxlen - 1)

    def __getitem__(self, day: int) -> Any:
        # assert (
        #         day >= self.start_day
        # ), f"Can't get a day ({day}) from earlier than start day ({self.start_day})"
        if day<self.start_day:
            day=self.start_day

        if day < 0:
            return self.default

        if day > self.last_day:
            return self.list[-1]

        return self.list[day - self.start_day]

    def __setitem__(self, day: int, value: Any) -> None:
        assert self.list.maxlen is not None
        if day == self.last_day:
            self.list[day - self.start_day] = value
        elif day > self.last_day:
            last_val = self.list[-1]
            # We need to extend the list except for 2 elements (the last, which
            # is going to be the same, and the one we are adding now).
            range_end = min(day - self.last_day, self.list.maxlen) - 2
            if range_end > 0:
                self.list.extend(last_val for _ in range(range_end))

            self.start_day = day - (self.list.maxlen - 1)

            self.list.append(value)
        else:
            assert False, "Can't insert in the past"

        assert day == self.last_day


def calculate_experiences(
        commits: Collection[Commit], first_pushdate: datetime, save: bool = True
) -> None:
    logger.info("Analyzing seniorities from %d commits...", len(commits))

    experiences = Experiences(save)

    for commit in tqdm(commits, desc='calculating experiences'):
        key = f"first_commit_time${commit.author}"
        if key not in experiences:
            experiences[key] = commit.pushdate
            commit.seniority_author = 0
        else:
            time_lapse = commit.pushdate - experiences[key]
            commit.seniority_author = time_lapse.total_seconds()

    logger.info("Analyzing experiences from %d commits...", len(commits))

    # Note: In the case of files, directories, components, we can't just use the sum of previous commits, as we could end
    # up overcounting them. For example, consider a commit A which modifies "dir1" and "dir2", a commit B which modifies
    # "dir1" and a commit C which modifies "dir1" and "dir2". The number of previous commits touching the same directories
    # for C should be 2 (A + B), and not 3 (A twice + B).

    def get_key(exp_type: str, commit_type: str, item: str) -> str:
        return f"{exp_type}${commit_type}${item}"

    def get_experience(
            exp_type: str, commit_type: str, item: str, day: int, default: Union[int, tuple]
    ) -> ExpQueue:
        key = get_key(exp_type, commit_type, item)
        try:
            return experiences[key]
        except KeyError:
            queue = ExpQueue(day, EXPERIENCE_TIMESPAN + 1, default)
            experiences[key] = queue
            return queue

    def update_experiences(
            experience_type: str, day: int, items: Collection[str]
    ) -> None:
        for commit_type in ("", "backout"):
            exp_queues = tuple(
                get_experience(experience_type, commit_type, item, day, 0)
                for item in items
            )
            total_exps = tuple(exp_queues[i][day] for i in range(len(items)))
            timespan_exps = tuple(
                exp - exp_queues[i][day - EXPERIENCE_TIMESPAN]
                for exp, i in zip(total_exps, range(len(items)))
            )

            total_exps_sum = sum(total_exps)
            timespan_exps_sum = sum(timespan_exps)

            commit.set_experience(
                experience_type,
                commit_type,
                "total",
                total_exps_sum,
                max(total_exps, default=0),
                min(total_exps, default=0),
            )
            commit.set_experience(
                experience_type,
                commit_type,
                EXPERIENCE_TIMESPAN_TEXT,
                timespan_exps_sum,
                max(timespan_exps, default=0),
                min(timespan_exps, default=0),
            )

            # We don't want to consider backed out commits when calculating normal experiences.
            if (
                    commit_type == ""
                    # and not commit.backedoutby
                    or commit_type == "backout"
                    # and commit.backedoutby
            ):
                for i in range(len(items)):
                    exp_queues[i][day] = total_exps[i] + 1

    def update_complex_experiences(
            experience_type: str, day: int, items: Collection[str]
    ) -> None:
        for commit_type in ("", "backout"):
            exp_queues = tuple(
                get_experience(experience_type, commit_type, item, day, tuple())
                for item in items
            )
            all_commit_lists = tuple(exp_queues[i][day] for i in range(len(items)))
            before_commit_lists = tuple(
                exp_queues[i][day - EXPERIENCE_TIMESPAN] for i in range(len(items))
            )
            timespan_commit_lists = tuple(
                commit_list[len(before_commit_list):]
                for commit_list, before_commit_list in zip(
                    all_commit_lists, before_commit_lists
                )
            )

            all_commits = set(sum(all_commit_lists, tuple()))
            timespan_commits = set(sum(timespan_commit_lists, tuple()))

            commit.set_experience(
                experience_type,
                commit_type,
                "total",
                len(all_commits),
                max(
                    (len(all_commit_list) for all_commit_list in all_commit_lists),
                    default=0,
                ),
                min(
                    (len(all_commit_list) for all_commit_list in all_commit_lists),
                    default=0,
                ),
            )
            commit.set_experience(
                experience_type,
                commit_type,
                EXPERIENCE_TIMESPAN_TEXT,
                len(timespan_commits),
                max(
                    (
                        len(timespan_commit_list)
                        for timespan_commit_list in timespan_commit_lists
                    ),
                    default=0,
                ),
                min(
                    (
                        len(timespan_commit_list)
                        for timespan_commit_list in timespan_commit_lists
                    ),
                    default=0,
                ),
            )

            # We don't want to consider backed out commits when calculating normal experiences.
            if (
                    commit_type == ""
                    # and not commit.backedoutby
                    or commit_type == "backout"
                    # and commit.backedoutby
            ):
                for i in range(len(items)):
                    exp_queues[i][day] = all_commit_lists[i] + (commit.node,)

    for i, commit in enumerate(tqdm(commits, desc='updating experiences')):
        # The push date is unreliable, e.g. 4d0e3037210dd03bdb21964a6a8c2e201c45794b was pushed after
        # 06b578dfadc9db8b683090e0e110ba75b84fb766, but it has an earlier push date.
        # We accept the unreliability as it is small enough.
        day = (commit.pushdate - first_pushdate).days
        assert day >= 0

        # When a file is moved/copied, copy original experience values to the copied path.
        for orig, copied in commit.file_copies.items():
            for commit_type in ("", "backout"):
                orig_key = get_key("file", commit_type, orig)
                if orig_key in experiences:
                    experiences[get_key("file", commit_type, copied)] = copy.deepcopy(
                        experiences[orig_key]
                    )
                else:
                    logger.warning(
                        f"Experience missing for file {orig}, type '{commit_type}', on commit {commit.node}"
                    )

        if (
                not commit.ignored
                # and len(commit.backsout) == 0
                and commit.bug_id is not None
        ):
            update_experiences("author", day, (commit.author,))
            update_experiences("reviewer", day, commit.reviewers)

            update_complex_experiences("file", day, commit.files)
            update_complex_experiences("directory", day, commit.directories)
            # update_complex_experiences("component", day, commit.components)
