---
name: skill-module-trend-style-normalizer
description: Stateless style and epistemic normalizer module. Enforces Taiwan Traditional Chinese analytical tone, deterministic concept rewrites (sanitizing marketing hype, bureaucratic cliches, and forbidden styles), and epistemic boundaries across all trend intelligence reports.
---
# Skill Module: Trend Style Normalizer

Stateless style sanitization and epistemic linter module governing tone, lexicon normalization, and reasoning boundary compliance for structured trend intelligence reports.

## When to Use

Use this module whenever generating or auditing draft sections for trend reports (Geopolitics, VISA, Global Economy, North America Politics) to sanitize forbidden styles and enforce deterministic concept rewrites.

## Input Requirements

- `draft_content`: Raw markdown text or section drafts to be validated/normalized.
- `domain`: Target intelligence domain (`geopolitics`, `visa`, `economy`, `na_politics`).

## Style & Lexicon Specification

### 1. Forbidden Styles
- **電報體**：禁止破碎短語或主謂賓不全的碎片記錄。
- **公文八股體**：禁止虛詞堆砌、形式主義官腔（如「此一」、「該等」）。
- **文言或半文半白**：禁止非現代書面語的文言句法。
- **行銷與短影音幹片語言**：禁止演算法誇大修辭、情緒動員詞彙。

### 2. Deterministic Concept Mappings
遇以下概念時，嚴格採行精確中立詞彙：
- **優化** $\to$ **最佳化**
- **落地** $\to$ **實施**、**導入**、**部署**、**應用**（依技術與政策語境選用）
- **賦能** $\to$ **提供能力**、**支援**、**強化**
- **基石** $\to$ **基礎**
- **最穩健的 / 最簡單 / 最有效** $\to$ **穩定性較高**、**複雜度較低**、**收斂速度較快**
- **至關重要 / 核心關鍵** $\to$ **具決定性影響**、**為必要條件**
- **降維打擊 / 精準打擊** $\to$ **結構性優勢**、**特定對象處置**
- **組合拳** $\to$ **多項措施併行**
- **鐵拳** $\to$ **強制制裁手段**
- **公文虛詞（此一、該等）** $\to$ **這個**、**這些**、**該項**

### 3. Chronology Rules
- 一律採西元紀年（`yyyy 年` 或 `yyyy-mm-dd`）；嚴格禁用漢字紀年（如二〇二六年）與干支紀年。

### 4. Epistemic Constraints
- **推論邊界**：推論必須標註 `模型推測`，且全文每一對應區塊嚴格限制至多一句。
- **勝負預測禁止**：嚴禁對選舉勝負、戰局終局或法院未決判決進行確定性預測。
- **事實分離**：嚴格區隔官方已生效/已公告之行動與未確認傳聞、草案或媒體放話。

## Process

1. **詞彙掃描與置換**：以確定性對照表遍歷文本，執行 Token 層級的正規化置換。
2. **語體風格檢查**：確認句式符合繁體中文（臺灣）專業智庫與分析師語體，移除公文八股與幹片詞。
3. **推論句數稽核**：統計「模型推測」出現次數，確保各章節不超過單句上限。
4. **輸出淨化文本**：返回通過 Lint 驗證的乾淨 Markdown 文本。

## Output

- `sanitized_content`: 符合樣式與知識論契約的 Markdown 文本。
- `lint_report`: 標記置換項目與推論句數檢驗結果。

## Validation Checklist

- [ ] 無任何「優化、落地、賦能、基石、精準打擊、此一」等非合規詞彙。
- [ ] 紀年皆為阿拉伯數字西元格式。
- [ ] 模型推測標註合規且無越界多句推論。
