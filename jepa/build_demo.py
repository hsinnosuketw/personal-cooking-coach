"""Collect the demo's videos, frames and data next to jepa/demo/index.html.

  python3 -m jepa.build_demo        then open jepa/demo/index.html (double-click works)

Reads jepa/results/demo/ (rendered videos + scores from Colab, frames/,
extraction.json) and jepa/results/ek100_strict.json, and writes
jepa/demo/data.js plus copies of the media. The page needs no server.
"""
from __future__ import annotations

import json
import shutil
from pathlib import Path

HERE = Path(__file__).parent
RES = HERE / "results"
SRC = RES / "demo"
OUT = HERE / "demo"

VIDEOS = [
    ("hdepic", "Steps from HD-EPIC annotations", "guide_P08_hdepic",
     "Recipe steps from HD-EPIC's annotators. Played at 4x; the picture freezes on each NEXT STEP decision. "
     "Green 'annotated' marks the step the annotators recorded at that moment."),
    ("nim", "Steps written by the NIM VLM", "guide_P08_nim",
     "Same predictions, but the recipe steps and their action tags were written by Llama 3.2 90B Vision on NVIDIA NIM."),
]


def main() -> None:
    OUT.mkdir(exist_ok=True)
    videos = []
    for key, label, stem, note in VIDEOS:
        mp4 = SRC / f"{stem}.mp4"
        if not mp4.exists():
            continue
        shutil.copy2(mp4, OUT / mp4.name)
        score = SRC / f"{stem}.json"
        videos.append({"key": key, "label": label, "file": mp4.name, "note": note,
                       "eval": json.loads(score.read_text()) if score.exists() else {}})
    if (OUT / "frames").exists():
        shutil.rmtree(OUT / "frames")
    shutil.copytree(SRC / "frames", OUT / "frames")
    frames = json.loads((SRC / "frames" / "frames.json").read_text(encoding="utf-8"))

    ek = json.loads((RES / "ek100_strict.json").read_text(encoding="utf-8"))
    onion = [r for r in ek["rows"] if "onion" in r["truth"]["noun"]["name"]]
    (OUT / "ek").mkdir(exist_ok=True)
    rows = []
    for r in onion[:16]:
        name = Path(r["thumb"]).name
        shutil.copy2(RES / r["thumb"], OUT / "ek" / name)
        rows.append(dict(r, thumb=f"ek/{name}"))

    data = {"videos": videos, "extraction": json.loads((SRC / "extraction.json").read_text(encoding="utf-8")),
            "frames": frames, "ek": {"summary": ek["summary"], "rows": rows}}
    (OUT / "data.js").write_text("window.DEMO = " + json.dumps(data, ensure_ascii=False) + ";\n", encoding="utf-8")
    print(f"built {OUT}/index.html: {len(videos)} videos, {len(frames['frames'])} frames, {len(rows)} EPIC examples")


if __name__ == "__main__":
    main()
