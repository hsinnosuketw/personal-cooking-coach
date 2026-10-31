"""V-JEPA 2 ViT-L looks at 4 s of kitchen video and predicts the action 1 s ahead.

  python3 -m jepa.anticipate --spike                time one clip, print memory
  python3 -m jepa.anticipate                        all downloaded validation videos
  python3 -m jepa.anticipate --protocol repo --limit 20

The encoder turns the clip into latent tokens, the JEPA predictor imagines
the tokens of the next frames, and Meta's frozen EK100 probe reads both and
names the coming verb, noun and action. Results go to jepa/results/.
Run python3 -m jepa.fetch first.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
import types
from pathlib import Path

os.environ.setdefault("PYTORCH_ENABLE_MPS_FALLBACK", "1")

import cv2
import numpy as np
import pandas as pd
import torch
import yaml

from . import clips
from .vocab import class_maps

HERE = Path(__file__).parent
CACHE = HERE / "_cache"
RESULTS = HERE / "results"
REPO = CACHE / "vjepa2"


def _import_vendored():
    """Put the V-JEPA 2 repo on the path. Its model code only needs timm for
    drop_path, which is a no-op at inference, so a stub stands in for timm."""
    if "timm.models.layers" not in sys.modules:
        layers = types.ModuleType("timm.models.layers")
        layers.drop_path = lambda x, drop_prob=0.0, training=False: x
        sys.modules.update({"timm": types.ModuleType("timm"), "timm.models": types.ModuleType("timm.models"),
                            "timm.models.layers": layers})
    sys.path.insert(0, str(REPO))
    from evals.action_anticipation_frozen.models import init_classifier
    from evals.action_anticipation_frozen.modelcustom import vit_encoder_predictor_concat_ar as wrapper
    return init_classifier, wrapper


def load_model(device: torch.device):
    init_classifier, wrapper = _import_vendored()
    cfg = yaml.safe_load((REPO / "configs/inference/vitl/ek100.yaml").read_text())
    data, mk = cfg["experiment"]["data"], cfg["model_kwargs"]
    assert (data["frames_per_clip"], data["frames_per_second"], data["resolution"]) == (clips.FRAMES, clips.FPS, clips.CROP)
    import logging
    logging.getLogger().setLevel(logging.WARNING)
    import contextlib, io
    with contextlib.redirect_stdout(io.StringIO()):  # the repo prints the whole model
        model = wrapper.init_module(frames_per_clip=data["frames_per_clip"], frames_per_second=data["frames_per_second"],
                                    resolution=data["resolution"], checkpoint=str(CACHE / "vitl-enc-pred.pt"),
                                    model_kwargs=mk["pretrain_kwargs"], wrapper_kwargs=mk["wrapper_kwargs"])
    maps = class_maps(CACHE / "EPIC_100_train.csv")
    clf_cfg = cfg["experiment"]["classifier"]
    with contextlib.redirect_stdout(io.StringIO()):
        probe = init_classifier(embed_dim=model.embed_dim, num_heads=clf_cfg["num_heads"],
                                num_blocks=clf_cfg["num_probe_blocks"], device=torch.device("cpu"), num_classifiers=1,
                                action_classes=maps["actions"], verb_classes=maps["verbs"], noun_classes=maps["nouns"])[0]
    sd = torch.load(CACHE / "ek100-vitl-256.pt", map_location="cpu", weights_only=False)["classifiers"][0]
    probe.load_state_dict({k.removeprefix("module."): v for k, v in sd.items()})
    return model.eval().to(device), probe.eval().to(device), maps


def segments(maps: dict, only: set[str] | None = None) -> pd.DataFrame:
    """Validation segments of the videos on disk whose action the probe knows."""
    val = pd.read_csv(CACHE / "EPIC_100_validation.csv")
    val = val[[a in maps["actions"] for a in zip(val.verb_class, val.noun_class)]]
    have = {p.stem: p for p in (CACHE / "EPIC-KITCHENS").rglob("*.MP4") if not only or p.stem in only}
    return val[val.video_id.isin(have)].assign(path=lambda d: d.video_id.map(have)).sort_values(["video_id", "start_frame"])


def mean_class_recall(rows: list[dict], key: str) -> float | None:
    """EK100's anticipation metric: top-5 recall per ground-truth class, averaged over the classes present."""
    hits: dict[int, list[bool]] = {}
    for r in rows:
        hits.setdefault(r["truth"][key]["id"], []).append(r["truth"][key]["id"] in [p["id"] for p in r["top5"][key]])
    return round(100 * float(np.mean([np.mean(h) for h in hits.values()])), 1) if hits else None


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--protocol", choices=("strict", "repo"), default="strict")
    ap.add_argument("--limit", type=int, default=0, help="only the first N segments")
    ap.add_argument("--only-onion", action="store_true")
    ap.add_argument("--videos", default="", help="comma-separated video ids (default: every video on disk)")
    ap.add_argument("--tag", default="", help="suffix for the results file")
    ap.add_argument("--device", default="mps" if torch.backends.mps.is_available() else "cpu")
    ap.add_argument("--spike", action="store_true", help="time one clip and stop")
    args = ap.parse_args()
    device = torch.device(args.device)

    t0 = time.time()
    model, probe, maps = load_model(device)
    print(f"model loaded on {device} in {time.time() - t0:.0f}s")
    names = {"verb": pd.read_csv(CACHE / "EPIC_100_verb_classes.csv").key.to_dict(),
             "noun": pd.read_csv(CACHE / "EPIC_100_noun_classes.csv").key.to_dict()}
    inv = {"verb": {i: k for k, i in maps["verbs"].items()}, "noun": {i: k for k, i in maps["nouns"].items()},
           "action": {i: k for k, i in maps["actions"].items()}}

    def label(key: str, idx: int) -> str:
        c = inv[key][idx]
        return f"{names['verb'][c[0]]} {names['noun'][c[1]]}" if key == "action" else names[key][c]

    segs = segments(maps, set(filter(None, args.videos.split(","))))
    if args.only_onion:
        segs = segs[segs.noun.str.contains("onion")]
    if args.limit or args.spike:
        segs = segs.head(1 if args.spike else args.limit)
    if segs.empty:
        sys.exit("no segments: run python3 -m jepa.fetch first")
    thumbs = RESULTS / "thumbs"
    thumbs.mkdir(parents=True, exist_ok=True)

    rows, caps, timings = [], {}, []
    for n, s in enumerate(segs.itertuples(), 1):
        cap = caps.setdefault(s.video_id, cv2.VideoCapture(str(s.path)))
        vfps = cap.get(cv2.CAP_PROP_FPS)
        t1 = time.time()
        frames = clips.read_frames(cap, clips.frame_indices(s.start_frame, s.stop_frame, vfps, args.protocol))
        x = clips.to_tensor(frames).unsqueeze(0).to(device)
        t2 = time.time()
        with torch.no_grad():
            out = probe(model(x, torch.tensor([clips.ANTICIPATION_SEC], device=device)))
        out = {k: torch.sigmoid(v[0].float()).cpu() for k, v in out.items()}  # the probe was trained with sigmoid focal loss
        t3 = time.time()
        timings.append((t2 - t1, t3 - t2))
        thumb = f"{s.narration_id}-{args.protocol}.jpg"
        (thumbs / thumb).write_bytes(clips.keyframe_jpeg(frames))
        truth_ids = {"verb": maps["verbs"][s.verb_class], "noun": maps["nouns"][s.noun_class],
                     "action": maps["actions"][(s.verb_class, s.noun_class)]}
        rows.append({
            "narration_id": s.narration_id, "video_id": s.video_id, "narration": s.narration,
            "start": s.start_timestamp, "stop": s.stop_timestamp, "thumb": f"thumbs/{thumb}",
            "truth": {k: {"id": i, "name": label(k, i)} for k, i in truth_ids.items()},
            "top5": {k: [{"id": int(i), "name": label(k, int(i)), "p": round(float(p), 3)}
                         for p, i in zip(*v.topk(5))] for k, v in out.items()},
        })
        r = rows[-1]
        print(f"[{n}/{len(segs)}] {s.narration_id:<14} truth: {r['truth']['action']['name']:<22} "
              f"pred: {r['top5']['action'][0]['name']:<22} decode {t2 - t1:.1f}s model {t3 - t2:.1f}s", flush=True)

    if device.type == "mps":
        print(f"MPS memory: {torch.mps.driver_allocated_memory() / 1e9:.1f} GB")
    if args.spike:
        return
    onion = [r for r in rows if "onion" in r["truth"]["noun"]["name"]]
    summary = {
        "protocol": args.protocol, "device": args.device, "segments": len(rows), "videos": sorted(segs.video_id.unique()),
        "seconds_per_clip": {"decode": round(float(np.mean([t[0] for t in timings])), 2),
                             "model": round(float(np.median([t[1] for t in timings])), 2)},
        "mean_class_recall_at5": {k: mean_class_recall(rows, k) for k in ("verb", "noun", "action")},
        "onion_mean_class_recall_at5": {k: mean_class_recall(onion, k) for k in ("verb", "noun", "action")},
        "onion_segments": len(onion),
        "chance_at5": {"verb": round(500 / 97, 1), "noun": round(500 / 289, 1), "action": round(500 / 3568, 2)},
    }
    out = RESULTS / f"ek100_{args.protocol}{'_' + args.tag if args.tag else ''}.json"
    out.write_text(json.dumps({"summary": summary, "rows": rows}, indent=1), encoding="utf-8")
    print(json.dumps(summary, indent=1))
    print(f"wrote {out}")


if __name__ == "__main__":
    main()
