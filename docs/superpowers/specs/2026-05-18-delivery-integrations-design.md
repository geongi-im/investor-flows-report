# Delivery Integrations Design

## Goal

After generating the KOSPI and KOSDAQ investor-flow report images, send both images to Telegram and create one MQWAY board post with both images attached.

The existing image generation flow remains unchanged.

## Telegram

Use the same Telegram Bot API pattern as the reference project:

- endpoint: `https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMediaGroup`
- chat id: `TELEGRAM_CHAT_ID`
- images: both generated report PNGs
- caption: attached only to the first image

Caption:

`YYYY-MM-DD 외국인+기관 동반 순매수 TOP 10`

On delivery failure, raise a clear exception. The main script will log the exception and attempt to send a test-channel error message if `TELEGRAM_CHAT_TEST_ID` is configured.

## MQWAY API

Use the same board API pattern as the reference project:

- base URL environment variable: `BASE_URL`
- endpoint: `{BASE_URL}/api/board-research`
- method: `POST`
- request type: multipart when images are present
- image fields: `image[0]`, `image[1]`
- optional thumbnail field: `thumbnail_image`

Post fields:

- title: `YYYY-MM-DD 외국인+기관 동반 순매수 TOP 10`
- content: `YYYY-MM-DD 외국인+기관 동반 순매수 TOP 10 결과`
- category: `외국인기관순매수`
- writer: `admin`

Thumbnail:

- path: `thumbnail/thumbnail.png`
- if missing, continue without thumbnail and log a warning.

## Environment

Add these environment variables to `.env.sample`:

- `TELEGRAM_BOT_TOKEN`
- `TELEGRAM_CHAT_ID`
- `TELEGRAM_CHAT_TEST_ID`
- `BASE_URL`

Add `Pillow` to `requirements.txt` because MQWAY image upload compresses images before posting.

## Tests

The network APIs are not called from unit tests. Tests cover:

- Telegram media group payload puts the caption only on the first image.
- MQWAY post payload uses category `외국인기관순매수`.
- MQWAY file field names are `image[0]` and `image[1]`.
- required environment variable checks fail with clear errors.
