# Delivery Integrations Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Send generated report images to Telegram and create an MQWAY board post with both images attached.

**Architecture:** Add two focused utility modules under `utils/`: one for Telegram delivery and one for MQWAY board posting. Keep payload builders testable without network calls, then wire them into `main.py` after image generation.

**Tech Stack:** Python 3, requests, python-dotenv, Pillow, pytest.

---

## File Structure

- Create `utils/telegram_util.py`: Telegram Bot API media group sender and payload builder.
- Create `utils/api_util.py`: MQWAY board post client and multipart payload builder.
- Create `tests/test_delivery_utils.py`: unit tests for payload construction and environment validation.
- Modify `main.py`: call Telegram and MQWAY after image generation.
- Modify `.env.sample`: add Telegram and MQWAY variables.
- Modify `requirements.txt`: add Pillow.
- Copy `thumbnail/thumbnail.png` from the reference project.

## Task 1: Delivery Utility Tests

**Files:**
- Create: `tests/test_delivery_utils.py`

- [ ] **Step 1: Write failing tests**

Tests should import `TelegramUtil`, `ApiUtil`, and `ApiError`, then verify payload construction without making HTTP requests.

- [ ] **Step 2: Verify tests fail**

Run: `python -m pytest tests/test_delivery_utils.py -v`

Expected: import failure because the utility modules do not exist yet.

## Task 2: Telegram Utility

**Files:**
- Create: `utils/telegram_util.py`

- [ ] **Step 1: Implement Telegram utility**

Create a utility that:

- reads `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID`, `TELEGRAM_CHAT_TEST_ID`.
- builds media group metadata with caption only on the first item.
- sends images through `requests.post`.
- raises `RuntimeError` when Telegram returns `ok: false`.

- [ ] **Step 2: Run delivery tests**

Run: `python -m pytest tests/test_delivery_utils.py -v`

Expected: tests that only depend on Telegram behavior pass, MQWAY imports may still fail until Task 3 is complete.

## Task 3: MQWAY API Utility

**Files:**
- Create: `utils/api_util.py`

- [ ] **Step 1: Implement MQWAY utility**

Create a utility that:

- reads `BASE_URL`.
- posts to `{BASE_URL}/api/board-research`.
- creates multipart fields `image[0]`, `image[1]`.
- compresses images with Pillow before upload.
- raises `ApiError` on HTTP/request/JSON/application failures.

- [ ] **Step 2: Run delivery tests**

Run: `python -m pytest tests/test_delivery_utils.py -v`

Expected: all delivery utility tests pass.

## Task 4: Main Integration

**Files:**
- Modify: `main.py`
- Modify: `.env.sample`
- Modify: `requirements.txt`
- Add: `thumbnail/thumbnail.png`

- [ ] **Step 1: Wire delivery into main**

After `InvestorFlowsReport().run()` returns two image paths, send them to Telegram and create an MQWAY post with category `외국인기관순매수`.

- [ ] **Step 2: Update environment and requirements**

Add Telegram/MQWAY env names to `.env.sample` and add `Pillow` to `requirements.txt`.

- [ ] **Step 3: Copy thumbnail asset**

Copy `C:\Users\imgeongi-notebook\python\institution-total-report\thumbnail\thumbnail.png` to `thumbnail/thumbnail.png`.

## Task 5: Verification

**Files:**
- Read: all changed files.

- [ ] **Step 1: Run tests**

Run: `python -m pytest -v`

Expected: all tests pass.

- [ ] **Step 2: Compile**

Run: `python -m compileall main.py investor_flows utils tests`

Expected: command exits 0.

- [ ] **Step 3: Live run**

Run `python main.py` with valid environment variables.

Expected:

- KOSPI and KOSDAQ images are generated.
- Telegram media group is sent.
- MQWAY API post is created.

- [ ] **Step 4: Commit**

Run:

```bash
git add docs/superpowers/specs/2026-05-18-delivery-integrations-design.md docs/superpowers/plans/2026-05-18-delivery-integrations.md tests/test_delivery_utils.py utils/telegram_util.py utils/api_util.py main.py .env.sample requirements.txt thumbnail/thumbnail.png
git commit -m "feat: add telegram and mqway delivery"
```
