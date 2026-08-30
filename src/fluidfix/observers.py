# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 devkancheti4-design
# Commercial licensing: see COMMERCIAL.md.
"""Observers: perception in, structured observations out. Never a fix.

MechanicalObserver  the zero-token default — kdebug's line regexes walked over
                    the packet's localised lines only (not the whole file, so
                    the measured 152x blind-search penalty never applies).
ClaudeObserver      Claude Opus 5 as a clear data provider: one batched call
                    for any number of packets, schema-forced output, with the
                    literal/operator pointers that took the benchmark corpus
                    from 17/27 to 26/27 in-vocabulary byte-exact.

The kind vocabulary in the prompt is generated from `acts.KINDS`, so the
mechanical regexes, the LLM contract, and the appliers can never drift apart.
"""
from __future__ import annotations

import json
import re

from .acts import KINDS, Observation
from .localize import Packet

__all__ = ["MechanicalObserver", "ClaudeObserver", "observer_prompt"]


class MechanicalObserver:
    """kdebug's observer, localised. Zero tokens, zero network."""

    def observe(self, packets: list[Packet]) -> list[list[Observation]]:
        out = []
        for p in packets:
            obs = []
            for l in p.lines:
                line = p.src_lines[l - 1].rstrip("\r")
                kinds = [k for k, (_, _, sig) in sorted(KINDS.items())
                         if sig.search(line)]
                if kinds:
                    obs.append(Observation(lineno=l, kinds=kinds))
            out.append(obs)
        return out


def observer_prompt(packets: list[Packet]) -> str:
    kinds_txt = "\n".join(f"   {k} = {name}: {desc}"
                          for k, (name, desc, _) in sorted(KINDS.items()))
    head = f"""You are a fault OBSERVER in a mechanical repair pipeline. You are NOT a debugger: never propose, describe, or apply a fix. A machine routes your observations to repairs; your only job is clean data.

Below are {len(packets)} independent bugs. Each "### BUG <id>" section gives the defect file's name, the compressed failing output of that project's own test suite, and numbered excerpts of the defect file — only the lines the failing test executed, so for runtime faults the defective line is in the excerpt.

For EVERY bug id report:
1. lineno — the 1-based line number of the defective line (the number before the "|"). Best effort even when you must refuse the kind.
2. kinds — fault kinds that apply to that line, from this closed vocabulary, most specific first:
{kinds_txt}
   If NONE of these describes the defect, return an empty kinds list. Never force-fit: the empty list is a correct and valued answer.
3. literal_value / literal_occurrence — only when kind 1 applies: the wrong literal exactly as its digits appear on the line, and which occurrence it is counting every match of that exact digit-run on the line, 1-based. The repair decrements THAT occurrence by one. Otherwise null.
4. op_occurrence — only when kind 3 applies: which binary additive operator is flipped, counting every " + " or " - " on the line left to right, 1-based. Otherwise null.

Rules: work only from this document; judge each bug independently; echo every bug id exactly once, in the order given; no fix suggestions anywhere."""
    body = "\n\n".join(p.render(tag=f"BUG {i}") for i, p in enumerate(packets))
    return head + "\n\n" + body


_SCHEMA_ITEM = {
    "type": "object",
    "properties": {
        "id": {"type": "integer"},
        "lineno": {"type": "integer"},
        "kinds": {"type": "array",
                  "items": {"type": "integer", "minimum": 0, "maximum": 15}},
        "literal_value": {"anyOf": [{"type": "null"}, {"type": "string"}]},
        "literal_occurrence": {"anyOf": [{"type": "null"}, {"type": "integer"}]},
        "op_occurrence": {"anyOf": [{"type": "null"}, {"type": "integer"}]},
    },
    "required": ["id", "lineno", "kinds", "literal_value",
                 "literal_occurrence", "op_occurrence"],
    "additionalProperties": False,
}


class ClaudeObserver:
    """Claude Opus 5, batched, schema-forced. Requires `pip install fluidfix[llm]`
    and Anthropic credentials (ANTHROPIC_API_KEY or an `ant auth login` profile).

    Server-side refusal fallbacks are enabled by default on the beta surface;
    if the account or platform rejects the beta, the call transparently retries
    on the plain Messages API without fallbacks.
    """

    def __init__(self, model: str = "claude-opus-5", client=None,
                 fallbacks: bool = True, max_tokens: int = 16000):
        if client is None:
            import anthropic
            client = anthropic.Anthropic()
        self.client = client
        self.model = model
        self.fallbacks = fallbacks
        self.max_tokens = max_tokens
        self.last_usage = None

    def _call(self, prompt: str, n: int):
        fmt = {"format": {"type": "json_schema", "schema": {
            "type": "object",
            "properties": {"observations": {
                "type": "array", "minItems": n, "maxItems": n,
                "items": _SCHEMA_ITEM}},
            "required": ["observations"],
            "additionalProperties": False,
        }}}
        kwargs = dict(model=self.model, max_tokens=self.max_tokens,
                      output_config=fmt,
                      messages=[{"role": "user", "content": prompt}])
        if self.fallbacks:
            # SDK import only on this path: an injected client with
            # fallbacks=False must work without the anthropic package.
            try:
                import anthropic
                bad_request = anthropic.BadRequestError
            except ModuleNotFoundError:
                bad_request = ()
            try:
                return self.client.beta.messages.create(
                    betas=["server-side-fallback-2026-07-01"],
                    fallbacks="default", **kwargs)
            except bad_request:
                pass  # beta not available here — fall through to plain call
        return self.client.messages.create(**kwargs)

    def observe(self, packets: list[Packet]) -> list[list[Observation]]:
        response = self._call(observer_prompt(packets), len(packets))
        if getattr(response, "stop_reason", None) == "refusal":
            det = getattr(response, "stop_details", None)
            raise RuntimeError(f"observer request refused: "
                               f"{getattr(det, 'explanation', 'no details')}")
        self.last_usage = getattr(response, "usage", None)
        stop = getattr(response, "stop_reason", None)
        if stop == "max_tokens":
            raise RuntimeError("observer response truncated at max_tokens="
                               f"{self.max_tokens} — raise max_tokens or send "
                               "fewer packets per call")
        text = next((b.text for b in response.content if b.type == "text"), None)
        if text is None:
            raise RuntimeError(f"observer returned no text block (stop_reason={stop})")
        try:
            raw = {o["id"]: o for o in json.loads(text)["observations"]}
        except (json.JSONDecodeError, KeyError, TypeError) as e:
            raise RuntimeError(f"observer returned unparseable output "
                               f"(stop_reason={stop}): {e}") from e
        missing = [i for i in range(len(packets)) if i not in raw]
        if missing:
            # a failed observer round trip must not masquerade as an honest
            # refusal — the ids are echoed from the prompt and must all match
            raise RuntimeError(f"observer echoed wrong bug ids: missing {missing}, "
                               f"got {sorted(raw)}")
        out = []
        for i, _ in enumerate(packets):
            o = raw[i]
            out.append([Observation(
                lineno=int(o["lineno"]),
                kinds=[k for k in o["kinds"] if isinstance(k, int)],
                literal_value=(str(o["literal_value"])
                               if o.get("literal_value") not in (None, "") else None),
                literal_occurrence=o.get("literal_occurrence"),
                op_occurrence=o.get("op_occurrence"),
            )])
        return out
