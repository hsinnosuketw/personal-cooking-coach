"""Where things live. Modules take their default paths from here; a path passed as an argument always wins."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]      # the repo (on Colab: where the notebook unpacked its bundle)
DATA_RAW = ROOT / "data" / "raw"                # downloads as fetched: videos, annotations, weights, vendored repos
DATA_PROCESSED = ROOT / "data" / "processed"    # derived inputs: per-second predictions, step tags, task graphs
RESULTS = ROOT / "results"                      # run outputs and rendered videos
SITE = ROOT / "site"                            # the demo page and its built data and media
