"""Build jepa/pipeline.ipynb: the whole guide, one stage per cell, runnable on a Colab GPU.

  python3 -m jepa.make_notebook

The notebook carries the jepa/ source (zipped, base64) inside its setup
cell, so a fresh Colab server needs no git clone or upload: run the
notebook from VS Code with the Colab kernel and the setup cell unpacks the
code into /content/coach. Rebuild after changing any jepa/*.py, or the
notebook keeps running the old copy. Run locally, it uses the repo as is.
"""
from __future__ import annotations

import base64
import io
import json
import zipfile
from pathlib import Path

HERE = Path(__file__).parent
SKIP = {"make_notebook.py", "serve_demo.py"}
EXTRA = ["results/nim_hand_P08_R03.json"]  # the VLM tags the demo page uses, for runs without an API key

CELLS: list[tuple[str, str]] = [
    ("md", """# V-JEPA 2 烹飪導引：逐段執行

每一段的**輸入 → 輸出**都寫在段落開頭，可以單獨重跑任何一段來檢查中間結果。

| 段 | 做什麼 | 需要 GPU |
|---|---|---|
| 1 | 環境設定（解開程式碼、確認 GPU） | |
| 2 | 參數 | |
| 3 | 下載標註、權重、影片 | |
| 4 | 載入 World Model（encoder + predictor）與 Probe | ✓ |
| 5 | 解剖一個時間點：影片 → latent state → 預測的 state → 動詞/名詞 | ✓ |
| 6 | 整部影片每秒預測一次，存成 `.npz` | ✓ |
| 7 | 食譜步驟（HD-EPIC 原文） | |
| 8 | VLM 為每一步寫手部動作標籤 | |
| 9 | Action Bank：把標籤變成矩陣 | |
| 10 | Step Tracker：每秒判斷目前步驟、計算準確率 | |
| 11 | 檢查單一秒的 Tracker 計算 | |
| 12 | （選用）渲染導引影片 | |

**在 VS Code 連上 Colab GPU**：安裝 Google Colab 擴充套件 → 右上角 *Select Kernel* → *Colab* → *New Colab Server* → 選 GPU（T4）。
T4 約 1.15 compute units/小時，用完記得在 Colab 擴充套件裡關掉 server。
第 7–11 段只需要第 6 段的 `.npz`，不需要 GPU。"""),
    ("md", """## 1. 環境設定
**輸入**：這一格最長那一行 `BUNDLE`（壓縮過的 jepa/ 程式碼，不用看）。**輸出**：`/content/coach/jepa/`（Colab）或直接用這個 repo（本機）；`DEVICE`。"""),
    ("code", """import base64, io, os, sys, zipfile
from pathlib import Path

def unpack(bundle: str) -> Path:
    \"\"\"On Colab, unzip this notebook's copy of jepa/ into /content/coach; locally, use the repo.\"\"\"
    if not Path("/content").is_dir():
        return Path.cwd() if (Path.cwd() / "jepa").is_dir() else Path.cwd().parent
    root = Path("/content/coach")
    with zipfile.ZipFile(io.BytesIO(base64.b64decode(bundle))) as zf:
        zf.extractall(root)  # always refresh the code from this notebook
    return root

BUNDLE_LINE
ROOT = unpack(BUNDLE)
ON_COLAB = ROOT == Path("/content/coach")
os.chdir(ROOT)  # the Colab kernel may start later cells back in /content, so paths below are absolute
sys.path.insert(0, str(ROOT))

try:
    import torch
    DEVICE = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    gpu = torch.cuda.get_device_name(0) if DEVICE.type == "cuda" else "none"
    print(f"torch {torch.__version__}, device {DEVICE}, GPU: {gpu}")
except Exception as e:  # stages 7-11 still run without torch
    torch, DEVICE = None, None
    print("no torch here:", e)
print("working in", ROOT)"""),
    ("md", """## 2. 參數
改這裡就能換影片或只跑前幾分鐘（`END = 120`）。HD-EPIC 的影片 id 與食譜 id 對照在 `complete_recipes.json`。"""),
    ("code", """VIDEO_ID = "P08-20240614-085000"   # HD-EPIC video
RECIPE = "P08_R03"                  # Scrambled Eggs, 7 steps
STRIDE = 1.0                        # seconds between predictions
END = None                          # stop after this many seconds (None = whole video)
BATCH = 4                           # clips per GPU call
T_INSPECT = 300.0                   # the moment stage 5 and 11 look at

VIDEO = ROOT / "jepa/_cache/hd-epic" / f"{VIDEO_ID}.mp4"
PRED = ROOT / "jepa/results" / f"{VIDEO_ID}{'' if END is None else f'_to{int(END)}'}.npz"
PRED.parent.mkdir(parents=True, exist_ok=True)"""),
    ("md", """## 3. 下載
**輸入**：網址。**輸出**：`jepa/_cache/` 裡的
- EPIC-KITCHENS 類別表、HD-EPIC 食譜與標註（幾 MB）
- Probe `ek100-vitl-256.pt`（0.2 GB，Meta）
- World Model 權重：下載 5.1 GB 的 `vitl.pt`，只留 encoder + predictor → `vitl-enc-pred.pt`（1.3 GB）
- 影片（P08 約 0.7 GB，從 Bristol 大學 8 條連線平行下載，約 10 分鐘）

已存在的檔案會跳過。下載不吃 GPU，但 server 開著就會計 compute units。"""),
    ("code", """from jepa import fetch
fetch.prepare(videos=[], hd_video=VIDEO_ID)"""),
    ("md", """## 4. 載入 World Model 與 Probe
**輸入**：權重檔。**輸出**：`model`（V-JEPA 2 ViT-L encoder + predictor）、`probe`（Meta 在 EPIC-KITCHENS-100 上訓練的分類器）。"""),
    ("code", """from jepa.anticipate import load_model
from jepa import clips

model, probe, maps = load_model(DEVICE)
millions = lambda m: sum(p.numel() for p in m.parameters()) / 1e6
print(f"encoder {millions(model.encoder):.0f}M, predictor {millions(model.predictor):.0f}M, probe {millions(probe):.0f}M parameters")
print(f"probe outputs: {len(maps['verbs'])} verbs, {len(maps['nouns'])} nouns, {len(maps['actions'])} actions")"""),
    ("md", """## 5. 解剖一個時間點
**輸入**：`T_INSPECT` 之前的 32 張 frame。**輸出**：
1. encoder 的 latent state（現在）
2. predictor 想像的未來 latent state
3. Probe 把兩者轉成動詞、名詞、動作機率

最後一格比較：只給 Probe「現在」的 state（不用 predictor）時，答案有沒有不同；以及 HD-EPIC 標註者記錄的真實動作。"""),
    ("code", """import cv2, numpy as np
import matplotlib.pyplot as plt

cap = cv2.VideoCapture(str(VIDEO))
fps = cap.get(cv2.CAP_PROP_FPS)
step = int(fps / clips.FPS)                       # 30 fps video -> every 3rd frame
end_frame = int(T_INSPECT * fps)
idx = np.clip(np.arange(end_frame - clips.FRAMES * step, end_frame, step), 0, None)
frames = clips.read_frames(cap, idx)
x = clips.to_tensor(frames).unsqueeze(0).to(DEVICE)   # [1, 3, 32, 256, 256]
span = clips.FRAMES * step / fps
ahead = clips.ANTICIPATION_SEC * clips.FPS * step / fps  # the predictor counts in 8 fps steps
print(f"video {fps:.0f} fps; the model sees {clips.FRAMES} frames over the last {span:.1f} s "
      f"({T_INSPECT - span:.1f}-{T_INSPECT:.1f} s) and imagines ~{ahead:.1f} s past the last one")
print("input tensor", tuple(x.shape))

fig, ax = plt.subplots(1, 8, figsize=(16, 2.4))
for a, i in zip(ax, range(0, clips.FRAMES, 4)):
    a.imshow(frames[i]); a.set_title(f"{idx[i] / fps:.1f}s", fontsize=9); a.axis("off")
plt.show()"""),
    ("code", """with torch.no_grad():
    z = model(x, torch.tensor([clips.ANTICIPATION_SEC], device=DEVICE))
n_pred = model.grid_size ** 2 * (model.num_output_frames // model.tubelet_size)
z_now, z_future = z[:, :-n_pred], z[:, -n_pred:]
print("model output      ", tuple(z.shape), "= encoder tokens + predicted tokens")
print("state now (encoder)", tuple(z_now.shape), f"= {clips.FRAMES // model.tubelet_size} time slices x {model.grid_size}x{model.grid_size} patches")
print("predicted state    ", tuple(z_future.shape), "= one future time slice")"""),
    ("code", """import pandas as pd
from jepa.vocab import Vocab
from jepa.guide_video import action_names
from jepa.extractors import HDEpicExtractor

vocab = Vocab.load()
hd = HDEpicExtractor(vocab)
NAMES = {"verb": sorted(vocab.verb_row, key=vocab.verb_row.get),
         "noun": sorted(vocab.noun_row, key=vocab.noun_row.get), "action": action_names()}

def read(tokens):
    with torch.no_grad():
        return {k: torch.sigmoid(v[0].float()).cpu().numpy() for k, v in probe(tokens).items()}

def top5(p, kind):
    return ", ".join(f"{NAMES[kind][j]} {p[j]:.2f}" for j in np.argsort(-p)[:5])

with_pred, now_only = read(z), read(z_now)
display(pd.DataFrame({"now + predicted (what the guide uses)": [top5(with_pred[k], k) for k in NAMES],
                      "now only (no predictor)": [top5(now_only[k], k) for k in NAMES]}, index=list(NAMES)))

narr = hd.narr[hd.narr.video_id == VIDEO_ID]
t_true = T_INSPECT + ahead
now = narr[(narr.start_timestamp <= t_true) & (narr.end_timestamp >= t_true)]
print(f"HD-EPIC narration at {t_true:.1f} s:", "; ".join(now.narration) or "(nothing annotated)")"""),
    ("md", """## 6. 整部影片：每秒一次預測
**輸入**：影片。**輸出**：`PRED`（`.npz`）：`t`（每次預測的時間）、`verb [T, 97]`、`noun [T, 289]`、`action [T, 3568]` 機率。

影片從頭到尾解碼一次，保留最近 32 張 frame，每 `STRIDE` 秒送一次進模型。T4 上整部 P08（877 秒）約 30 分鐘。已有檔案就直接讀取；要重算請把 `RERUN` 設成 `True`。"""),
    ("code", """from jepa import precompute
RERUN = False
if RERUN or not PRED.exists():
    precompute.run(VIDEO, PRED, STRIDE, DEVICE, BATCH, END)
pred = dict(np.load(PRED))
print({k: v.shape for k, v in pred.items() if k != "fps"})
display(pd.DataFrame({"t": pred["t"][:8].round(1),
                      "top verb": [NAMES["verb"][j] for j in pred["verb"][:8].argmax(1)],
                      "top noun": [NAMES["noun"][j] for j in pred["noun"][:8].argmax(1)],
                      "top action": [NAMES["action"][j] for j in pred["action"][:8].argmax(1)]}))"""),
    ("md", """## 7. 食譜步驟
**輸入**：HD-EPIC 的 `complete_recipes.json`。**輸出**：`texts`，也就是食譜原文的步驟。沒有用到模型。

（第 7–11 段不需要 GPU。只要有第 6 段的 `.npz`，本機也能跑。本機要先跑第 1、2 段，以及第 5 段第三格裡載入 `vocab` / `hd` / `NAMES` 的部分。）"""),
    ("code", """if "hd" not in globals():  # stage 5 was skipped (e.g. running locally without torch)
    import numpy as np, pandas as pd
    import matplotlib.pyplot as plt
    from jepa.vocab import Vocab
    from jepa.guide_video import action_names
    from jepa.extractors import HDEpicExtractor
    vocab = Vocab.load()
    hd = HDEpicExtractor(vocab)
    NAMES = {"verb": sorted(vocab.verb_row, key=vocab.verb_row.get),
             "noun": sorted(vocab.noun_row, key=vocab.noun_row.get), "action": action_names()}
    pred = dict(np.load(PRED))

hd_steps = hd.extract_steps(RECIPE)
texts = [s.text for s in hd_steps]
name = hd.recipes[RECIPE]["name"]
print(name)
for k, t in enumerate(texts, 1):
    print(f"{k}. {t}")"""),
    ("md", """## 8. VLM：每一步的手部動作標籤
**輸入**：菜名 + 第 7 段的步驟文字（**不看影片**）。**輸出**：`steps`，每一步 3–6 組 Probe 認得的「動詞 名詞」。

- `USE_VLM = True`：呼叫 NVIDIA NIM 上的 Llama 3.2 90B Vision（約 30–120 秒），需要 `NVIDIA_API_KEY`（會跳出輸入框，不會存進 notebook）。
- `USE_VLM = False`：讀取 demo 頁使用的那份結果（只適用 P08_R03）。"""),
    ("code", """import getpass, json
from jepa.extractors import ManualRecipeExtractor, NIMRecipeExtractor
from jepa.vocab import class_frequencies

USE_VLM = False
SAVED = ROOT / "jepa/results/nim_hand_P08_R03.json"
if USE_VLM:
    if not os.environ.get("NVIDIA_API_KEY"):
        env = ROOT / ".env"
        line = [l for l in env.read_text().splitlines() if l.startswith("NVIDIA_API_KEY=")] if env.exists() else []
        os.environ["NVIDIA_API_KEY"] = line[0].split("=", 1)[1].strip() if line else getpass.getpass("NVIDIA_API_KEY: ")
    vlm = NIMRecipeExtractor(vocab, hand_level=True, frequencies=class_frequencies())
    steps = vlm.tag_steps(name, texts)
    print("synonyms rewritten:", [f"{a} -> {b}" for _, a, b in vlm.mapped])
    print("dropped (not in the probe's vocabulary):", vlm.rejected)
    STEPS_JSON = ROOT / f"jepa/results/steps_{RECIPE}.json"
    STEPS_JSON.write_text(json.dumps({"aligned_to": RECIPE, "steps": [
        {"id": s.step_id, "text": s.text, "pairs": [[v, n] for v, n, _ in s.pairs]} for s in steps]}, indent=1))
else:
    STEPS_JSON = SAVED
    steps = ManualRecipeExtractor(vocab).extract_steps(str(SAVED))
for s in steps:
    print(f"{s.order + 1}. " + ", ".join(f"{v} {n}" for v, n, _ in s.pairs))"""),
    ("md", """## 9. Action Bank
**輸入**：`steps`。**輸出**：兩個矩陣 `V [步驟數, 97]`、`Nn [步驟數, 289]`：每一步的動詞、名詞分布（各列加總為 1，另外均勻分 2% 給所有詞，避免沒列到的詞讓分數歸零）。"""),
    ("code", """from jepa.action_bank import ActionBankRepository
bank = ActionBankRepository(vocab).from_steps(steps)
V, Nn = bank.get_batched_embeddings()
print("V", V.shape, " Nn", Nn.shape)
for k in range(len(steps)):
    tv = ", ".join(f"{NAMES['verb'][j]} {V[k, j]:.2f}" for j in np.argsort(-V[k])[:3])
    tn = ", ".join(f"{NAMES['noun'][j]} {Nn[k, j]:.2f}" for j in np.argsort(-Nn[k])[:3])
    print(f"step {k + 1}: verbs {tv} | nouns {tn}")"""),
    ("md", """## 10. Step Tracker
**輸入**：第 6 段的每秒預測 + 第 9 段的矩陣。**輸出**：每秒的「目前步驟」，以及和 HD-EPIC 標註比較的準確率。

每秒：
1. 比對分數 = log(預測動詞 · V) + log(預測名詞 · Nn)
2. 加上 0.3 × 順序先驗（留在原步驟 0.45，下一步 0.35）
3. softmax
4. 新步驟領先 0.15 以上、連續 2 秒才切換

準確率的算法：每一秒，把 Tracker 認為的步驟，和標註中 1 秒後正在進行的步驟比較。只計算有標註步驟的秒數。下面同時列出用 HD-EPIC 標註當標籤的版本當參考（偏樂觀，因為標籤來自同一部影片）。"""),
    ("code", """from jepa.guide_video import evaluate, replay, truth_steps
truth = truth_steps(hd, RECIPE, VIDEO_ID)
results = replay(bank, pred)
current = np.array([r.extras["current"] for r in results])
ref = replay(ActionBankRepository(vocab).from_steps(hd_steps), pred)
display(pd.DataFrame({"these steps (stage 8)": evaluate(results, pred["t"], truth, len(steps)),
                      "HD-EPIC annotated tags (reference)": evaluate(ref, pred["t"], truth, len(steps))}))

fig, ax = plt.subplots(figsize=(16, 2.6))
colours = plt.cm.tab10(np.arange(len(steps)))
for k, s0, s1 in truth:
    ax.broken_barh([(s0, s1 - s0)], (1.1, 0.8), color=colours[k])
for k in range(len(steps)):
    on = current == k
    ax.scatter(pred["t"][on], np.full(on.sum(), 0.5), color=colours[k], s=6, marker="s", label=f"step {k + 1}")
ax.set_yticks([0.5, 1.5], ["tracker", "annotated"]); ax.set_xlabel("seconds")
ax.legend(ncol=len(steps), fontsize=8, loc="upper center", bbox_to_anchor=(0.5, -0.35))
plt.show()"""),
    ("md", """## 11. 檢查單一秒
**輸入**：`T_INSPECT` 那一秒的預測。**輸出**：每一步的比對分數、順序先驗、最後的機率，以及 Tracker 的決定。"""),
    ("code", """from jepa.scorer import PRIOR_WEIGHT, match_scores, order_prior, softmax
i = int(np.searchsorted(pred["t"], T_INSPECT))
prev = int(current[i - 1]) if i else -1
m = match_scores(bank, pred["verb"][i:i + 1].astype(float), pred["noun"][i:i + 1].astype(float))[0]
prior = PRIOR_WEIGHT * order_prior(len(steps), prev)
display(pd.DataFrame({"step": [s.text[:60] for s in steps], "match": m.round(2), "prior x0.3": prior.round(2),
                      "posterior": softmax(m + prior).round(3)}, index=range(1, len(steps) + 1)))
print(f"t = {pred['t'][i]:.1f}s, step before: {prev + 1 or 'not started'}, tracker now: {current[i] + 1}, "
      f"annotated 1 s later: {sorted(k + 1 for k, s0, s1 in truth if s0 <= pred['t'][i] + 1 <= s1) or 'none'}")"""),
    ("md", """## 12. （選用）渲染導引影片
**輸入**：影片、`PRED`、`STEPS_JSON`。**輸出**：MP4（`RENDER_END` 秒為止）。渲染只用 CPU，本機（Mac）比 Colab 快約 5 倍；
可以先把 `PRED` 的 `.npz`（約 6 MB）帶回本機再渲染。"""),
    ("code", """from jepa import guide_video
RENDER_END = 120
out = ROOT / f"jepa/results/guide_{VIDEO_ID}_to{RENDER_END}.mp4"
print(guide_video.render(VIDEO, PRED, RECIPE, out, 1.0, STEPS_JSON, None, RENDER_END))
print("wrote", out)"""),
]


def bundle() -> str:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        for p in sorted(HERE.glob("*.py")):
            if p.name not in SKIP:
                z.write(p, f"jepa/{p.name}")
        for rel in EXTRA:
            if (HERE / rel).exists():
                z.write(HERE / rel, f"jepa/{rel}")
    return base64.b64encode(buf.getvalue()).decode()


def cell(n: int, kind: str, src: str) -> dict:
    lines = src.splitlines(keepends=True)
    if kind == "md":
        return {"cell_type": "markdown", "id": f"c{n:02d}", "metadata": {}, "source": lines}
    if "BUNDLE_LINE" in src:
        lines = src.replace("BUNDLE_LINE", f'BUNDLE = "{bundle()}"  # jepa/ zipped; python3 -m jepa.make_notebook rebuilds it').splitlines(keepends=True)
    return {"cell_type": "code", "id": f"c{n:02d}", "execution_count": None, "metadata": {}, "outputs": [], "source": lines}


def main() -> None:
    nb = {"cells": [cell(n, k, s) for n, (k, s) in enumerate(CELLS)], "nbformat": 4, "nbformat_minor": 5,
          "metadata": {"kernelspec": {"name": "python3", "display_name": "Python 3", "language": "python"},
                       "language_info": {"name": "python"}}}
    out = HERE / "pipeline.ipynb"
    out.write_text(json.dumps(nb, indent=1, ensure_ascii=False), encoding="utf-8")
    print(f"wrote {out} ({out.stat().st_size / 1e3:.0f} kB)")


if __name__ == "__main__":
    main()
