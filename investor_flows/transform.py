from __future__ import annotations

from typing import Any, Iterable

import pandas as pd


def parse_int(value: Any) -> int:
    if value is None:
        return 0
    text = str(value).replace(",", "").strip()
    if not text:
        return 0
    return int(float(text))


def with_combined_flow_fields(row: dict[str, Any]) -> dict[str, Any]:
    item = row.copy()
    foreign_qty = parse_int(item.get("frgn_ntby_qty"))
    institution_qty = parse_int(item.get("orgn_ntby_qty"))
    foreign_amount = parse_int(item.get("frgn_ntby_tr_pbmn"))
    institution_amount = parse_int(item.get("orgn_ntby_tr_pbmn"))

    item["combined_net_buy_qty"] = foreign_qty + institution_qty
    item["combined_net_buy_amount"] = foreign_amount + institution_amount
    return item


def tag_rows_with_market(rows: Iterable[dict[str, Any]], market: str) -> list[dict[str, Any]]:
    result = []
    for row in rows:
        item = row.copy()
        item["market"] = market
        result.append(item)
    return result


def select_top_combined_net_buy(
    rows: Iterable[dict[str, Any]], top_n: int = 10
) -> list[dict[str, Any]]:
    enriched = [with_combined_flow_fields(row) for row in rows]
    enriched.sort(key=lambda item: item["combined_net_buy_qty"], reverse=True)
    return enriched[:top_n]


def _format_rate(value: Any) -> str:
    value_float = float(value)
    if value_float < 0:
        return f"<span class='negative'>{value_float:.2f}%</span>"
    if value_float > 0:
        return f"<span class='positive'>{value_float:.2f}%</span>"
    return f"{value_float:.2f}%"


def _format_compare_rates(row: dict[str, Any]) -> str:
    market = row.get("market", "UNKNOWN")
    market_text = f"{market}: {_format_rate(row.get('index_change_rate', 0))}"
    stock_text = f"종목: {_format_rate(row.get('price_change_rate', 0))}"
    return f"{market_text}<br>{stock_text}"


def build_report_dataframe(rows: list[dict[str, Any]]) -> pd.DataFrame:
    if not rows:
        return pd.DataFrame()

    result_df = pd.DataFrame()
    result_df["종목명"] = [
        f"{row['hts_kor_isnm']} <span class='stock-code'>({row['mksc_shrn_iscd']})</span>"
        for row in rows
    ]
    result_df["현재가"] = [f"{parse_int(row.get('stck_prpr')):,}" for row in rows]
    result_df["시장대비등락률"] = [_format_compare_rates(row) for row in rows]
    result_df["외국인순매수량"] = [f"{parse_int(row.get('frgn_ntby_qty')):,}" for row in rows]
    result_df["기관순매수량"] = [f"{parse_int(row.get('orgn_ntby_qty')):,}" for row in rows]
    result_df["합산순매수량"] = [
        f"{parse_int(row.get('combined_net_buy_qty')):,}" for row in rows
    ]
    result_df["합산순매수금액"] = [
        f"{round(parse_int(row.get('combined_net_buy_amount')) / 100, 2):,}"
        for row in rows
    ]
    return result_df
