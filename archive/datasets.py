"""Real student-interaction data: ASSISTments 2009-2010 skill-builder format.

The public skill-builder release is one row per student attempt with (among
others) these columns::

    order_id, assignment_id, user_id, assistment_id, problem_id,
    original, correct, ms_first_response, skill_id, skill_name, ...

Only four columns matter here: who (user_id), in what order (order_id),
which skill (skill_id, falling back to skill_name), and whether the attempt
was right (correct, kept only when 0/1). Everything else is ignored, so the
loader also accepts any CSV with equivalent columns (see ``load_csv``).

No network access is needed: point the loader at a downloaded file. A
synthetic generator in the same schema lives in ``replay.py``
(``make_synthetic_csv``) so the whole pipeline is testable offline.
"""
from __future__ import annotations

import csv
from collections import Counter, defaultdict


def load_csv(path: str,
             col_user: str = "user_id",
             col_order: str = "order_id",
             col_skill: str = "skill_id",
             col_skill_fallback: str = "skill_name",
             col_correct: str = "correct") -> tuple[list[dict], dict]:
    """Parse attempts into a canonical row list, sorted by (user, order).

    Each row is ``{"user": str, "skill": str, "correct": 0|1, "order": int}``.
    Rows with missing skills, non-integer order, or correctness outside
    {0, 1} are dropped; returns ``(rows, drop_counts)``.
    """
    rows, dropped = [], Counter()
    with open(path, newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        for line in reader:
            try:
                user = (line.get(col_user) or "").strip()
                skill = (line.get(col_skill) or "").strip()
                if not skill and col_skill_fallback:
                    skill = (line.get(col_skill_fallback) or "").strip()
                order = int(float(line[col_order]))
                correct = int(float(line[col_correct]))
            except (KeyError, TypeError, ValueError):
                dropped["unparseable"] += 1
                continue
            if not user or not skill:
                dropped["missing_id"] += 1
                continue
            if correct not in (0, 1):
                dropped["bad_correct"] += 1
                continue
            rows.append({"user": user, "skill": skill,
                         "correct": correct, "order": order})
    rows.sort(key=lambda r: (r["user"], r["order"]))
    return rows, dict(dropped)


def to_skill_sequences(rows: list[dict]) -> dict[tuple[str, str], list[int]]:
    """Group rows into ordered correctness lists keyed by (user, skill)."""
    seqs: dict[tuple[str, str], list[int]] = defaultdict(list)
    for r in rows:
        seqs[(r["user"], r["skill"])].append(r["correct"])
    return dict(seqs)


def top_skills(rows: list[dict], n: int) -> list[str]:
    """The n skills with the most attempts (stable order on ties)."""
    counts = Counter(r["skill"] for r in rows)
    return [s for s, _ in sorted(counts.items(), key=lambda kv: (-kv[1], kv[0]))[:n]]


def summarize(rows: list[dict]) -> dict:
    """One-line dataset portrait: users, skills, attempts, base rate."""
    users = {r["user"] for r in rows}
    skills = {r["skill"] for r in rows}
    n = len(rows)
    return {
        "users": len(users),
        "skills": len(skills),
        "attempts": n,
        "base_rate": (sum(r["correct"] for r in rows) / n) if n else 0.0,
    }


def learning_curve(rows: list[dict], skill: str, max_attempt: int = 30) -> list[float]:
    """P(correct) by within-skill attempt number, pooled across users.

    Attempt 1 uses every user's first try on `skill`; attempt k uses users
    with at least k tries. Returns NaN for positions with no data.
    """
    import math
    buckets: dict[int, list[int]] = defaultdict(list)
    seqs = to_skill_sequences([r for r in rows if r["skill"] == skill])
    for seq in seqs.values():
        for k, c in enumerate(seq[:max_attempt], start=1):
            buckets[k].append(c)
    return [(sum(v) / len(v)) if v else math.nan for k, v in
            (sorted(buckets.items()) if buckets else [])]


def split_users(rows: list[dict], n_train_users: int, seed: int = 0
                ) -> tuple[list[dict], list[dict]]:
    """Split rows by user id: first `n_train_users` (shuffled) for fitting."""
    import random
    users = sorted({r["user"] for r in rows})
    rng = random.Random(seed)
    rng.shuffle(users)
    train = set(users[:n_train_users])
    return ([r for r in rows if r["user"] in train],
            [r for r in rows if r["user"] not in train])


# ---------------------------------------------------------------------------
# Junyi Academy carrier: ProblemLog-shaped attempts, optional exercise table.
#
# Junyi-side files vary in exact header names, so columns are auto-detected
# from candidate aliases (case/punctuation-insensitive). A row needs: who
# (user), which exercise, whether it was right, and an ordering key
# (timestamp or running order). Skills come from the exercise->KC table
# when provided; otherwise each exercise is treated as its own skill
# (Junyi exercises each target one knowledge component).
# ---------------------------------------------------------------------------

_JUNYI_USER_CANDS = ("user_id", "uid", "user", "userid", "student_id")
_JUNYI_EXERCISE_CANDS = ("exercise", "exercise_id", "problem_id", "item_id",
                         "question_id", "problemid")
_JUNYI_CORRECT_CANDS = ("correct", "is_correct", "correctness", "score",
                        "is_right", "result")
_JUNYI_TIME_CANDS = ("timestamp", "time", "created_at", "date", "order",
                     "order_id", "seq", "index")
_JUNYI_KC_CANDS = ("kc", "kc_id", "knowledge_component", "skill",
                   "skill_id", "topic", "concept")


def _norm_header(h: str) -> str:
    return "".join(c for c in h.strip().lower() if c.isalnum())


def _detect_column(headers: list[str], candidates: tuple[str, ...],
                   label: str) -> str:
    norm = {_norm_header(h): h for h in headers}
    for cand in candidates:
        if _norm_header(cand) in norm:
            return norm[_norm_header(cand)]
    raise ValueError(
        f"Junyi loader: no {label} column found (tried "
        f"{', '.join(candidates)}); headers are {headers}")


def _parse_junyi_correct(raw) -> int:
    if isinstance(raw, bool):
        return int(raw)
    s = str(raw).strip().lower()
    if s in ("1", "1.0", "true", "t", "yes", "correct", "right"):
        return 1
    if s in ("0", "0.0", "false", "f", "no", "wrong", "incorrect"):
        return 0
    raise ValueError(f"bad correct value: {raw!r}")


def _parse_junyi_time(raw) -> tuple[int, float]:
    """Return (rank_key_kind, value): numeric orders sort before timestamps.

    Kind 0 = running number (order/seq/index or epoch); kind 1 = ISO string
    (compared lexicographically, which orders ISO-8601 correctly).
    """
    s = str(raw).strip()
    try:
        return (0, float(s))
    except (TypeError, ValueError):
        pass
    if not s:
        raise ValueError("empty timestamp")
    return (1, s)


def load_junyi_exercise_table(path: str, col_exercise: str | None = None,
                              col_kc: str | None = None) -> dict:
    """Map exercise id -> knowledge-component id from an exercise table."""
    with open(path, newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        headers = reader.fieldnames or []
        ce = col_exercise or _detect_column(headers, _JUNYI_EXERCISE_CANDS,
                                            "exercise")
        ck = col_kc or _detect_column(headers, _JUNYI_KC_CANDS,
                                       "knowledge component")
        mapping = {}
        for line in reader:
            ex, kc = (line.get(ce) or "").strip(), (line.get(ck) or "").strip()
            if ex and kc:
                mapping[ex] = kc
    if not mapping:
        raise ValueError(f"Junyi loader: no exercise->KC rows in {path}")
    return mapping


def load_junyi_problem_log(path: str, exercise_table_path: str | None = None,
                           col_user: str | None = None,
                           col_exercise: str | None = None,
                           col_correct: str | None = None,
                           col_time: str | None = None
                           ) -> tuple[list[dict], dict, dict]:
    """Parse a Junyi ProblemLog-shaped CSV into canonical rows.

    Returns ``(rows, drop_counts, meta)``. ``meta`` records the detected
    columns and whether skills came from the exercise table or raw
    exercise ids. Rows whose exercise has no KC mapping (when a table is
    given) are dropped and counted as ``unmapped_exercise``.
    """
    with open(path, newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        headers = reader.fieldnames or []
        cu = col_user or _detect_column(headers, _JUNYI_USER_CANDS, "user")
        ce = col_exercise or _detect_column(headers, _JUNYI_EXERCISE_CANDS,
                                            "exercise")
        cc = col_correct or _detect_column(headers, _JUNYI_CORRECT_CANDS,
                                           "correctness")
        ct = col_time or _detect_column(headers, _JUNYI_TIME_CANDS, "time/order")
        kc_map = (load_junyi_exercise_table(exercise_table_path)
                  if exercise_table_path else {})
        rows, dropped = [], Counter()
        for line in reader:
            try:
                user = (line.get(cu) or "").strip()
                ex = (line.get(ce) or "").strip()
                correct = _parse_junyi_correct(line.get(cc))
                tkey = _parse_junyi_time(line.get(ct))
            except (KeyError, TypeError, ValueError):
                dropped["unparseable"] += 1
                continue
            if not user or not ex:
                dropped["missing_id"] += 1
                continue
            if kc_map:
                if ex not in kc_map:
                    dropped["unmapped_exercise"] += 1
                    continue
                skill = kc_map[ex]
            else:
                skill = ex
            rows.append({"user": user, "skill": skill, "correct": correct,
                         "order": tkey})
    rows.sort(key=lambda r: (r["user"], r["order"]))
    for i, r in enumerate(rows):
        r["order"] = i  # canonical running order after sorting
    meta = {"columns": {"user": cu, "exercise": ce, "correct": cc, "time": ct},
            "skill_source": "kc_table" if kc_map else "exercise_id",
            "n_mapped_exercises": len(kc_map)}
    return rows, dict(dropped), meta

