"""Recipe step graphs and the six skill IDs they share (plan B01-B04)."""
from __future__ import annotations

import json
import pathlib
from functools import lru_cache

SKILLS = {
    "knife_cut": "切法（大小一致）",
    "salt_timing": "加鹽時機",
    "heat_control": "火力控制",
    "moisture": "水分管理",
    "target_state": "判斷目標狀態",
    "step_judgment": "判斷何時進下一步",
}
RECIPE_DIR = pathlib.Path(__file__).with_name("recipes")


@lru_cache(maxsize=None)
def load(recipe_id: str) -> dict:
    data = json.loads((RECIPE_DIR / f"{recipe_id}.json").read_text(encoding="utf-8"))
    for s in data["steps"]:
        unknown = set(s["skills"]) - set(SKILLS)
        if unknown:
            raise ValueError(f"{recipe_id}/{s['step_id']}: unknown skills {sorted(unknown)}")
    return data


def available() -> list[str]:
    return sorted(p.stem for p in RECIPE_DIR.glob("*.json"))


def step(recipe_id: str, step_id: str) -> dict:
    for s in load(recipe_id)["steps"]:
        if s["step_id"] == step_id:
            return s
    raise KeyError(f"{recipe_id} has no step {step_id!r}")


def first_step_id(recipe_id: str) -> str:
    return load(recipe_id)["steps"][0]["step_id"]


def next_step_id(recipe_id: str, step_id: str) -> str | None:
    ids = [s["step_id"] for s in load(recipe_id)["steps"]]
    i = ids.index(step_id)
    return ids[i + 1] if i + 1 < len(ids) else None
