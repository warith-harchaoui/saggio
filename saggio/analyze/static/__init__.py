"""
Reading a repository without running it.

Module summary
--------------
Before anything is executed, a great deal can be learned by reading. Which
languages the repository is written in, what shape of work it does, which compute
frameworks it imports, how much work a full run performs, which paid services it
calls and on which line, and what could be run as a short representative slice.

Everything in this module is deterministic and quotes its evidence. That is the
division of labour the package keeps: **the static pass owns every number**, and
the local model, when one is available, owns only qualitative judgements. A number
that came out of a language model is a number nobody can check.

The work-size read is where care is needed. A repository often states its size in
more than one place, and an earlier file saying ``max_iters = 300`` while the real
configuration says ``600000`` would silently cap a measured slice at two thousand
times the intended size. So every candidate is collected, precedence is explicit
and documented, and a disagreement is recorded rather than resolved in silence.

Usage example
-------------
>>> from saggio.analyze.static import read_repository
>>> reading = read_repository(".")
>>> reading.languages.get("Python", 0) > 0
True

Author
------
Warith Harchaoui
"""

from __future__ import annotations

from .archetype import (
    declares_console_script,
    detect_archetype,
    detect_frameworks,
)
from .calls import detect_models, detect_services, model_named_on
from .findings import ModelHit, RepositoryReading, ServiceHit, WorkSizeCandidate
from .languages import detect_languages
from .read import read_repository
from .running import (
    capped_entrypoint_command,
    detect_tests,
    find_entrypoint,
    scaling_ladder,
)
from .tables import (
    ARCHETYPE_FILES,
    CONFIG_FILE_PRECEDENCE,
    DEFAULT_CAP_FRACTION,
    DEFAULT_SCALING_GROWTH,
    DEFAULT_SCALING_STEPS,
    ENTRYPOINT_NAMES,
    FOUND_ONLY_IN_SUITE,
    FRAMEWORK_INVOCATIONS,
    FRAMEWORK_MODULES,
    FRAMEWORK_PATTERNS,
    LANGUAGE_BY_EXTENSION,
    MODEL_ASSIGNMENT_PATTERN,
    MODEL_MAPPING_PATTERN,
    PROSE_MARKERS,
    SIDE_ERRAND_DIRECTORIES,
    SKIPPED_DIRECTORIES,
    TEST_DIRECTORIES,
    TRAINING_DIRECTORIES,
    WORK_SIZE_KEYS,
)
from .walking import _is_prose_line, _iter_source_files, is_test_path
from .worksize import find_work_size

__all__ = [
    "ARCHETYPE_FILES",
    "CONFIG_FILE_PRECEDENCE",
    "DEFAULT_CAP_FRACTION",
    "DEFAULT_SCALING_GROWTH",
    "DEFAULT_SCALING_STEPS",
    "ENTRYPOINT_NAMES",
    "FOUND_ONLY_IN_SUITE",
    "FRAMEWORK_INVOCATIONS",
    "FRAMEWORK_MODULES",
    "FRAMEWORK_PATTERNS",
    "LANGUAGE_BY_EXTENSION",
    "MODEL_ASSIGNMENT_PATTERN",
    "MODEL_MAPPING_PATTERN",
    "ModelHit",
    "PROSE_MARKERS",
    "RepositoryReading",
    "SIDE_ERRAND_DIRECTORIES",
    "SKIPPED_DIRECTORIES",
    "ServiceHit",
    "TEST_DIRECTORIES",
    "TRAINING_DIRECTORIES",
    "WORK_SIZE_KEYS",
    "WorkSizeCandidate",
    "capped_entrypoint_command",
    "declares_console_script",
    "detect_archetype",
    "detect_frameworks",
    "detect_languages",
    "detect_models",
    "detect_services",
    "detect_tests",
    "find_entrypoint",
    "find_work_size",
    "is_test_path",
    "model_named_on",
    "read_repository",
    "scaling_ladder",
    "_is_prose_line",
    "_iter_source_files",
]
