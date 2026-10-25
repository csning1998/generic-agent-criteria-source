---
name: skill-module-delta-comparator
description: Stateless baseline diffing and directional movement classifier module. Compares extracted candidate facts against prior period baselines, formats structured factual change narratives, and injects empty-delta fallbacks.
---
# Skill Module: Delta Comparator

Stateless difference-engine and movement classifier module that evaluates whether new candidate facts constitute a directional policy, market, or legal change relative to the prior period baseline.

## When to Use

Use this module whenever a trend pipeline needs to determine the delta between newly scraped facts and the prior baseline, format the 5-element factual change chain, or trigger the standardized empty-delta fallback.

## Input Requirements

- `candidates`: List of verified candidates from `skill-module-authority-search`.
- `prior_baseline_date`: Date or reference document of the prior session/cycle baseline.
- `domain`: Intelligence domain (`geopolitics`, `visa`, `economy`, `na_politics`).

## Process

1. **State Diffing**:
   - Compare each candidate against the known prior baseline.
   - Categorize each monitored entity or sector into:
     - `STRUCTURAL_DELTA`: Concrete policy change, threshold shift, rate move, legal filing, or military action.
     - `BASELINE_UNCHANGED`: No new official rule, data point, or action published within the window.
2. **Fact-Chain Construction (for Delta items)**:
   - Construct the standard 5-element factual narrative:
     1. Who did what / What changed (provision, threshold, quota, rate, action).
     2. Effective date, applicability, and former state.
     3. Stated justification from the source (or explicitly state "官方未說明理由").
     4. Directional movement relative to the prior session/cycle.
     5. Official document date and active URL.
3. **Empty-Delta Fallback Handling (for Unchanged items)**:
   - When `BASELINE_UNCHANGED`, emit the exact domain-mandated fallback string without speculation or outdated fillers:
     - **Geopolitics (外圍區域)**: `本週無足以改寫格局的新發展` (若既有基線未變，註明既有文件日期)。
     - **VISA**: `本期無新的可核對規則` (保留既有基線一句，不得以舊頁面充數)。
     - **Economy**: `無新的可核對數字` (保留既有指標報價與最後更新日期)。
     - **NA Politics**: `本期無新的可核對官方紀錄` (各區塊不得刪節，保留基線一句)。

## Output

- `diff_results`:
  - `deltas`: Array of structured narrative items matching the 5-element chain.
  - `unchanged_entities`: Array of fallback statements mapped to untouched sectors.
  - `top_moves`: Top 5 directional relationship movements for Section 5/6 synthesis.

## Validation Checklist

- [ ] Every delta item contains all 5 required narrative elements.
- [ ] No unannounced motives or fabricated justifications (unspecified reasons explicitly marked as "官方未說明理由").
- [ ] Unchanged entities strictly employ the prescribed fallback phrase.
