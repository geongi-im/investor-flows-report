# Market Split Positive Flows Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Produce separate KOSPI and KOSDAQ TOP 10 images after filtering to stocks with both positive foreign and institutional net buy quantities.

**Architecture:** Extend the existing pure transform module so ranking behavior remains tested without live KIS calls. Update `main.py` so each market is processed independently and image rendering receives a market label and market index summary.

**Tech Stack:** Python 3, pandas, requests, python-dotenv, imgkit, holidays, pytest.

---

## File Structure

- Modify `tests/test_transform.py`: add failing tests for positive-both filtering and row-level stock change column.
- Modify `investor_flows/transform.py`: filter before sorting and change the report DataFrame column from `시장대비등락률` to `종목등락률(30일)`.
- Modify `main.py`: process `KOSPI` and `KOSDAQ` separately, render two images, and show the market index change once above the table.

## Task 1: Transform Tests and Logic

**Files:**
- Modify: `tests/test_transform.py`
- Modify: `investor_flows/transform.py`

- [ ] **Step 1: Write failing tests**

Add tests asserting that `select_top_combined_net_buy()` excludes rows where `frgn_ntby_qty <= 0` or `orgn_ntby_qty <= 0`, and that `build_report_dataframe()` produces `종목등락률(30일)` without repeated market index text.

- [ ] **Step 2: Verify tests fail**

Run: `python -m pytest tests/test_transform.py -v`

Expected: at least one failure because existing logic includes zero/negative-side rows and still outputs `시장대비등락률`.

- [ ] **Step 3: Implement minimal transform changes**

Update `select_top_combined_net_buy()` to filter enriched rows with both positive quantities before sorting. Update `build_report_dataframe()` to output `종목등락률(30일)` from `price_change_rate`.

- [ ] **Step 4: Verify tests pass**

Run: `python -m pytest tests/test_transform.py -v`

Expected: all transform tests pass.

## Task 2: Market Split Rendering

**Files:**
- Modify: `main.py`

- [ ] **Step 1: Update market processing**

Change `run()` to call a helper for each market:

- KOSPI: input code `0001`, file prefix `investor_flows_kospi_top_report`
- KOSDAQ: input code `1001`, file prefix `investor_flows_kosdaq_top_report`

Each helper filters and ranks only that market's rows.

- [ ] **Step 2: Update image rendering signature**

Change `save_df_as_image()` to accept `market`, `market_index_change_rate`, and `file_name`. Render the market index summary above the table.

- [ ] **Step 3: Verify compile and tests**

Run:

```bash
python -m pytest -v
python -m compileall main.py investor_flows utils tests
```

Expected: all tests pass and compile exits 0.

## Task 3: Live Verification

**Files:**
- Read: `img/`

- [ ] **Step 1: Run the report**

Run `python main.py` with valid KIS and wkhtmltoimage environment variables.

Expected: two image paths are printed.

- [ ] **Step 2: Inspect generated images**

Open both PNG files and verify:

- KOSPI image contains KOSPI caption and market index summary.
- KOSDAQ image contains KOSDAQ caption and market index summary.
- row table contains `종목등락률(30일)`.
- there is no repeated per-row market index value.

- [ ] **Step 3: Commit**

Run:

```bash
git add docs/superpowers/specs/2026-05-18-market-split-positive-flows-design.md docs/superpowers/plans/2026-05-18-market-split-positive-flows.md tests/test_transform.py investor_flows/transform.py main.py
git commit -m "feat: split positive investor flows by market"
```
