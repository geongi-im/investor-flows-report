# Market Split Positive Flows Design

## Goal

Update the investor flows report so each market produces its own TOP 10 image.

The ranking must first filter to stocks where both foreign and institutional net buy quantities are positive. After that filter, each market is ranked by combined foreign plus institutional net buy quantity.

## Ranking Rule

For each market independently:

1. Fetch KOSPI rows with `FID_INPUT_ISCD=0001`.
2. Fetch KOSDAQ rows with `FID_INPUT_ISCD=1001`.
3. Keep only rows where `frgn_ntby_qty > 0` and `orgn_ntby_qty > 0`.
4. Compute `combined_net_buy_qty = frgn_ntby_qty + orgn_ntby_qty`.
5. Sort descending by `combined_net_buy_qty`.
6. Select TOP 10.

Rows where either side is zero or negative are excluded before ranking, even if the combined value would be large.

## Output

Generate two PNG files:

- `img/investor_flows_kospi_top_report_YYYYMMDD.png`
- `img/investor_flows_kosdaq_top_report_YYYYMMDD.png`

The script prints both paths, one per line.

## Layout

Each image caption identifies the market:

- `YYYY-MM-DD KOSPI 외국인+기관 동반 순매수 TOP 10`
- `YYYY-MM-DD KOSDAQ 외국인+기관 동반 순매수 TOP 10`

The repeated market index value is removed from every row. Instead, each image shows the market 30-day change once near the top:

- `시장지표(30일): KOSPI +1.23%`
- `시장지표(30일): KOSDAQ -0.45%`

The table keeps the stock 30-day change as a row-level value under `종목등락률(30일)`.

## Tests

Tests cover:

- filtering out rows where foreign or institutional net buy quantity is not positive.
- sorting and TOP 10 selection after filtering.
- report DataFrame exposes `종목등락률(30일)` instead of repeated market index text.
- market labels remain attached to rows from market-specific API calls.
