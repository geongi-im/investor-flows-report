import pandas as pd

from investor_flows.transform import (
    build_report_dataframe,
    parse_int,
    select_top_combined_net_buy,
    tag_rows_with_market,
)


def test_parse_int_accepts_positive_negative_and_blank_values():
    """parse_int가 양수, 음수, 빈 값을 올바르게 변환하는지 검증한다.

    Input:
        없음. 테스트 내부의 고정 입력값을 사용한다.
    Output:
        None: 기대값과 다르면 assertion 오류가 발생한다.
    """
    assert parse_int("12345") == 12345
    assert parse_int("-120") == -120
    assert parse_int("") == 0
    assert parse_int(None) == 0


def test_select_top_combined_net_buy_sorts_before_slicing():
    """상위 종목을 자르기 전에 합산 순매수 기준으로 정렬하는지 검증한다.

    Input:
        없음. 테스트 내부에서 12개 종목 행을 만든다.
    Output:
        None: 정렬 및 슬라이싱 결과가 다르면 assertion 오류가 발생한다.
    """
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


def test_select_top_combined_net_buy_filters_to_positive_foreign_and_institution():
    """외국인과 기관이 모두 순매수한 행만 남기는지 검증한다.

    Input:
        없음. 테스트 내부에서 필터링 대상 행을 만든다.
    Output:
        None: 필터링 결과가 다르면 assertion 오류가 발생한다.
    """
    rows = [
        {
            "hts_kor_isnm": "ForeignOnly",
            "mksc_shrn_iscd": "000001",
            "stck_prpr": "1000",
            "frgn_ntby_qty": "999999",
            "orgn_ntby_qty": "0",
        },
        {
            "hts_kor_isnm": "InstitutionOnly",
            "mksc_shrn_iscd": "000002",
            "stck_prpr": "1000",
            "frgn_ntby_qty": "0",
            "orgn_ntby_qty": "999999",
        },
        {
            "hts_kor_isnm": "BothPositive",
            "mksc_shrn_iscd": "000003",
            "stck_prpr": "1000",
            "frgn_ntby_qty": "10",
            "orgn_ntby_qty": "20",
        },
        {
            "hts_kor_isnm": "ForeignNegative",
            "mksc_shrn_iscd": "000004",
            "stck_prpr": "1000",
            "frgn_ntby_qty": "-1",
            "orgn_ntby_qty": "999999",
        },
    ]

    result = select_top_combined_net_buy(rows, top_n=10)

    assert [row["mksc_shrn_iscd"] for row in result] == ["000003"]
    assert result[0]["combined_net_buy_qty"] == 30


def test_build_report_dataframe_formats_combined_columns():
    """보고서 DataFrame의 합산 컬럼과 표시 형식이 맞는지 검증한다.

    Input:
        없음. 테스트 내부에서 보고서 행을 만든다.
    Output:
        None: 컬럼 형식 또는 값이 다르면 assertion 오류가 발생한다.
    """
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
    assert "종목등락률(30일)" in df.columns
    assert "KOSPI" not in df.loc[0, "종목등락률(30일)"]
    assert "-3.45%" in df.loc[0, "종목등락률(30일)"]
    assert "시장대비등락률" not in df.columns


def test_tag_rows_with_market_returns_copies_with_market_field():
    """시장 태그 추가 시 원본 행을 변경하지 않고 복사본을 반환하는지 검증한다.

    Input:
        없음. 테스트 내부의 단일 행 목록을 사용한다.
    Output:
        None: 반환값 또는 원본 보존 여부가 다르면 assertion 오류가 발생한다.
    """
    rows = [{"mksc_shrn_iscd": "005930"}]

    result = tag_rows_with_market(rows, "KOSPI")

    assert result == [{"mksc_shrn_iscd": "005930", "market": "KOSPI"}]
    assert rows == [{"mksc_shrn_iscd": "005930"}]
