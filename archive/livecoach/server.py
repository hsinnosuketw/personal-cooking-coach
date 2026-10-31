"""HTTP API and page for the live coach (plan D01, D03, D04, D12; G01-G08).

  python3 -m livecoach.server [--port 8100] [--provider mock|meta[:model]]

Serves coach.html plus a small JSON API. Sessions live in memory; each one
also appends a JSONL log under livecoach/runs/ (git-ignored) for export and
replay. The provider defaults to the offline mock, so it runs without a key.
"""
from __future__ import annotations

import argparse
import pathlib
import time

import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel

from . import recipes
from .evaluate import make_provider
from .schema import Decision, KitchenState, LearnerResponse, ObservationEvent, SkillBelief, WMPrediction
from .session import Session

HERE = pathlib.Path(__file__).parent
app = FastAPI(title="Live cooking coach")
SESSIONS: dict[str, Session] = {}
PROVIDER = "mock"


class NewSession(BaseModel):
    learner_id: str = "demo-learner"
    recipe_id: str = "pasta_pomodoro"
    memory: bool = True


class SwitchRecipe(BaseModel):
    recipe_id: str


def _session(sid: str) -> Session:
    if sid not in SESSIONS:
        raise HTTPException(404, f"no session {sid}")
    return SESSIONS[sid]


def _new(learner_id: str, recipe_id: str, memory: bool) -> dict:
    if recipe_id not in recipes.available():
        raise HTTPException(400, f"unknown recipe {recipe_id}")
    s = Session(learner_id, recipe_id, make_provider(PROVIDER), memory=memory, log_dir=str(HERE / "runs"))
    SESSIONS[s.session_id] = s
    return s.snapshot()


@app.get("/")
def page():
    return FileResponse(HERE / "coach.html", media_type="text/html; charset=utf-8")


@app.get("/api/recipes")
def all_recipes():
    return {rid: recipes.load(rid) for rid in recipes.available()}


@app.get("/api/schema")
def schema():
    """JSON Schema of the shared contracts (plan B10), for front ends and tests."""
    return {m.__name__: m.model_json_schema() for m in
            (ObservationEvent, KitchenState, SkillBelief, WMPrediction, Decision, LearnerResponse)}


@app.post("/api/sessions")
def create(body: NewSession):
    return _new(body.learner_id, body.recipe_id, body.memory)


@app.get("/api/sessions/{sid}")
def snapshot(sid: str):
    return _session(sid).snapshot()


@app.post("/api/sessions/{sid}/events")
def event(sid: str, ev: ObservationEvent):
    s = _session(sid)
    try:
        s.observe(ev)
    except KeyError as e:
        raise HTTPException(400, str(e))
    return s.snapshot()


@app.post("/api/sessions/{sid}/responses")
def respond(sid: str, r: LearnerResponse):
    s = _session(sid)
    s.respond(r)
    return s.snapshot()


@app.post("/api/sessions/{sid}/recipe")
def switch(sid: str, body: SwitchRecipe):
    s = _session(sid)
    if body.recipe_id not in recipes.available():
        raise HTTPException(400, f"unknown recipe {body.recipe_id}")
    s.switch_recipe(body.recipe_id, time.time())
    return s.snapshot()


@app.post("/api/sessions/{sid}/reset")
def reset(sid: str):
    """Clean reset (plan D12): a fresh session for the same learner, no memory kept."""
    old = SESSIONS.pop(sid, None) or _session(sid)
    return _new(old.learner_id, old.state.recipe_id, old.memory)


@app.get("/api/sessions/{sid}/export")
def export(sid: str):
    s = _session(sid)
    return {"snapshot": s.snapshot(), "decisions": [d.model_dump() for d in s.decisions],
            "trace": s.trace, "log": str(s.log_path) if s.log_path else None}


def main() -> None:
    global PROVIDER
    ap = argparse.ArgumentParser(description="Serve the live cooking coach.")
    ap.add_argument("--port", type=int, default=8100)
    ap.add_argument("--host", default="127.0.0.1")
    ap.add_argument("--provider", default="mock", help="mock (offline) or meta[:model] (needs MODEL_API_KEY)")
    args = ap.parse_args()
    PROVIDER = args.provider
    print(f"live coach on http://{args.host}:{args.port}/  (provider: {PROVIDER})")
    uvicorn.run(app, host=args.host, port=args.port, log_level="warning")


if __name__ == "__main__":
    main()
