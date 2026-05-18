import io
import os
from typing import Optional

import requests
from dotenv import load_dotenv
from PIL import Image

from utils.logger_util import LoggerUtil

load_dotenv()


class ApiError(Exception):
    def __init__(self, status_code: int, message: str):
        self.status_code = status_code
        self.message = message
        super().__init__(f"API Error (Status: {status_code}): {message}")


class ApiUtil:
    def __init__(self) -> None:
        base_url = os.getenv("BASE_URL")
        if not base_url:
            raise EnvironmentError("Missing environment variable: BASE_URL")

        self.api_base_url = f"{base_url.rstrip('/')}/api"
        self.headers = {"Accept": "application/json"}
        self.max_file_size = 1 * 1024 * 1024
        self.max_width = 800
        self.logger = LoggerUtil().get_logger()

    def compress_image(self, image_path: str) -> tuple[bytes, str]:
        with Image.open(image_path) as image:
            if image.width > self.max_width:
                ratio = self.max_width / image.width
                new_height = int(image.height * ratio)
                image = image.resize((self.max_width, new_height), Image.Resampling.LANCZOS)

            output_format = image.format if image.format else "PNG"
            buffer = io.BytesIO()

            if output_format == "PNG":
                image.save(buffer, format=output_format, optimize=True)
            else:
                image.save(buffer, format=output_format, quality=85, optimize=True)

            compressed_image = buffer.getvalue()
            quality = 85

            while len(compressed_image) > self.max_file_size and quality > 30:
                buffer = io.BytesIO()
                image.convert("RGB").save(buffer, format="JPEG", quality=quality, optimize=True)
                compressed_image = buffer.getvalue()
                output_format = "JPEG"
                quality -= 10

            return compressed_image, output_format.lower()

    def build_post_data(
        self, title: str, content: str, category: str, writer: str
    ) -> dict[str, str]:
        return {
            "title": title,
            "content": content,
            "category": category,
            "writer": writer,
        }

    def build_image_files(self, image_paths: list[str]) -> dict[str, tuple[str, bytes, str]]:
        files = {}
        for index, image_path in enumerate(image_paths):
            if not os.path.exists(image_path):
                self.logger.warning("이미지 경로가 존재하지 않습니다: %s", image_path)
                continue

            compressed_image, image_format = self.compress_image(image_path)
            original_filename = os.path.basename(image_path)
            files[f"image[{index}]"] = (
                original_filename,
                compressed_image,
                f"image/{image_format}",
            )
        return files

    def create_post(
        self,
        title: str,
        content: str,
        category: str,
        writer: str,
        image_paths: Optional[list[str]] = None,
        thumbnail_image_path: str | None = None,
    ) -> dict:
        url = f"{self.api_base_url}/board-research"
        data = self.build_post_data(title, content, category, writer)
        files = self.build_image_files(image_paths or [])
        intended_images = bool(image_paths)

        if thumbnail_image_path:
            if os.path.exists(thumbnail_image_path):
                compressed_image, image_format = self.compress_image(thumbnail_image_path)
                files["thumbnail_image"] = (
                    os.path.basename(thumbnail_image_path),
                    compressed_image,
                    f"image/{image_format}",
                )
            else:
                self.logger.warning("썸네일 경로가 존재하지 않습니다: %s", thumbnail_image_path)

        if intended_images and not any(key.startswith("image[") for key in files):
            raise ApiError(400, "처리 가능한 이미지가 없습니다.")

        try:
            if files:
                form_data = {key: (None, str(value)) for key, value in data.items()}
                form_data.update(files)
                response = requests.post(
                    url,
                    headers=self.headers,
                    files=form_data,
                    timeout=30,
                )
            else:
                response = requests.post(url, headers=self.headers, json=data, timeout=30)

            response.encoding = "utf-8"
            try:
                response_data = response.json()
            except ValueError as exc:
                raise ApiError(
                    response.status_code,
                    f"JSON 응답 파싱 실패\n제목: {title}\n카테고리: {category}\n응답: {response.text}",
                ) from exc

            if not response_data.get("success", False):
                raise ApiError(
                    response.status_code,
                    f"게시글 생성 실패\n제목: {title}\n카테고리: {category}\n응답: {response.text}",
                )

            return response_data
        except requests.RequestException as exc:
            raise ApiError(
                500,
                f"API 요청 중 오류 발생\n제목: {title}\n카테고리: {category}\n오류: {exc}",
            ) from exc
