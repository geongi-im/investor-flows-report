import pandas as pd

from investor_flows.transform import (
    build_report_dataframe,
    parse_int,
    select_top_combined_net_buy,
    tag_rows_with_market,
)


def test_parse_int_accepts_positive_negative_and_blank_values():
    assert parse_int("12345") == 12345
    assert parse_int("-120") == -120
    assert parse_int("") == 0
    assert parse_int(None) == 0


def test_select_top_combined_net_buy_sorts_before_slicing():
    rows = []
    for idx in range(12):
        rows.append(
            {
                "hts_kor_isnm": f"Stock{idx}",
                "mksc_shrn_iscd": f"{idx:06d}",
                "stck_prpr": "1000",
                "frgn_ntby_qty": str(idx),
                "orgn_ntby_qty": str(idx * 10),
                "frgn_ntby_tr_pbmn": str(idx * 100),
                "orgn_ntby_tr_pbmn": str(idx * 1000),
            }
        )

    result = select_top_combined_net_buy(rows, top_n=10)

    assert len(result) == 10
    assert result[0]["mksc_shrn_iscd"] == "000011"
    assert result[-1]["mksc_shrn_iscd"] == "000002"
    assert result[0]["combined_net_buy_qty"] == 121
    assert result[0]["combined_net_buy_amount"] == 12100


def test_build_report_dataframe_formats_combined_columns():
    rows = [
        {
            "hts_kor_isnm": "Alpha",
            "mksc_shrn_iscd": "123456",
            "stck_prpr": "50000",
            "frgn_ntby_qty": "1000",
            "orgn_ntby_qty": "-250",
            "frgn_ntby_tr_pbmn": "20000",
            "orgn_ntby_tr_pbmn": "30000",
            "market": "KOSPI",
            "index_change_rate": 1.2,
            "price_change_rate": -3.45,
            "combined_net_buy_qty": 750,
            "combined_net_buy_amount": 50000,
        }
    ]

    df = build_report_dataframe(rows)

    assert isinstance(df, pd.DataFrame)
    assert df.loc[0, "현재가"] == "50,000"
    assert df.loc[0, "외국인순매수량"] == "1,000"
    assert df.loc[0, "기관순매수량"] == "-250"
    assert df.loc[0, "합산순매수량"] == "750"
    assert df.loc[0, "합산순매수금액"] == "500.0"
    assert "KOSPI" in df.loc[0, "시장대비등락률"]


def test_tag_rows_with_market_returns_copies_with_market_field():
    rows = [{"mksc_shrn_iscd": "005930"}]

    result = tag_rows_with_market(rows, "KOSPI")

    assert result == [{"mksc_shrn_iscd": "005930", "market": "KOSPI"}]
    assert rows == [{"mksc_shrn_iscd": "005930"}]
