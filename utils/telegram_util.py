import json
import logging
import os
import time
from contextlib import ExitStack

import requests
from dotenv import load_dotenv

load_dotenv()

# logger_util.LoggerUtil 이 파일/콘솔 핸들러를 붙이는 로거 이름
logger = logging.getLogger("investor_flows_report")

API_BASE_URL = "https://api.telegram.org"
CONNECT_TIMEOUT_SECONDS = 10
READ_TIMEOUT_SECONDS = 60
MAX_ATTEMPTS = 3
RETRY_BACKOFF_SECONDS = 2
MAX_RETRY_AFTER_SECONDS = 60
RETRYABLE_STATUS_CODES = {429, 500, 502, 503, 504}


class TelegramSendError(RuntimeError):
    """Telegram 이 전송을 거부했거나 재시도 후에도 응답을 받지 못한 경우 발생한다."""


class TelegramUtil:
    def __init__(self) -> None:
        """Telegram 전송에 필요한 환경 변수를 읽고 검증한다.

        Input:
            없음.
        Output:
            None: 봇 토큰과 채팅 ID를 인스턴스 속성에 설정한다.
        """
        self.bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
        self.chat_id = os.getenv("TELEGRAM_CHAT_ID")
        self.chat_test_id = os.getenv("TELEGRAM_CHAT_TEST_ID")

        missing = []
        if not self.bot_token:
            missing.append("TELEGRAM_BOT_TOKEN")
        if not self.chat_id:
            missing.append("TELEGRAM_CHAT_ID")
        if missing:
            raise EnvironmentError(f"Missing environment variables: {', '.join(missing)}")

    @staticmethod
    def build_media_group(photo_paths: list[str], caption: str = "") -> list[dict[str, str]]:
        """Telegram sendMediaGroup 요청에 사용할 media 배열을 만든다.

        Input:
            photo_paths: 전송할 이미지 파일 경로 목록.
            caption: 첫 번째 이미지에만 붙일 캡션.
        Output:
            list[dict[str, str]]: Telegram API media 파라미터용 딕셔너리 목록.
        """
        media = []
        for index, _photo_path in enumerate(photo_paths):
            media.append(
                {
                    "type": "photo",
                    "media": f"attach://photo{index}",
                    "caption": caption if index == 0 else "",
                    "parse_mode": "html",
                }
            )
        return media

    def _request(self, method: str, data: dict, open_files=None) -> dict:
        """Telegram Bot API 를 호출하고 네트워크 오류/429/5xx 는 재시도한다.

        재시도할 때 파일 포인터가 끝에 가 있으면 빈 파일이 올라가므로 open_files 로 매번 다시 연다.
        읽기 타임아웃 뒤 재시도하면 이미 도착한 메시지가 한 번 더 갈 수 있다.

        Input:
            method: Telegram API 메서드 이름.
            data: 요청 본문.
            open_files: ExitStack 을 받아 새로 연 파일 dict 를 돌려주는 함수.
        Output:
            dict: 마지막 Telegram 응답. JSON 이 아니면 ok=False 형태로 맞춘다.
        """
        url = f"{API_BASE_URL}/bot{self.bot_token}/{method}"
        last_error = None

        for attempt in range(1, MAX_ATTEMPTS + 1):
            wait_seconds = RETRY_BACKOFF_SECONDS * attempt
            try:
                with ExitStack() as stack:
                    files = open_files(stack) if open_files else None
                    response = requests.post(
                        url,
                        data=data,
                        files=files,
                        timeout=(CONNECT_TIMEOUT_SECONDS, READ_TIMEOUT_SECONDS),
                    )
            except (requests.ConnectionError, requests.Timeout) as e:
                last_error = self._mask_token(e)
                logger.warning("Telegram %s 네트워크 오류(%s/%s): %s", method, attempt, MAX_ATTEMPTS, last_error)
            else:
                result = self._parse_response(response)
                if result.get("ok") or response.status_code not in RETRYABLE_STATUS_CODES:
                    return result
                retry_after = (result.get("parameters") or {}).get("retry_after")
                if retry_after:
                    wait_seconds = min(int(retry_after) + 1, MAX_RETRY_AFTER_SECONDS)
                logger.warning(
                    "Telegram %s 응답 오류(%s/%s): status=%s %s",
                    method, attempt, MAX_ATTEMPTS, response.status_code, result.get("description"),
                )
                if attempt == MAX_ATTEMPTS:
                    return result

            if attempt < MAX_ATTEMPTS:
                time.sleep(wait_seconds)

        # 원래 예외를 체인으로 달면 traceback 에 토큰이 든 URL 이 그대로 찍힌다
        raise TelegramSendError(f"Telegram {method} 전송 실패: {last_error}") from None

    def _mask_token(self, error: Exception) -> str:
        """requests 예외 메시지에 들어 있는 봇 토큰을 가린다.

        Input:
            error: requests 네트워크 예외.
        Output:
            str: 토큰을 *** 로 바꾼 예외 설명.
        """
        text = f"{type(error).__name__}: {error}"
        if self.bot_token:
            text = text.replace(self.bot_token, "***")
        return text

    @staticmethod
    def _parse_response(response: requests.Response) -> dict:
        """Telegram 응답을 dict 로 읽는다. 프록시 오류 페이지처럼 JSON 이 아니면 ok=False 로 맞춘다.

        Input:
            response: requests 응답 객체.
        Output:
            dict: Telegram 형식의 응답 데이터.
        """
        try:
            result = response.json()
        except ValueError:
            result = None
        if not isinstance(result, dict):
            result = {
                "ok": False,
                "error_code": response.status_code,
                "description": response.text[:300],
            }
        return result

    def send_test_message(self, message: str) -> None:
        """테스트 채팅방이 설정되어 있으면 Telegram 메시지를 전송한다.

        Input:
            message: 테스트 채팅방으로 보낼 메시지 본문.
        Output:
            None: 메시지 전송 요청을 수행한다. 실패하면 TelegramSendError 를 던진다.
        """
        if not self.chat_test_id:
            return

        result = self._request(
            "sendMessage",
            {"chat_id": self.chat_test_id, "parse_mode": "html", "text": message},
        )
        if not result.get("ok"):
            raise TelegramSendError(f"Telegram sendMessage 실패: {str(result)[:300]}")

    def send_multiple_photo(self, photo_paths: list[str], caption: str = "") -> dict:
        """여러 이미지를 하나의 Telegram 미디어 그룹으로 전송한다.

        Input:
            photo_paths: 전송할 이미지 파일 경로 목록.
            caption: 미디어 그룹 첫 이미지에 표시할 캡션.
        Output:
            dict: Telegram API의 JSON 응답 데이터.
        """
        if not photo_paths:
            raise ValueError("photo_paths must contain at least one image.")

        payload = {
            "chat_id": self.chat_id,
            "media": json.dumps(self.build_media_group(photo_paths, caption), ensure_ascii=False),
        }
        response_data = self._request(
            "sendMediaGroup",
            payload,
            lambda stack: {
                f"photo{index}": stack.enter_context(open(photo_path, "rb"))
                for index, photo_path in enumerate(photo_paths)
            },
        )

        if not response_data.get("ok", False):
            raise TelegramSendError(f"Telegram media group send failed: {str(response_data)[:300]}")

        return response_data
