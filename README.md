# Cooking guide on a V-JEPA 2 world model

A coach that watches someone cook, predicts their next action about 1 s
ahead with Meta's V-JEPA 2 world model, and tells them which recipe step
comes next. Built for the Meta Global AI Developer Hackathon.

Everything lives in `jepa/`. The earlier work (the POMDP benchmark, the 3D
kitchen duel, the onion game, the live-coach prototype) is in `archive/`
and still runs from there (`cd archive && python3 test_chef.py`).

## How it works

```
recipe text ─► VLM on NVIDIA NIM ─► action tags per step ─┐
                                                          ├─► step tracker ─► current step / NEXT STEP
cooking video ─► V-JEPA 2 ViT-L ─► EK100 probe ───────────┘
                 (latent, ~1 s ahead)  (verb/noun/action probabilities)
```

| Layer | Code | Source |
|---|---|---|
| World model: encoder + predictor, imagines the next ~1 s in latent space | `anticipate.py`, `precompute.py`, `clips.py` | Meta V-JEPA 2 ViT-L weights (MIT) |
| Probe: latent -> 97 verbs, 289 nouns, 3568 actions | vendored from `facebookresearch/vjepa2` | Meta, trained on EPIC-KITCHENS-100 |
| Recipe -> steps + action tags | `extractors.py` (HD-EPIC, hand-written JSON, NIM VLM) | Llama 3.2 90B Vision on NVIDIA NIM |
| VLM words -> probe classes | `vocab.py` (class names, EPIC synonym lists, plurals, head noun) | EPIC-KITCHENS class tables |
| Step tracker: scores every step against the prediction, pauses on a change | `action_bank.py`, `scorer.py` | ours, hand-set parameters |
| Demo video and page | `guide_video.py`, `demo_frames.py`, `build_demo.py`, `demo/index.html` | ours |

## Run it

```bash
pip install -r requirements.txt
python3 test_jepa.py                         # 9 tests, no torch or network
python3 -m jepa.fetch --annotations-only     # EPIC-KITCHENS + HD-EPIC labels and recipes
python3 -m jepa.build_demo && open jepa/demo/index.html   # needs the rendered media in jepa/results/demo/
```

The model itself runs on a GPU (Colab T4: ~2 s per prediction; an M1 Mac
took 45-178 s and ran out of memory):

```bash
python3 -m jepa.fetch --videos "" --hd-video P08-20240614-085000     # weights + one HD-EPIC video
python3 -m jepa.precompute jepa/_cache/hd-epic/P08-20240614-085000.mp4 --out jepa/results/P08.npz
python3 -m jepa.guide_video jepa/_cache/hd-epic/P08-20240614-085000.mp4 jepa/results/P08.npz \
        --recipe P08_R03 --out guide.mp4
NVIDIA_API_KEY=... python3 -m jepa.compare_vlm          # VLM tagging variants, scored
```

## Results so far (measured, small samples)

| What | Result | Chance |
|---|---|---|
| Probe on EPIC-KITCHENS, 145 actions, verb / noun / action top-5 recall | 47.9 / 53.8 / 36.4% | 5.2 / 1.7 / 0.14% |
| Same probe on the HD-EPIC scrambled-egg video, verb / noun | 22.5 / 18.5% | |
| Step tracker with HD-EPIC's annotated tags (in-sample, optimistic) | 57.5% | 15.6% |
| Step tracker with VLM tags for the recipe's own steps | 28-30% | 15.6% |

The probe was trained on GoPro footage (EPIC-KITCHENS); HD-EPIC is filmed
with Aria glasses in other kitchens, and the probe reads it about half as
well. That, not the VLM prompt, is the main limit: asking the VLM for more
specific tags made the tracker worse (13-27%). The next step is a step
probe trained on HD-EPIC's own latents.

## Data and licences

EPIC-KITCHENS-100 and HD-EPIC are CC BY-NC 4.0 (non-commercial); their
videos and the rendered demo media are kept out of git. V-JEPA 2 code and
weights are MIT. The NIM key is read from `.env` (git-ignored).
