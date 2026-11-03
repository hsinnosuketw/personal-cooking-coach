"""The recipe as a task graph: which steps must be finished before another can start, and which repeat.

Cooks rarely follow the recipe order: they chop the onion before cracking the eggs, or plate while the pan heats.
That is fine as long as a step's prerequisites are done before it starts. The graph is written once per recipe,
from the recipe text only (one coach call), and reused by every run.
"""
from __future__ import annotations

import re

LOOP_RE = re.compile(r"^\W*LOOP\W*:\s*(\d+)\s*(?:-\s*(\d+))?\s*\|\s*([^|\n]*)\|\s*(.*)$", re.M | re.I)
NEEDS_RE = re.compile(r"^\W*STEP\s*(\d+)\W*NEEDS\W*:\s*(.*)$", re.M | re.I)


def graph_prompt(name: str, texts: list[str]) -> str:
    recipe = "\n".join(f"{k + 1}. {s}" for k, s in enumerate(texts))
    return f"""Recipe: {name}
{recipe}

Home cooks often do steps out of order or in parallel (chopping while the pan heats, cracking eggs at the end).
For each step, list only the steps that must really be FINISHED before it can START (its ingredients or tools come
from them). Steps that could be done in any order are not prerequisites. Use only the recipe text.
Then list every run of consecutive steps a cook repeats (once per item, or until something is ready).
Answer with exactly these lines and nothing else:
STEP <n> NEEDS: <step numbers, or none>      (one line per step, for every step)
LOOP: <first step>-<last step> | <how many times, or "until done"> | <what is repeated>      (or LOOP: none)"""


def loops_prompt(name: str, texts: list[str]) -> str:
    """Stage 27's question: only the repeated runs."""
    recipe = "\n".join(f"{k + 1}. {s}" for k, s in enumerate(texts))
    return f"""Recipe: {name}
{recipe}

Some recipes repeat a run of steps: once per item (each disc, each paratha, each slice), or until something is ready (flip until both sides are brown).
List every run of consecutive steps that a cook repeats. Use only the recipe text.
Answer with one line per run, and nothing else:
LOOP: <first step>-<last step> | <how many times, or "until done"> | <what is repeated, in a few words>
If no steps repeat, answer exactly: LOOP: none"""


def parse_loops(text: str, n_steps: int) -> list[dict]:
    """LOOP lines as [{"first", "last", "times", "what"}], 0-based."""
    loops = []
    for m in LOOP_RE.finditer(text or ""):
        a, b = int(m[1]) - 1, int(m[2] or m[1]) - 1
        if 0 <= a <= b < n_steps:
            loops.append({"first": a, "last": b, "times": m[3].strip(), "what": m[4].strip()})
    return loops


def parse_graph(text: str, n_steps: int) -> dict:
    """{"needs": {step: [prerequisite steps]}, "loops": [{"first", "last", "times", "what"}]}; steps are 0-based."""
    needs = {k: [] for k in range(n_steps)}
    for m in NEEDS_RE.finditer(text or ""):
        k = int(m[1]) - 1
        if 0 <= k < n_steps:
            needs[k] = sorted({int(x) - 1 for x in re.findall(r"\d+", m[2]) if 0 <= int(x) - 1 < k})  # only earlier steps
    return {"needs": needs, "loops": parse_loops(text, n_steps)}


def needed_by(needs: dict[int, list[int]]) -> dict[int, list[int]]:
    """Step -> the steps that need it (the reverse of needs)."""
    out: dict[int, list[int]] = {k: [] for k in needs}
    for k, pre in needs.items():
        for j in pre:
            out.setdefault(j, []).append(k)
    return out


def all_prerequisites(needs: dict[int, list[int]], k: int) -> set[int]:
    """Every step that must be finished before k, directly or through other steps."""
    seen, todo = set(), list(needs.get(k, []))
    while todo:
        j = todo.pop()
        if j not in seen:
            seen.add(j)
            todo += needs.get(j, [])
    return seen
