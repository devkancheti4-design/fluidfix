# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 devkancheti4-design
"""fluidfix — zero-token repair decisions for mechanical single-line bugs.

    from fluidfix import Oracle, build_packet, MechanicalObserver, repair

    oracle = Oracle("path/to/project", python="path/to/venv/bin/python")
    packet = build_packet(oracle, "pkg/module.py")
    observations = MechanicalObserver().observe([packet])[0]
    result = repair(oracle, "pkg/module.py", observations)
    print(result.summary())
"""
from .acts import (ACTS, KINDS, WORKED_EXAMPLE, Observation, SpanEdit, act_for, apply,
                   candidates, register)
from .guard import (GuardReport, commit_repair, find_candidate_files,
                    guard_once, write_refusal)
from .lanes import ADVANCE, EMIT, HALT, kind_of, mask_of
from .localize import Packet, build_packet
from .loop import RepairResult, repair
from .observers import ClaudeObserver, MechanicalObserver, observer_prompt
from .oracle import Oracle
from .router import pack, route, route_packed

__version__ = "0.9.0"
__all__ = [
    "route", "route_packed", "pack",
    "EMIT", "ADVANCE", "HALT", "mask_of", "kind_of",
    "Observation", "KINDS", "ACTS", "WORKED_EXAMPLE", "act_for", "apply",
    "register", "candidates",
    "Oracle", "Packet", "build_packet",
    "MechanicalObserver", "ClaudeObserver", "observer_prompt",
    "repair", "RepairResult",
    "GuardReport", "guard_once", "find_candidate_files", "commit_repair",
    "write_refusal",
]
