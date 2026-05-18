import json
import os
import urllib.parse
from urllib.request import urlopen

import requests
from dotenv import load_dotenv

load_dotenv()


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

    def send_test_message(self, message: str) -> None:
        """테스트 채팅방이 설정되어 있으면 Telegram 메시지를 전송한다.

        Input:
            message: 테스트 채팅방으로 보낼 메시지 본문.
        Output:
            None: 메시지 전송 요청을 수행한다.
        """
        if not self.chat_test_id:
            return

        encoded_message = urllib.parse.quote_plus(message)
        urlopen(
            f"https://api.telegram.org/bot{self.bot_token}/sendMessage"
            f"?chat_id={self.chat_test_id}&parse_mode=html&text={encoded_message}"
        )

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

        url = f"https://api.telegram.org/bot{self.bot_token}/sendMediaGroup"
        files = {}

        try:
            for index, photo_path in enumerate(photo_paths):
                files[f"photo{index}"] = open(photo_path, "rb")

            payload = {
                "chat_id": self.chat_id,
                "media": json.dumps(self.build_media_group(photo_paths, caption), ensure_ascii=False),
            }
            response = requests.post(url, data=payload, files=files, timeout=30)
            response_data = response.json()

            if not response_data.get("ok", False):
                raise RuntimeError(f"Telegram media group send failed: {response.text}")

            return response_data
        finally:
            for file in files.values():
                file.close()
