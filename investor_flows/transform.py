from __future__ import annotations

from typing import Any, Iterable

import pandas as pd


def parse_int(value: Any) -> int:
    """숫자 형태의 값을 정수로 변환한다.

    Input:
        value: 숫자, 문자열, None 등 정수로 변환할 원본 값.
    Output:
        int: 변환된 정수. 값이 없으면 0을 반환한다.
    """
    if value is None:
        return 0
    text = str(value).replace(",", "").strip()
    if not text:
        return 0
    return int(float(text))


def with_combined_flow_fields(row: dict[str, Any]) -> dict[str, Any]:
    """외국인과 기관의 순매수 수량/금액을 합산한 필드를 추가한다.

    Input:
        row: KIS 투자자 매매동향 API의 종목별 원본 행.
    Output:
        dict[str, Any]: 합산 순매수 수량과 금액 필드가 추가된 행 복사본.
    """
    item = row.copy()
    foreign_qty = parse_int(item.get("frgn_ntby_qty"))
    institution_qty = parse_int(item.get("orgn_ntby_qty"))
    foreign_amount = parse_int(item.get("frgn_ntby_tr_pbmn"))
    institution_amount = parse_int(item.get("orgn_ntby_tr_pbmn"))

    item["combined_net_buy_qty"] = foreign_qty + institution_qty
    item["combined_net_buy_amount"] = foreign_amount + institution_amount
    return item


def tag_rows_with_market(rows: Iterable[dict[str, Any]], market: str) -> list[dict[str, Any]]:
    """각 행에 시장 구분 값을 추가한다.

    Input:
        rows: 시장 구분을 추가할 원본 행 목록.
        market: 행에 설정할 시장명.
    Output:
        list[dict[str, Any]]: market 필드가 추가된 행 복사본 목록.
    """
    result = []
    for row in rows:
        item = row.copy()
        item["market"] = market
        result.append(item)
    return result


def select_top_combined_net_buy(
    rows: Iterable[dict[str, Any]], top_n: int = 10
) -> list[dict[str, Any]]:
    """외국인과 기관이 모두 순매수한 종목 중 합산 순매수 상위 종목을 고른다.

    Input:
        rows: 투자자 매매동향 원본 행 목록.
        top_n: 반환할 상위 종목 개수.
    Output:
        list[dict[str, Any]]: 합산 순매수 수량 기준 내림차순 상위 행 목록.
    """
    enriched = [
        with_combined_flow_fields(row)
        for row in rows
        if parse_int(row.get("frgn_ntby_qty")) > 0 and parse_int(row.get("orgn_ntby_qty")) > 0
    ]
    enriched.sort(key=lambda item: item["combined_net_buy_qty"], reverse=True)
    return enriched[:top_n]


def _format_rate(value: Any) -> str:
    """등락률 값을 HTML 색상 span 문자열로 변환한다.

    Input:
        value: 퍼센트로 표시할 숫자형 값.
    Output:
        str: 양수/음수 CSS 클래스가 적용된 HTML 문자열.
    """
    value_float = float(value)
    if value_float < 0:
        return f"<span class='negative'>{value_float:.2f}%</span>"
    if value_float > 0:
        return f"<span class='positive'>{value_float:.2f}%</span>"
    return f"{value_float:.2f}%"


def build_report_dataframe(rows: list[dict[str, Any]]) -> pd.DataFrame:
    """보고서 이미지 렌더링에 사용할 표시용 DataFrame을 만든다.

    Input:
        rows: 상위 순매수 종목과 가격 변동 정보가 담긴 행 목록.
    Output:
        pd.DataFrame: 화면 표시용 컬럼과 포맷이 적용된 DataFrame.
    """
    if not rows:
        return pd.DataFrame()

    result_df = pd.DataFrame()
    result_df["종목명"] = [
        f"{row['hts_kor_isnm']} <span class='stock-code'>({row['mksc_shrn_iscd']})</span>"
        for row in rows
    ]
    result_df["현재가"] = [f"{parse_int(row.get('stck_prpr')):,}" for row in rows]
    result_df["종목등락률(30일)"] = [_format_rate(row.get("price_change_rate", 0)) for row in rows]
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
