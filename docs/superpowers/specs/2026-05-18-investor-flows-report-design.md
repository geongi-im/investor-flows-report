# Investor Flows Report Design

## Goal

Create a new Python project in `investor-flows-report` that uses the Korea Investment & Securities Open API `foreign-institution-total` endpoint to find the top 10 Korean stocks by combined foreign and institutional net buy quantity.

The first version stops at local image generation. Telegram delivery and board post API registration are intentionally out of scope.

## Reference

The existing reference project is available through `reference.lnk`, which points to:

`C:\Users\imgeongi-notebook\python\institution-total-report`

The reference implementation already handles:

- KIS token loading, refreshing, and saving.
- `foreign-institution-total` API calls.
- market detection with FinanceDataReader.
- 30 trading-day stock and index change calculations.
- rendering a DataFrame as a PNG through `imgkit`.

This project reuses that structure but changes the ranking basis from institution-only flow to combined foreign plus institutional flow.

## API Behavior

Use:

- Path: `/uapi/domestic-stock/v1/quotations/foreign-institution-total`
- TR ID: `FHPTJ04400000`
- `FID_COND_MRKT_DIV_CODE`: `V`
- `FID_COND_SCR_DIV_CODE`: `16449`
- `FID_INPUT_ISCD`: `0000`
- `FID_DIV_CLS_CODE`: `0`
- `FID_RANK_SORT_CLS_CODE`: `0`
- `FID_ETC_CLS_CODE`: `0`

`FID_ETC_CLS_CODE=0` retrieves the aggregate screen that includes both foreign and institutional columns. The fields used for ranking are:

- `frgn_ntby_qty`: foreign net buy quantity
- `orgn_ntby_qty`: institutional net buy quantity

## Ranking Rule

For each API row:

`combined_net_buy_qty = frgn_ntby_qty + orgn_ntby_qty`

Rows are sorted by `combined_net_buy_qty` descending. The first 10 rows are selected.

Negative values are allowed in the inputs. A stock can still rank highly if the sum is high after one side offsets the other.

## Output

Generate one PNG image under `img/`:

`img/investor_flows_top_report_YYYYMMDD.png`

The table should show:

- stock name and code
- current price
- 30-day market versus stock performance
- foreign net buy quantity
- institutional net buy quantity
- combined net buy quantity
- combined net buy amount in KRW 100 million units, if both amount fields are present

The caption should identify the report as:

`YYYY-MM-DD 외국인+기관 합산 순매수 상위 TOP 10`

## Project Structure

Expected files:

- `main.py`: executable report script.
- `utils/logger_util.py`: local logger helper.
- `requirements.txt`: runtime dependencies.
- `.env.sample`: required environment variables.
- `token.json.sample`: token file example.
- `img/`: generated output directory.

The implementation should not include Telegram or external board post utilities in the first version.

## Error Handling

The script should fail clearly when required KIS environment variables are missing:

- `KIS_APP_KEY`
- `KIS_APP_SECRET`
- `KIS_URL_BASE`

It should also fail clearly when `WKHTMLTOIMAGE_PATH` is missing because image generation depends on it.

API failures should include the KIS message code or response body where available.

## Tests

Add focused tests around the pure ranking and formatting logic before writing production code:

- numeric string parsing handles comma-free positive and negative values.
- combined quantity is computed from foreign plus institutional values.
- rows are sorted by combined quantity descending.
- top 10 slicing is applied after sorting, not before.
- combined amount is computed from foreign plus institutional amount fields when available.

API calls, FinanceDataReader calls, and image rendering can remain integration behavior for this first version.
