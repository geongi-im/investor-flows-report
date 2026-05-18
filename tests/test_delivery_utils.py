import io

import pytest
from PIL import Image

import main
from main import build_delivery_metadata, deliver_results
from utils.api_util import ApiError, ApiUtil
from utils.telegram_util import TelegramUtil


def test_telegram_media_group_caption_is_only_on_first_item():
    media = TelegramUtil.build_media_group(["kospi.png", "kosdaq.png"], "report caption")

    assert media == [
        {
            "type": "photo",
            "media": "attach://photo0",
            "caption": "report caption",
            "parse_mode": "html",
        },
        {
            "type": "photo",
            "media": "attach://photo1",
            "caption": "",
            "parse_mode": "html",
        },
    ]


def test_telegram_requires_bot_token_and_chat_id(monkeypatch):
    monkeypatch.delenv("TELEGRAM_BOT_TOKEN", raising=False)
    monkeypatch.setenv("TELEGRAM_CHAT_ID", "123")

    with pytest.raises(EnvironmentError, match="TELEGRAM_BOT_TOKEN"):
        TelegramUtil()


def test_api_util_requires_base_url(monkeypatch):
    monkeypatch.delenv("BASE_URL", raising=False)

    with pytest.raises(EnvironmentError, match="BASE_URL"):
        ApiUtil()


def test_api_post_data_uses_confirmed_category(monkeypatch):
    monkeypatch.setenv("BASE_URL", "https://example.com")
    api = ApiUtil()

    data = api.build_post_data(
        title="title",
        content="content",
        category="외국인기관순매수",
        writer="admin",
    )

    assert data == {
        "title": "title",
        "content": "content",
        "category": "외국인기관순매수",
        "writer": "admin",
    }


def test_api_image_files_use_indexed_field_names(monkeypatch, tmp_path):
    monkeypatch.setenv("BASE_URL", "https://example.com")
    api = ApiUtil()

    image_paths = []
    for index in range(2):
        path = tmp_path / f"image{index}.png"
        image = Image.new("RGB", (10, 10), color=(255, 255, 255))
        image.save(path, format="PNG")
        image_paths.append(str(path))

    files = api.build_image_files(image_paths)

    assert list(files.keys()) == ["image[0]", "image[1]"]
    assert files["image[0]"][0] == "image0.png"
    assert isinstance(files["image[0]"][1], bytes)
    assert files["image[0]"][2] == "image/png"


def test_api_error_message_contains_status_and_message():
    error = ApiError(400, "bad request")

    assert "400" in str(error)
    assert "bad request" in str(error)


def test_delivery_metadata_uses_confirmed_category():
    metadata = build_delivery_metadata()

    assert metadata["category"] == "외국인기관순매수"
    assert metadata["writer"] == "admin"
    assert "외국인+기관 동반 순매수 TOP 10" in metadata["title"]


def test_delivery_preserves_api_error_when_error_notification_fails(monkeypatch):
    class FakeTelegram:
        def send_multiple_photo(self, image_paths, caption):
            return {"ok": True}

        def send_test_message(self, message):
            raise RuntimeError("test notification failed")

    class FakeApi:
        def create_post(self, **kwargs):
            raise ApiError(500, "mqway failed")

    monkeypatch.setattr(main, "TelegramUtil", lambda: FakeTelegram())
    monkeypatch.setattr(main, "ApiUtil", lambda: FakeApi())

    with pytest.raises(ApiError, match="mqway failed"):
        deliver_results(["kospi.png", "kosdaq.png"])
