# Investor Flows Report Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a local Python report that selects the top 10 stocks by combined foreign plus institutional net buy quantity and renders the result as a PNG image.

**Architecture:** Keep pure ranking and formatting logic in `investor_flows/transform.py` so it can be tested without KIS credentials. Keep KIS token/API calls, market/index enrichment, and image rendering in `main.py`, following the existing reference project structure but excluding Telegram and board post integrations.

**Tech Stack:** Python 3, pandas, requests, python-dotenv, imgkit, holidays, pytest.

---

## File Structure

- Create `.gitignore`: exclude local credentials, generated images, logs, caches, and virtual environments.
- Create `.env.sample`: document KIS and wkhtmltoimage environment variables.
- Create `requirements.txt`: runtime and test dependencies.
- Create `token.json.sample`: sample token cache shape.
- Create `utils/logger_util.py`: shared logger setup.
- Create `utils/__init__.py`: package marker.
- Create `investor_flows/__init__.py`: package marker.
- Create `investor_flows/transform.py`: pure numeric parsing, combined flow enrichment, sorting, top-N selection, and report DataFrame creation.
- Create `tests/test_transform.py`: focused tests for pure logic.
- Create `main.py`: executable script that calls KIS separately for KOSPI and KOSDAQ, enriches selected rows, and writes the PNG image.

## Task 1: Repository Baseline

**Files:**
- Create: `.gitignore`
- Create: `.env.sample`
- Create: `requirements.txt`
- Create: `token.json.sample`
- Create: `utils/__init__.py`
- Create: `investor_flows/__init__.py`

- [ ] **Step 1: Create baseline project files**

Create `.gitignore`:

```gitignore
.env
token.json
__pycache__/
*.py[cod]
.pytest_cache/
.venv/
venv/
logs/
img/*.png
img/*.jpg
img/*.jpeg
img/*.webp
```

Create `.env.sample`:

```dotenv
KIS_APP_KEY=your_app_key_here
KIS_APP_SECRET=your_app_secret_here
KIS_URL_BASE=https://openapi.koreainvestment.com:9443
WKHTMLTOIMAGE_PATH=C:\\Program Files\\wkhtmltopdf\\bin\\wkhtmltoimage.exe
```

Create `requirements.txt`:

```text
requests
python-dotenv
pandas
imgkit
holidays
pytest
```

Create `token.json.sample`:

```json
{
  "access_token": "your_access_token_here",
  "expires_in": 86400,
  "access_token_token_expired": "2099-12-31 23:59:59"
}
```

Create empty package files:

```python
# utils/__init__.py
```

```python
# investor_flows/__init__.py
```

- [ ] **Step 2: Commit baseline files**

Run:

```bash
git add .gitignore .env.sample requirements.txt token.json.sample utils/__init__.py investor_flows/__init__.py
git commit -m "chore: add project baseline"
```

Expected: commit succeeds on branch `main`.

## Task 2: Combined Flow Transform Logic

**Files:**
- Create: `tests/test_transform.py`
- Create: `investor_flows/transform.py`

- [ ] **Step 1: Write failing tests**

Create `tests/test_transform.py`:

```python
import pandas as pd

from investor_flows.transform import (
    build_report_dataframe,
    parse_int,
    select_top_combined_net_buy,
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
```

- [ ] **Step 2: Run tests to verify they fail**

Run:

```bash
pytest tests/test_transform.py -v
```

Expected: FAIL during import because `investor_flows.transform` does not exist.

- [ ] **Step 3: Implement transform module**

Create `investor_flows/transform.py`:

```python
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


def select_top_combined_net_buy(rows: Iterable[dict[str, Any]], top_n: int = 10) -> list[dict[str, Any]]:
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
    result_df["합산순매수량"] = [f"{parse_int(row.get('combined_net_buy_qty')):,}" for row in rows]
    result_df["합산순매수금액"] = [
        f"{round(parse_int(row.get('combined_net_buy_amount')) / 100, 2):,}"
        for row in rows
    ]
    return result_df
```

- [ ] **Step 4: Run tests to verify they pass**

Run:

```bash
pytest tests/test_transform.py -v
```

Expected: 3 tests pass.

- [ ] **Step 5: Commit transform logic**

Run:

```bash
git add investor_flows/transform.py tests/test_transform.py
git commit -m "feat: add combined investor flow ranking"
```

Expected: commit succeeds.

## Task 3: Logger Utility

**Files:**
- Create: `utils/logger_util.py`

- [ ] **Step 1: Create logger utility**

Create `utils/logger_util.py`:

```python
import logging
import os
from datetime import datetime


class LoggerUtil:
    _logger = None

    def __init__(self, name: str = "investor_flows_report"):
        if LoggerUtil._logger is None:
            LoggerUtil._logger = self._create_logger(name)

    def _create_logger(self, name: str) -> logging.Logger:
        logger = logging.getLogger(name)
        logger.setLevel(logging.DEBUG)

        if logger.handlers:
            return logger

        formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        )

        stream_handler = logging.StreamHandler()
        stream_handler.setLevel(logging.INFO)
        stream_handler.setFormatter(formatter)
        logger.addHandler(stream_handler)

        log_dir = os.path.join(os.getcwd(), "logs")
        os.makedirs(log_dir, exist_ok=True)
        log_file = os.path.join(log_dir, f"investor_flows_{datetime.now():%Y%m%d}.log")

        file_handler = logging.FileHandler(log_file, encoding="utf-8")
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

        return logger

    def get_logger(self) -> logging.Logger:
        return LoggerUtil._logger
```

- [ ] **Step 2: Smoke check logger import**

Run:

```bash
python -c "from utils.logger_util import LoggerUtil; LoggerUtil().get_logger().info('logger ok')"
```

Expected: command exits 0 and prints `logger ok`.

- [ ] **Step 3: Commit logger utility**

Run:

```bash
git add utils/logger_util.py
git commit -m "chore: add logger utility"
```

Expected: commit succeeds.

## Task 4: KIS Report Script and Image Rendering

**Files:**
- Create: `main.py`

- [ ] **Step 1: Create executable report script**

Create `main.py` with:

```python
import json
import os
import re
import sys
from datetime import datetime
from typing import Any

import FinanceDataReader as fdr
import holidays
import imgkit
import pandas as pd
import requests
from dotenv import load_dotenv

from investor_flows.transform import build_report_dataframe, select_top_combined_net_buy
from utils.logger_util import LoggerUtil

load_dotenv()

_cached_kospi_tickers: list[str] | None = None
_cached_kosdaq_tickers: list[str] | None = None


def check_market(ticker: str) -> str:
    global _cached_kospi_tickers, _cached_kosdaq_tickers

    code = str(ticker).strip().zfill(6)
    if _cached_kospi_tickers is None:
        _cached_kospi_tickers = fdr.StockListing("KOSPI")["Code"].tolist()
    if _cached_kosdaq_tickers is None:
        _cached_kosdaq_tickers = fdr.StockListing("KOSDAQ")["Code"].tolist()

    if code in _cached_kospi_tickers:
        return "KOSPI"
    if code in _cached_kosdaq_tickers:
        return "KOSDAQ"
    return "Not Found"


def is_today_holiday() -> bool:
    return datetime.today().date() in holidays.KR()


class InvestorFlowsReport:
    def __init__(self) -> None:
        self.url_base = os.getenv("KIS_URL_BASE")
        self.app_key = os.getenv("KIS_APP_KEY")
        self.app_secret = os.getenv("KIS_APP_SECRET")
        self.token_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), "token.json")
        self.img_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "img")
        self.wkhtmltoimage_path = os.getenv("WKHTMLTOIMAGE_PATH")
        self.logger = LoggerUtil().get_logger()

        os.makedirs(self.img_dir, exist_ok=True)

    def check_env_variables(self) -> None:
        required_vars = ["KIS_APP_KEY", "KIS_APP_SECRET", "KIS_URL_BASE"]
        missing_vars = [var for var in required_vars if not os.getenv(var)]
        if missing_vars:
            raise EnvironmentError(f"Missing environment variables: {', '.join(missing_vars)}")

    def load_token(self) -> str | None:
        if not os.path.exists(self.token_file):
            return None

        with open(self.token_file, "r", encoding="utf-8") as file:
            data = json.load(file)

        now = datetime.now()
        expires_at = datetime.strptime(data["access_token_token_expired"], "%Y-%m-%d %H:%M:%S")
        if expires_at <= now:
            return None

        return data["access_token"]

    def save_token(self, token_info: dict[str, Any]) -> None:
        data = {
            "access_token": token_info["access_token"],
            "expires_in": token_info["expires_in"],
            "access_token_token_expired": token_info["access_token_token_expired"],
        }
        with open(self.token_file, "w", encoding="utf-8") as file:
            json.dump(data, file)

    def get_token(self) -> str:
        self.check_env_variables()

        token = self.load_token()
        if token:
            return token

        headers = {"content-type": "application/json"}
        body = {
            "grant_type": "client_credentials",
            "appkey": self.app_key,
            "appsecret": self.app_secret,
        }
        url = f"{self.url_base}/oauth2/tokenP"
        response = requests.post(url, headers=headers, data=json.dumps(body), timeout=30)
        if response.status_code != 200:
            raise RuntimeError(f"Token request failed: {response.status_code} {response.text}")

        token_info = response.json()
        self.save_token(token_info)
        return token_info["access_token"]

    def get_investor_flow_rows(self) -> list[dict[str, Any]]:
        token = self.get_token()
        url = f"{self.url_base}/uapi/domestic-stock/v1/quotations/foreign-institution-total"
        headers = {
            "Content-Type": "application/json; charset=utf-8",
            "authorization": f"Bearer {token}",
            "appKey": self.app_key,
            "appSecret": self.app_secret,
            "tr_id": "FHPTJ04400000",
        }
        params = {
            "FID_COND_MRKT_DIV_CODE": "V",
            "FID_COND_SCR_DIV_CODE": "16449",
            "FID_INPUT_ISCD": "0000",
            "FID_DIV_CLS_CODE": "0",
            "FID_RANK_SORT_CLS_CODE": "0",
            "FID_ETC_CLS_CODE": "0",
        }
        response = requests.get(url, headers=headers, params=params, timeout=30)
        body = response.json()
        if response.status_code == 200 and body.get("rt_cd") == "0":
            return body.get("output", [])

        message = body.get("msg_cd") or body.get("msg1") or response.text
        raise RuntimeError(f"KIS investor flow request failed: {message}")

    def get_stock_price(self, stock_code: str, start_date: str, end_date: str) -> pd.DataFrame:
        token = self.get_token()
        url = f"{self.url_base}/uapi/domestic-stock/v1/quotations/inquire-daily-itemchartprice"
        headers = {
            "Content-Type": "application/json; charset=utf-8",
            "authorization": f"Bearer {token}",
            "appKey": self.app_key,
            "appSecret": self.app_secret,
            "tr_id": "FHKST03010100",
        }
        params = {
            "FID_COND_MRKT_DIV_CODE": "J",
            "FID_INPUT_ISCD": stock_code,
            "FID_INPUT_DATE_1": start_date,
            "FID_INPUT_DATE_2": end_date,
            "FID_PERIOD_DIV_CODE": "D",
            "FID_ORG_ADJ_PRC": "1",
        }
        response = requests.get(url, headers=headers, params=params, timeout=30)
        body = response.json()
        if response.status_code != 200 or body.get("rt_cd") != "0":
            message = body.get("msg_cd") or body.get("msg1") or response.text
            raise RuntimeError(f"KIS stock price request failed for {stock_code}: {message}")

        df = pd.DataFrame(body.get("output2", []))
        if df.empty:
            return df

        df = df[["stck_bsop_date", "stck_clpr"]].rename(
            columns={"stck_bsop_date": "date", "stck_clpr": "close"}
        )
        df["date"] = pd.to_datetime(df["date"], format="%Y%m%d")
        df["close"] = pd.to_numeric(df["close"], errors="coerce")
        return df.sort_values(by="date", ascending=False).reset_index(drop=True)

    def get_domestic_index(self, market_code: str, date: str) -> pd.DataFrame:
        token = self.get_token()
        market_input_code = {"KOSPI": "0001", "KOSDAQ": "1001"}[market_code]
        url = f"{self.url_base}/uapi/domestic-stock/v1/quotations/inquire-index-daily-price"
        headers = {
            "Content-Type": "application/json; charset=utf-8",
            "authorization": f"Bearer {token}",
            "appKey": self.app_key,
            "appSecret": self.app_secret,
            "tr_id": "FHPUP02120000",
        }
        params = {
            "FID_COND_MRKT_DIV_CODE": "U",
            "FID_INPUT_ISCD": market_input_code,
            "FID_INPUT_DATE_1": date,
            "FID_PERIOD_DIV_CODE": "D",
        }
        response = requests.get(url, headers=headers, params=params, timeout=30)
        body = response.json()
        if response.status_code != 200 or body.get("rt_cd") != "0":
            message = body.get("msg_cd") or body.get("msg1") or response.text
            raise RuntimeError(f"KIS index request failed for {market_code}: {message}")

        df = pd.DataFrame(body.get("output2", []))
        if df.empty:
            return df

        df = df[["stck_bsop_date", "bstp_nmix_prpr"]].rename(
            columns={"stck_bsop_date": "date", "bstp_nmix_prpr": "close"}
        )
        df["date"] = pd.to_datetime(df["date"], format="%Y%m%d")
        df["close"] = pd.to_numeric(df["close"], errors="coerce")
        return df.sort_values(by="date", ascending=False).reset_index(drop=True)

    def add_historical_price_change(self, rows: list[dict[str, Any]], reference_date: str) -> list[dict[str, Any]]:
        result = []
        for row in rows:
            item = row.copy()
            current_price = int(str(item["stck_prpr"]).replace(",", ""))
            try:
                price_df = self.get_stock_price(item["mksc_shrn_iscd"], reference_date, reference_date)
                historical_price = float(price_df.iloc[0]["close"]) if not price_df.empty else 0
                item["historical_price"] = int(historical_price)
                item["price_change_rate"] = (
                    round(((current_price - historical_price) / historical_price) * 100, 2)
                    if historical_price > 0
                    else 0
                )
            except Exception as exc:
                self.logger.warning("Historical price lookup failed for %s: %s", item["mksc_shrn_iscd"], exc)
                item["historical_price"] = 0
                item["price_change_rate"] = 0
            result.append(item)
        return result

    def add_market_info(self, rows: list[dict[str, Any]], kospi_rate: float, kosdaq_rate: float) -> list[dict[str, Any]]:
        result = []
        for row in rows:
            item = row.copy()
            market = check_market(item["mksc_shrn_iscd"])
            item["market"] = market
            if market == "KOSPI":
                item["index_change_rate"] = kospi_rate
            elif market == "KOSDAQ":
                item["index_change_rate"] = kosdaq_rate
            else:
                item["index_change_rate"] = 0
            result.append(item)
        return result

    def save_df_as_image(self, df: pd.DataFrame, file_name: str = "investor_flows_top_report") -> str:
        if df.empty:
            raise ValueError("Cannot render an empty DataFrame.")
        if not self.wkhtmltoimage_path:
            raise EnvironmentError("WKHTMLTOIMAGE_PATH is required for image generation.")

        current_date = datetime.now().strftime("%Y%m%d")
        file_path = os.path.join(self.img_dir, f"{file_name}_{current_date}.png")

        for old_file in os.listdir(self.img_dir):
            if old_file.startswith(file_name) and old_file.endswith(".png"):
                os.remove(os.path.join(self.img_dir, old_file))

        caption = f"{datetime.now():%Y-%m-%d} 외국인+기관 합산 순매수 상위 TOP 10"
        df_html = df.to_html(index=False, classes="styled-table", escape=False)
        df_html = df_html.replace(">시장대비등락률<", ">시장대비등락률<br>(30일기준)<")
        df_html = df_html.replace(">합산순매수금액<", ">합산순매수금액<br>(억원)<")
        df_html = df_html.replace("<th>종목명</th>", '<th class="stock-name">종목명</th>')
        df_html = re.sub(r"(<tr[^>]*>)\s*<td([^>]*)>", r'\1<td class="stock-name"\2>', df_html)

        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <link href="https://fonts.googleapis.com/css2?family=Noto+Sans+KR:wght@400;500;700&display=swap" rel="stylesheet">
            <style>
                body {{ font-family: 'Noto Sans KR', sans-serif; margin: 10px; max-width: 760px; }}
                table {{ border-collapse: collapse; width: 100%; margin: 10px auto; box-shadow: 0 1px 3px rgba(0,0,0,0.1); }}
                th, td {{ border: 1px solid #e0e0e0; padding: 8px 9px; text-align: center; }}
                th {{ background-color: #333333; color: white; font-weight: 700; font-size: 12px; white-space: nowrap; }}
                td {{ font-size: 12px; font-weight: 500; }}
                td.stock-name {{ text-align: center; min-width: 92px; }}
                .stock-code {{ font-size: 10px; color: #666; display: block; margin-top: 2px; }}
                tr:nth-child(even) td {{ background-color: #f9f9f9; }}
                .caption {{ text-align: center; font-size: 18px; font-weight: 700; margin: 15px 0; color: #333333; }}
                .source {{ text-align: right; font-size: 11px; color: #666666; margin-top: 10px; }}
                .positive {{ color: #d32f2f; }}
                .negative {{ color: #1976d2; }}
            </style>
        </head>
        <body>
            <div class="caption">{caption}</div>
            {df_html}
            <div class="source">※ 출처 : 한국투자증권 Open API, MQ(Money Quotient)</div>
        </body>
        </html>
        """

        options = {
            "format": "png",
            "encoding": "UTF-8",
            "quality": 100,
            "width": 760,
            "enable-local-file-access": None,
            "minimum-font-size": 10,
        }
        config = imgkit.config(wkhtmltoimage=self.wkhtmltoimage_path)
        imgkit.from_string(html, file_path, options=options, config=config)
        return file_path

    def run(self) -> str:
        today = datetime.now().strftime("%Y%m%d")
        self.logger.info("Investor flows report started.")

        rows = self.get_investor_flow_rows()
        top_rows = select_top_combined_net_buy(rows, top_n=10)

        kospi_df = self.get_domestic_index("KOSPI", today)
        kosdaq_df = self.get_domestic_index("KOSDAQ", today)
        if len(kospi_df) < 30 or len(kosdaq_df) < 30:
            raise RuntimeError("At least 30 index rows are required to compute 30-day rates.")

        kospi_rate = round(((kospi_df.iloc[0]["close"] - kospi_df.iloc[29]["close"]) / kospi_df.iloc[29]["close"]) * 100, 2)
        kosdaq_rate = round(((kosdaq_df.iloc[0]["close"] - kosdaq_df.iloc[29]["close"]) / kosdaq_df.iloc[29]["close"]) * 100, 2)
        reference_date = kospi_df.iloc[29]["date"].strftime("%Y%m%d")

        top_rows = self.add_historical_price_change(top_rows, reference_date)
        top_rows = self.add_market_info(top_rows, kospi_rate, kosdaq_rate)
        df = build_report_dataframe(top_rows)
        image_path = self.save_df_as_image(df)

        self.logger.info("Investor flows report image saved: %s", image_path)
        return image_path


if __name__ == "__main__":
    logger = LoggerUtil().get_logger()
    try:
        if is_today_holiday():
            logger.info("Today is a Korean market holiday. Exiting.")
            sys.exit(0)
        path = InvestorFlowsReport().run()
        print(path)
    except Exception as exc:
        logger.exception("Report failed: %s", exc)
        sys.exit(1)
```

- [ ] **Step 2: Run existing tests**

Run:

```bash
pytest tests/test_transform.py -v
```

Expected: tests still pass.

- [ ] **Step 3: Compile Python files**

Run:

```bash
python -m compileall main.py investor_flows utils tests
```

Expected: command exits 0.

- [ ] **Step 4: Commit report script**

Run:

```bash
git add main.py
git commit -m "feat: render investor flows report image"
```

Expected: commit succeeds.

## Task 5: Final Verification

**Files:**
- Read: `docs/superpowers/specs/2026-05-18-investor-flows-report-design.md`
- Read: `docs/superpowers/plans/2026-05-18-investor-flows-report.md`

- [ ] **Step 1: Run full automated verification**

Run:

```bash
pytest -v
```

Expected: all tests pass.

- [ ] **Step 2: Run compile verification**

Run:

```bash
python -m compileall main.py investor_flows utils tests
```

Expected: command exits 0.

- [ ] **Step 3: Inspect git status**

Run:

```bash
git status --short --branch
```

Expected: only intentionally untracked local files remain, such as `reference.lnk`; project source changes are committed or staged intentionally.

- [ ] **Step 4: Report runtime caveat**

State that live image generation requires real `.env`, valid KIS credentials, `token.json` generation, and a valid `WKHTMLTOIMAGE_PATH`. Do not claim live API/image generation succeeded unless `python main.py` was run successfully.
