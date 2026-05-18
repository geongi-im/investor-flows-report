import json
import os
import re
import sys
from datetime import datetime
from typing import Any

import holidays
import imgkit
import pandas as pd
import requests
from dotenv import load_dotenv

from investor_flows.transform import (
    build_report_dataframe,
    select_top_combined_net_buy,
    tag_rows_with_market,
)
from utils.api_util import ApiError, ApiUtil
from utils.logger_util import LoggerUtil
from utils.telegram_util import TelegramUtil

load_dotenv()


def is_today_holiday() -> bool:
    return datetime.today().date() in holidays.KR()


def build_delivery_metadata(today: datetime | None = None) -> dict[str, str]:
    report_date = today or datetime.now()
    title = f"{report_date:%Y-%m-%d} 외국인+기관 동반 순매수 TOP 10"
    return {
        "title": title,
        "content": f"{title} 결과",
        "category": "외국인기관순매수",
        "writer": "admin",
    }


def deliver_results(image_paths: list[str]) -> None:
    metadata = build_delivery_metadata()
    logger = LoggerUtil().get_logger()
    telegram = TelegramUtil()

    logger.info("Telegram 메시지 전송 시작")
    telegram.send_multiple_photo(image_paths, metadata["title"])
    logger.info("Telegram 메시지 전송 완료")

    try:
        api_util = ApiUtil()
        thumbnail_path = os.path.join(
            os.path.dirname(os.path.abspath(__file__)), "thumbnail", "thumbnail.png"
        )

        logger.info("MQWAY API 포스트 생성 시작")
        api_util.create_post(
            title=metadata["title"],
            content=metadata["content"],
            category=metadata["category"],
            writer=metadata["writer"],
            image_paths=image_paths,
            thumbnail_image_path=thumbnail_path,
        )
        logger.info("MQWAY API 포스트 생성 완료")
    except ApiError as exc:
        error_message = f"API 오류 발생\n\n{exc.message}"
        try:
            telegram.send_test_message(error_message)
        except Exception as notify_error:
            logger.warning("Telegram 테스트 알림 전송 실패: %s", notify_error)
        logger.error("MQWAY API 포스트 생성 오류: %s", exc.message)
        raise


class InvestorFlowsReport:
    def __init__(self) -> None:
        self.url_base = (os.getenv("KIS_URL_BASE") or "").rstrip("/")
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
        expires_at = datetime.strptime(
            data["access_token_token_expired"], "%Y-%m-%d %H:%M:%S"
        )
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

    def get_investor_flow_rows_for_market(
        self, input_iscd: str, market: str
    ) -> list[dict[str, Any]]:
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
            "FID_INPUT_ISCD": input_iscd,
            "FID_DIV_CLS_CODE": "0",
            "FID_RANK_SORT_CLS_CODE": "0",
            "FID_ETC_CLS_CODE": "0",
        }
        response = requests.get(url, headers=headers, params=params, timeout=30)
        body = response.json()
        if response.status_code == 200 and body.get("rt_cd") == "0":
            return tag_rows_with_market(body.get("output", []), market)

        message = body.get("msg_cd") or body.get("msg1") or response.text
        raise RuntimeError(f"KIS investor flow request failed for {market}: {message}")

    def get_investor_flow_rows(self) -> list[dict[str, Any]]:
        rows = []
        rows.extend(self.get_investor_flow_rows_for_market("0001", "KOSPI"))
        rows.extend(self.get_investor_flow_rows_for_market("1001", "KOSDAQ"))
        return rows

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

    def add_historical_price_change(
        self, rows: list[dict[str, Any]], reference_date: str
    ) -> list[dict[str, Any]]:
        result = []
        for row in rows:
            item = row.copy()
            current_price = int(str(item["stck_prpr"]).replace(",", ""))
            try:
                price_df = self.get_stock_price(
                    item["mksc_shrn_iscd"], reference_date, reference_date
                )
                historical_price = float(price_df.iloc[0]["close"]) if not price_df.empty else 0
                item["historical_price"] = int(historical_price)
                item["price_change_rate"] = (
                    round(((current_price - historical_price) / historical_price) * 100, 2)
                    if historical_price > 0
                    else 0
                )
            except Exception as exc:
                self.logger.warning(
                    "Historical price lookup failed for %s: %s",
                    item["mksc_shrn_iscd"],
                    exc,
                )
                item["historical_price"] = 0
                item["price_change_rate"] = 0
            result.append(item)
        return result

    def calculate_30day_rate(self, df: pd.DataFrame, label: str) -> float:
        if len(df) < 30:
            raise RuntimeError(f"At least 30 {label} rows are required to compute 30-day rates.")

        return round(
            ((df.iloc[0]["close"] - df.iloc[29]["close"]) / df.iloc[29]["close"]) * 100,
            2,
        )

    def format_rate(self, value: float) -> str:
        if value < 0:
            return f"<span class='negative'>{value:.2f}%</span>"
        if value > 0:
            return f"<span class='positive'>{value:.2f}%</span>"
        return f"{value:.2f}%"

    def save_df_as_image(
        self,
        df: pd.DataFrame,
        market: str,
        market_index_change_rate: float,
        file_name: str,
    ) -> str:
        if df.empty:
            raise ValueError("Cannot render an empty DataFrame.")
        if not self.wkhtmltoimage_path:
            raise EnvironmentError("WKHTMLTOIMAGE_PATH is required for image generation.")

        current_date = datetime.now().strftime("%Y%m%d")
        file_path = os.path.join(self.img_dir, f"{file_name}_{current_date}.png")

        for old_file in os.listdir(self.img_dir):
            if old_file.startswith(file_name) and old_file.endswith(".png"):
                os.remove(os.path.join(self.img_dir, old_file))

        caption = f"{datetime.now():%Y-%m-%d} {market} 외국인+기관 동반 순매수 TOP 10"
        market_summary = (
            f"시장지표(30일): <strong>{market}</strong> "
            f"{self.format_rate(market_index_change_rate)}"
        )
        df_html = df.to_html(index=False, classes="styled-table", escape=False)
        df_html = df_html.replace(">합산순매수금액<", ">합산순매수금액<br>(억원)<")
        df_html = df_html.replace("<th>종목명</th>", '<th class="stock-name">종목명</th>')
        df_html = re.sub(
            r"(<tr[^>]*>)\s*<td([^>]*)>", r'\1<td class="stock-name"\2>', df_html
        )

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
                .market-summary {{ text-align: right; font-size: 13px; font-weight: 600; margin: 0 0 10px; color: #333333; }}
                .source {{ text-align: right; font-size: 11px; color: #666666; margin-top: 10px; }}
                .positive {{ color: #d32f2f; }}
                .negative {{ color: #1976d2; }}
            </style>
        </head>
        <body>
            <div class="caption">{caption}</div>
            <div class="market-summary">{market_summary}</div>
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

    def build_market_report(
        self,
        market: str,
        input_iscd: str,
        index_df: pd.DataFrame,
        file_name: str,
    ) -> str:
        market_index_change_rate = self.calculate_30day_rate(index_df, market)
        reference_date = index_df.iloc[29]["date"].strftime("%Y%m%d")

        rows = self.get_investor_flow_rows_for_market(input_iscd, market)
        top_rows = select_top_combined_net_buy(rows, top_n=10)
        top_rows = self.add_historical_price_change(top_rows, reference_date)
        df = build_report_dataframe(top_rows)
        return self.save_df_as_image(
            df=df,
            market=market,
            market_index_change_rate=market_index_change_rate,
            file_name=file_name,
        )

    def run(self) -> list[str]:
        today = datetime.now().strftime("%Y%m%d")
        self.logger.info("Investor flows report started.")

        kospi_df = self.get_domestic_index("KOSPI", today)
        kosdaq_df = self.get_domestic_index("KOSDAQ", today)

        image_paths = [
            self.build_market_report(
                market="KOSPI",
                input_iscd="0001",
                index_df=kospi_df,
                file_name="investor_flows_kospi_top_report",
            ),
            self.build_market_report(
                market="KOSDAQ",
                input_iscd="1001",
                index_df=kosdaq_df,
                file_name="investor_flows_kosdaq_top_report",
            ),
        ]

        self.logger.info("Investor flows report images saved: %s", image_paths)
        return image_paths


if __name__ == "__main__":
    logger = LoggerUtil().get_logger()
    try:
        if is_today_holiday():
            logger.info("Today is a Korean market holiday. Exiting.")
            sys.exit(0)
        paths = InvestorFlowsReport().run()
        deliver_results(paths)
        for path in paths:
            print(path)
    except Exception as exc:
        logger.exception("Report failed: %s", exc)
        sys.exit(1)
