# 題庫更新工具

用來把「產險業務員測驗題庫」原廠 PDF 轉成 `index.html` 內嵌的題庫資料。
每次改版（檔名如 `...題庫YYYYMMDD.pdf`）都可以重跑這套流程，不必再重新手動解析 PDF。

## 資料流

```
保險實務、產險業務員測驗題庫YYYYMMDD.pdf ─┐
                                          ├─► extract_pdf.py ─► tools/out/{practical,regulation}.json
保險法規與理論、產險業務員測驗題庫YYYYMMDD.pdf ─┘
                                                                        │
                                                                        ▼
                                                          build_questions.py
                                                                        │
                                                                        ▼
                                                     tools/data/questions.json  （人類可讀，進 git）
                                                                        │
                                                                        ▼
                                                          inject_questions.js
                                                                        │
                                                                        ▼
                                                              index.html（混淆後內嵌）
```

## 使用方式

1. 把兩份原廠 PDF 放在專案根目錄（檔名需完全對應，含全形／半形空格）。
2. 安裝相依套件：`pip install pymupdf`（Node 端不需額外套件）。
3. 執行：

   ```bash
   mkdir -p tools/out
   python3 tools/extract_pdf.py "保險實務、產險業務員測驗題庫YYYYMMDD.pdf" tools/out/practical.json
   python3 tools/extract_pdf.py "保險法規與理論 、產險業務員測驗題庫YYYYMMDD.pdf" tools/out/regulation.json
   python3 tools/build_questions.py tools/out/practical.json tools/out/regulation.json tools/data/questions.json
   node tools/inject_questions.js
   ```

4. 檢查 `build_questions.py` 印出的統計與警告（詳見下方「已知眉角」），確認無誤後：
   - 用瀏覽器打開 `index.html` 實際操作一輪（進分類練習、作答看有沒有跳出解析、跑一次模擬考）。
   - **重要**：若本次改版使題目 `id` 重新分配（分類新增/刪除/順序變動、或總題數變動都會），
     必須同步把 `index.html` 裡 `const LS` 的 `wrong`／`fav` 版本號往上加一
     （例如 `pins_wrong_v2` → `pins_wrong_v3`），否則舊使用者瀏覽器裡儲存的錯題本／收藏
     id 會對應到錯誤的新題目。`progress`／`records` 兩把 key 因為不是用題目 id 存，通常不用動。
5. `git add index.html tools/data/questions.json`（連同 `tools/out/*.json` 如果想留底），
   commit + push 到 `main`，GitHub Pages 會自動部署。原廠 PDF 本身不要進 git
   （版權內容，且會讓 repo 變得肥大——參考 `.gitignore`）。

## 已知眉角（20260512 版遇到的狀況，未來版本可能不同）

- **廠商防複製亂碼**：PDF 文字層裡，選項的字母標籤有時會被刻意重複
  （例如 `(A)(A)條款(B)(B)條款(C)(C)條款(D)以上皆是` 而不是乾淨的
  `(A)條款(B)條款(C)條款(D)以上皆是`）。`extract_pdf.py` 會自動收斂這種
  相鄰重複的狀況。但「運輸保險」（協會貨物條款 ICC(A)/(B)/(C)）那一段
  有少數幾題重複被打亂而非乾淨相鄰（例如變成 `(A)(C)...(C)(A)...`），
  無法自動還原，這幾題已在 `build_questions.py` 的 `MANUAL_FIXES` 裡
  用逐字元比對 PDF 原始資料手動修正並寫死。若重新解析同一版 PDF，這些
  修正仍然適用；但如果換成全新一版 PDF，`MANUAL_FIXES` 裡的
  `(page, source_no)` 座標多半會失效，需要重新用同樣手法（讀
  `fitz`/PyMuPDF 的 `get_text("rawdict")` 字元座標）找出受影響的題目。
- **分類是用題號重置偵測出來的，不是 PDF 裡的章節標題**：`保險實務`
  那份 PDF 完全沒有印出章節名稱，只能靠「題號從 1 重新開始」來切出
  7 個小節，再照內容判斷屬於哪個險種（`build_questions.py` 裡的
  `PRACTICAL_SECTION_LABELS`，照順序寫死）。如果未來版本增減章節或調
  換順序，這個對照表必須跟著改，否則整批題目分類會全部錯位——
  `build_questions.py` 會在小節數量對不上時直接報錯中止，但如果數量
  剛好相同、只是順序換了，並不會自動偵測出來，仍要人工核對。
- **20260512 版把「財產保險理論」併入「保險法規與理論」那份 PDF**，
  不再是獨立的實務類別。`index.html` 的 `CATS` 也對應拿掉了
  `財產保險理論`，`財產保險法規` 改標籤為「財產保險法規與理論」。
- **1 題已知內容缺字**（財產保險法規類，題幹「...造成損失發生之意外
  事件係指」開頭少了「危險因素」四個字）：已用 PyMuPDF 讀到字元座標
  層級確認這是原廠 PDF 文字層本身就缺漏，不是解析程式的問題，未特別
  修正。
