import json, sys, time
sys.path.insert(0, "/tmp/w3d-pw")
from playwright.sync_api import sync_playwright

CHROME = ("/Users/samsam/Library/Caches/ms-playwright/chromium-1248/"
          "chrome-mac-arm64/Google Chrome for Testing.app/Contents/MacOS/Google Chrome for Testing")
OUT = "/Users/samsam/Documents/muse-project/test/_w3d"
import os
os.makedirs(OUT, exist_ok=True)

console, failed = [], []
with sync_playwright() as p:
    b = p.chromium.launch(executable_path=CHROME,
                          args=["--no-sandbox", "--disable-dev-shm-usage"])
    pg = b.new_page(viewport={"width": 1366, "height": 768})
    pg.on("console", lambda m: console.append((m.type, m.text[:200])))
    pg.on("requestfailed", lambda r: failed.append(r.url + " " + (r.failure or "")))
    pg.on("pageerror", lambda e: console.append(("pageerror", str(e)[:200])))
    pg.goto("http://127.0.0.1:8000/game.html", wait_until="networkidle")
    pg.wait_for_timeout(4000)
    pg.screenshot(path=f"{OUT}/d_idle.png")
    has_canvas = pg.evaluate("() => { const c = document.getElementById('scene'); return c && c.width > 0; }")
    print("canvas present:", has_canvas)
    # drive: pause autoplay, step, scrub to drift, xray, seed change
    pg.click("#playBtn")  # pause (autoplay is on unless reduced-motion)
    pg.click("#stepBtn"); pg.wait_for_timeout(500)
    print("session after step:", pg.eval_on_selector("#sessOut", "e => e.textContent"))
    pg.eval_on_selector("#sessSlider", "e => { e.value = 21; e.dispatchEvent(new Event('input')); }")
    pg.wait_for_timeout(1500)
    pg.screenshot(path=f"{OUT}/d_drift21.png")
    print("banner visible:", pg.eval_on_selector("#banner", "e => e.style.display"))
    pg.click("#xray"); pg.wait_for_timeout(500)
    pg.screenshot(path=f"{OUT}/d_xray.png")
    pg.select_option("#seedSel", "12"); pg.wait_for_timeout(2500)
    pg.screenshot(path=f"{OUT}/d_seed12.png")
    print("bubbleB:", pg.eval_on_selector("#bubbleB span", "e => e.textContent")[:120])
    print("readout:", pg.eval_on_selector("#readout", "e => e.textContent")[:160])
    print("sess:", pg.eval_on_selector("#sessOut", "e => e.textContent"))
    b.close()
errs = [m for m in console if m[0] in ("error", "pageerror")]
print("CONSOLE_ERRORS:", len(errs))
for t, m in errs[:10]:
    print(" -", t, m)
print("FAILED_REQUESTS:", len(failed))
for f in failed[:10]:
    print(" -", f)
warns = [m for m in console if m[0] == "warning"]
print("WARNINGS:", len(warns))
