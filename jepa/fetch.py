"""Download what the EPIC-KITCHENS anticipation demo needs into jepa/_cache/.

  python3 -m jepa.fetch            code, labels, probe, slimmed ViT-L weights, 4 videos
  python3 -m jepa.fetch --videos P28_15,P04_28   pick other validation videos
  python3 -m jepa.fetch --annotations-only        EK100 labels + HD-EPIC recipes only

Every step skips work already done and refuses to start a download that
would leave less than 4 GB free on the disk.
"""
from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
import urllib.request
from pathlib import Path

CACHE = Path(__file__).parent / "_cache"
VJEPA_REPO = "https://github.com/facebookresearch/vjepa2.git"
EPIC_DL_REPO = "https://github.com/epic-kitchens/epic-kitchens-download-scripts.git"
ANNOT = "https://raw.githubusercontent.com/epic-kitchens/epic-kitchens-100-annotations/master/"
ANNOT_FILES = ("EPIC_100_train.csv", "EPIC_100_validation.csv", "EPIC_100_verb_classes.csv",
               "EPIC_100_noun_classes.csv", "EPIC_100_video_info.csv")
PROBE_URL = "https://dl.fbaipublicfiles.com/vjepa2/evals/ek100-vitl-256.pt"
VITL_URL = "https://dl.fbaipublicfiles.com/vjepa2/vitl.pt"
# Shortest validation videos with onion actions (see jepa/README.md).
VIDEOS = ("P28_15", "P04_28", "P26_35", "P28_16")
MIN_FREE_GB = 4
HD_ANNOT = "https://raw.githubusercontent.com/hd-epic/hd-epic-annotations/main/"
HD_FILES = ("high-level/complete_recipes.json", "narrations-and-action-segments/HD_EPIC_Narrations.pkl",
            "narrations-and-action-segments/HD_EPIC_verb_classes.csv",
            "narrations-and-action-segments/HD_EPIC_noun_classes.csv")


def free_gb() -> float:
    return shutil.disk_usage(CACHE).free / 1e9


def download(url: str, dest: Path, size_gb: float = 0.0) -> Path:
    if dest.exists():
        return dest
    if free_gb() - size_gb < MIN_FREE_GB:
        sys.exit(f"not enough disk for {dest.name}: {free_gb():.1f} GB free, needs {size_gb:.1f} + {MIN_FREE_GB}")
    print(f"downloading {url} ({size_gb:.2f} GB)", flush=True)
    part = dest.with_suffix(dest.suffix + ".part")
    with urllib.request.urlopen(url) as r, open(part, "wb") as f:
        shutil.copyfileobj(r, f, 1 << 22)
    part.rename(dest)
    return dest


def clone(url: str, dest: Path) -> str:
    if not dest.exists():
        subprocess.run(["git", "clone", "--depth", "1", "-q", url, str(dest)], check=True)
    return subprocess.run(["git", "-C", str(dest), "rev-parse", "HEAD"], capture_output=True,
                          text=True, check=True).stdout.strip()


def slim_vitl() -> Path:
    """Keep only the encoder and predictor (~1.3 GB) out of the 5.1 GB training checkpoint."""
    slim = CACHE / "vitl-enc-pred.pt"
    if slim.exists():
        return slim
    full = download(VITL_URL, CACHE / "vitl.pt", 5.13)
    import torch
    ckpt = torch.load(full, map_location="cpu", mmap=True, weights_only=False)
    torch.save({k: ckpt[k] for k in ("target_encoder", "predictor")}, slim)
    del ckpt
    full.unlink()
    return slim


def fetch_videos(ids: list[str]) -> None:
    dl = CACHE / "epic-dl"
    clone(EPIC_DL_REPO, dl)
    have = {p.stem for p in (CACHE / "EPIC-KITCHENS").rglob("*.MP4")}
    missing = [v for v in ids if v not in have]
    if missing:
        if free_gb() < MIN_FREE_GB + 3:
            sys.exit(f"not enough disk for videos: {free_gb():.1f} GB free")
        subprocess.run([sys.executable, "epic_downloader.py", "--videos", "--specific-videos", ",".join(missing),
                        "--output-path", str(CACHE.resolve())], cwd=dl, check=True)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--videos", default=",".join(VIDEOS))
    ap.add_argument("--annotations-only", action="store_true", help="labels and recipes only (no weights, no video)")
    args = ap.parse_args()
    CACHE.mkdir(exist_ok=True)
    print("vjepa2 commit", clone(VJEPA_REPO, CACHE / "vjepa2"))
    for name in ANNOT_FILES:
        download(ANNOT + name, CACHE / name)
    (CACHE / "hd-epic").mkdir(exist_ok=True)
    for name in HD_FILES:
        download(HD_ANNOT + name, CACHE / "hd-epic" / Path(name).name)
    if args.annotations_only:
        return
    download(PROBE_URL, CACHE / "ek100-vitl-256.pt", 0.21)
    slim_vitl()
    fetch_videos(args.videos.split(","))
    print(f"done; {free_gb():.1f} GB free")


if __name__ == "__main__":
    main()
