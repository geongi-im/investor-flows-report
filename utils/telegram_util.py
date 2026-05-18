import json
import os
import urllib.parse
from urllib.request import urlopen

import requests
from dotenv import load_dotenv

load_dotenv()


class TelegramUtil:
    def __init__(self) -> None:
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
        if not self.chat_test_id:
            return

        encoded_message = urllib.parse.quote_plus(message)
        urlopen(
            f"https://api.telegram.org/bot{self.bot_token}/sendMessage"
            f"?chat_id={self.chat_test_id}&parse_mode=html&text={encoded_message}"
        )

    def send_multiple_photo(self, photo_paths: list[str], caption: str = "") -> dict:
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
