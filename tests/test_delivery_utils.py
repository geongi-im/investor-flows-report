import io

import pytest
from PIL import Image

import main
from main import build_delivery_metadata, deliver_results
from utils.api_util import ApiError, ApiUtil
from utils.telegram_util import TelegramUtil


def test_telegram_media_group_caption_is_only_on_first_item():
    """Telegram 미디어 그룹 캡션이 첫 번째 이미지에만 들어가는지 검증한다.

    Input:
        없음. 테스트 내부의 이미지 경로와 캡션을 사용한다.
    Output:
        None: media 배열 구조가 다르면 assertion 오류가 발생한다.
    """
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
    """TelegramUtil이 필수 Telegram 환경 변수 누락을 감지하는지 검증한다.

    Input:
        monkeypatch: 테스트용 환경 변수 변경 fixture.
    Output:
        None: 예상 예외가 발생하지 않으면 assertion 오류가 발생한다.
    """
    monkeypatch.delenv("TELEGRAM_BOT_TOKEN", raising=False)
    monkeypatch.setenv("TELEGRAM_CHAT_ID", "123")

    with pytest.raises(EnvironmentError, match="TELEGRAM_BOT_TOKEN"):
        TelegramUtil()


def test_api_util_requires_base_url(monkeypatch):
    """ApiUtil이 BASE_URL 환경 변수 누락을 감지하는지 검증한다.

    Input:
        monkeypatch: 테스트용 환경 변수 변경 fixture.
    Output:
        None: 예상 예외가 발생하지 않으면 assertion 오류가 발생한다.
    """
    monkeypatch.delenv("BASE_URL", raising=False)

    with pytest.raises(EnvironmentError, match="BASE_URL"):
        ApiUtil()


def test_api_post_data_uses_confirmed_category(monkeypatch):
    """게시글 요청 데이터에 확정된 카테고리 값이 포함되는지 검증한다.

    Input:
        monkeypatch: 테스트용 환경 변수 변경 fixture.
    Output:
        None: 요청 데이터가 기대값과 다르면 assertion 오류가 발생한다.
    """
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
    """이미지 첨부 필드명이 배열 인덱스 형식으로 만들어지는지 검증한다.

    Input:
        monkeypatch: 테스트용 환경 변수 변경 fixture.
        tmp_path: 임시 이미지 파일 생성 경로 fixture.
    Output:
        None: 파일 필드명이나 업로드 튜플 형식이 다르면 assertion 오류가 발생한다.
    """
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
    """ApiError 문자열에 상태 코드와 메시지가 포함되는지 검증한다.

    Input:
        없음. 테스트 내부에서 ApiError를 생성한다.
    Output:
        None: 예외 문자열이 기대와 다르면 assertion 오류가 발생한다.
    """
    error = ApiError(400, "bad request")

    assert "400" in str(error)
    assert "bad request" in str(error)


def test_delivery_metadata_uses_confirmed_category():
    """전달 메타데이터가 확정된 카테고리와 작성자를 사용하는지 검증한다.

    Input:
        없음. 현재 날짜 기준 메타데이터를 생성한다.
    Output:
        None: 메타데이터 값이 기대와 다르면 assertion 오류가 발생한다.
    """
    metadata = build_delivery_metadata()

    assert metadata["category"] == "외국인기관순매수"
    assert metadata["writer"] == "admin"
    assert "외국인+기관 동반 순매수 TOP 10" in metadata["title"]


def test_delivery_preserves_api_error_when_error_notification_fails(monkeypatch):
    """오류 알림 실패가 원래 API 오류를 덮어쓰지 않는지 검증한다.

    Input:
        monkeypatch: TelegramUtil과 ApiUtil을 테스트용 객체로 바꾸는 fixture.
    Output:
        None: 원래 ApiError가 유지되지 않으면 assertion 오류가 발생한다.
    """
    class FakeTelegram:
        def send_multiple_photo(self, image_paths, caption):
            """테스트용 Telegram 사진 전송 성공 응답을 반환한다.

            Input:
                image_paths: 전달된 이미지 경로 목록.
                caption: 전달된 캡션 문자열.
            Output:
                dict: 성공 형태의 Telegram 응답.
            """
            return {"ok": True}

        def send_test_message(self, message):
            """테스트용 오류 알림 전송 실패를 발생시킨다.

            Input:
                message: 전달된 오류 메시지.
            Output:
                None: 항상 RuntimeError를 발생시킨다.
            """
            raise RuntimeError("test notification failed")

    class FakeApi:
        def create_post(self, **kwargs):
            """테스트용 게시글 생성 실패를 발생시킨다.

            Input:
                kwargs: 게시글 생성 호출 인자.
            Output:
                None: 항상 ApiError를 발생시킨다.
            """
            raise ApiError(500, "mqway failed")

    monkeypatch.setattr(main, "TelegramUtil", lambda: FakeTelegram())
    monkeypatch.setattr(main, "ApiUtil", lambda: FakeApi())

    with pytest.raises(ApiError, match="mqway failed"):
        deliver_results(["kospi.png", "kosdaq.png"])
