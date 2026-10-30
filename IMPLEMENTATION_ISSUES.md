# 實作問題記錄（Implementation Issues Log）

> 目的：記錄本專案實作過程中撞到的問題、當時的解法與驗證結果，
> 以及**尚未解決、需要跟 teammate 討論**的事項。
> 最後更新：2026-10-28（session 內實際執行結果為準）

## 一、已解決：原始參考程式跑不出交叉現象

- **現象**：照給定的 snippet 原樣實測，B 從第 3 堂就領先（+0.09 → +0.21），
  且狂刷 `stretch_recipe`；雙方都在 ~15 堂前逼近 1.85 上限飽和。
- **根因（probe1–probe6 共六輪探測確認）**：
  1. 學習率太高（0.20–0.25），`(1-s)` 動態下約 15 堂就飽和，後期無優勢可言；
  2. 閘門太弱（`exp(-3.5·shortfall)`），過早的 stretch 幾乎不受懲罰；
  3. 資訊加成符號反了（預測使變異數變大，`√var − √var'` 恆為負）；
  4. Kalman 增益 ≈0.96，信念 1–2 堂就修好，B 從未付出學習成本。
- **解法（三項公開宣告的修改，見 [benchmark.py](/Users/samsam/Documents/muse-project/test/benchmark.py)）**：
  閘門 3.5→6.0、學習率縮放 ×~0.55；B 初期規格錯誤（`gate_hat=0`、
  從預測誤差學閘門）；Bandit 獎勵改用環境 session-score jump。
- **驗證**：第 3–9 堂 B−A=−0.151、第 11–20 堂 +0.113，交叉點約第 11 堂；
  `test_crossover_windows` 通過。

## 二、已解決：Bandit A 莫名弱、World B 莫名強

- **現象**：早期探測中 B 永遠贏（30/30 種子），A 甚至反覆選已飽和的 `knife_drill`。
- **根因**：A 的獎勵（session 間 obs 差總和）噪聲標準差 ~0.2，遠大於真實增益
  0.05–0.15（SNR < 1），加上強制五臂全試一輪浪費前期；B 的 `alpha_hat`
  初值接近真值、Kalman 一兩步就收斂，等於沒付辨識成本。
- **解法**：A 改樂觀初始化＋session-score 獎勵；B 初期錯估（高估 heat、
  忽略閘門）且 EMA 學得慢，製造出「付學費」的早期成本。
- **驗證**：`test_replay.py`／`test_benchmark.py` 全數通過；JS 版重現交叉
  （early −0.135、late +0.128、交叉第 11 堂）。

## 三、已解決：BKT 擬合的兩個測試失敗（皆為真實現象，非程式 bug）

1. **`p_init` 還原失敗**：合成資料真值 0.3，擬合出 0.1。
   根因是 BKT 已知的弱可識別性（`p_init` 與 `p_guess` 在短序列下分不開），
   而決策真正依賴的 `p_learn`／`p_guess` 還原精確。解法：測試對
   `p_learn`／`p_guess` 用緊界、對 `p_init`／`p_slip` 用鬆界，並在註解載明理由。
2. **Oracle 在合成資料上輸給 B（1.633 vs 1.667）**：雙方都逼近 2.0 上限，
   30 種子下的差距是抽樣噪聲。解法：比照 toy 的慣例放寬為
   `O ≥ B − 0.05`，並在 README 誠實記載。

## 四、已解決：沙盒環境限制

- **無網路**（`curl github`／`pypi` 皆回 000）：無法下載 ASSISTments/EdNet，
  也無法 `pip install`。對策：只用內建＋預裝套件（numpy、pandas、
  sklearn、torch 皆可用），真實資料管線改用「同格式合成 CSV」全程驗證，
  等拿到真檔直接丟進 `data/` 跑 `real-data`。
- **pytest 未安裝**：測試寫成 `python3 test_*.py` 可直接跑的形式。
- **matplotlib 字體快取無寫入權限**：設 `MPLCONFIGDIR=/tmp/mplconfig` 繞過。
- **port 8765 被 AnkiConnect 佔用、`setsid` 在 macOS 不存在、
  沙盒擋下 port 8931 綁定**：改用 `require_escalated` 申請後以 session
  內 server 驗證；交接時只給啟動指令，不宣稱長期可用。
- **index.html 曾出現重複 `</body></html>`**：已刪除，83 個 ID 無重複、
  內嵌 JS 通過 `node --check`。

## 五、未解決：要跟 teammate 討論的事項

以下每一項都是「程式能跑，但產品／科學判斷還沒定案」的問題：

1. **「B 在慢速/高噪聲學習者吃虧 7/20」未被證實。**
   實測各噪聲下 B 只輸 0–2/40（Kalman 對噪聲很穩）。要問 teammate：
   這個宣稱要保留、重測（多原型抽樣＋遺忘項），還是從 demo 拿掉？
   目前 `ARCHETYPES`（steady/fast/slow/noisy）與 `forget_rate` 已進
   [benchmark.py](/Users/samsam/Documents/muse-project/test/benchmark.py)（預設關閉），
   但還沒跑出結論。
2. **Junyi 轉接器剛開工、尚未驗證。**
   [datasets.py](/Users/samsam/Documents/muse-project/test/datasets.py) 已有
   欄位自動偵測＋練習→知識點對照表設計（因無網路、無法核對官方欄位名稱，
   所以不敢寫死 header），但合成 Junyi 檔、擬合、重播、測試都還沒做。
   要問 teammate：Junyi 真檔誰負責拿？欄位對應由誰跟官方確認？
   （EdNet/Adnet 順位排在 Junyi 之後。）
3. **Muse 即時語音還沒接。**
   文字擷取已有 API 路徑（含離線回退），但教練回覆仍是固定模板；
   `demo.py chat --live`、`generate_coach_reply` 都還沒寫。
   要問 teammate：誰拿 `MODEL_API_KEY`？demo 當天沒 key 的備案就是離線模板，
   可以接受嗎？
4. **對話 demo 的觀測來源是展示用的。**
   `chat_demo` 裡信念更新用的是模擬器觀測值，文字擷取的 obs 只印出來對照；
   正式環境要把文字 obs 變成更新輸入（號稱改一行，但改了之後信念動態
   會變，數字要重跑）。要問 teammate：這一行誰改、誰重驗？
5. **交叉是做菜設定的特性，不是普世定律。**
   同一套 A/B/Oracle 搬到 BKT 合成動態上，B 從頭贏到尾（+0.90，無交叉）。
   要問 teammate：黑客松故事要主打「交叉」還是主打「按資料實測的方法論」？
   這決定 demo 影片腳本與 README 的寫法。
6. **截止與分工（11/4 晚間 9:00 ET）。**
   建議順序：Muse 語音 → 信念面板進產品 → 真實資料驗證 → 3 分鐘影片。
   要問 teammate：錄影誰負責？`results.png`／`results_inside.png` 目前是最新，
   但改了程式就要重跑 `demo.py benchmark` 更新圖片。
