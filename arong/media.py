"""그림·사진 처리 도우미."""
from __future__ import annotations

import base64
import io

from PIL import Image, ImageOps

PHOTO_MAX = 1280  # 사진 긴 쪽 최대 픽셀 (발표 화면에 충분하고 저장 공간은 아끼는 크기)


def _flatten(img: Image.Image) -> Image.Image:
    """투명한 부분은 흰 바탕으로 채워서 RGB로 바꾼다."""
    if img.mode in ("RGBA", "LA") or (img.mode == "P" and "transparency" in img.info):
        img = img.convert("RGBA")
        bg = Image.new("RGB", img.size, (255, 255, 255))
        bg.paste(img, mask=img.split()[-1])
        return bg
    return img.convert("RGB")


def process_photo(raw: bytes) -> bytes:
    """올린 사진을 바로 세우고(휴대폰 회전 정보), 알맞게 줄여 JPEG로 만든다."""
    img = Image.open(io.BytesIO(raw))
    try:
        img.seek(0)  # 움직이는 GIF는 첫 장면만
    except EOFError:
        pass
    img = ImageOps.exif_transpose(img)
    img = _flatten(img)
    img.thumbnail((PHOTO_MAX, PHOTO_MAX))
    out = io.BytesIO()
    img.save(out, format="JPEG", quality=82, optimize=True)
    return out.getvalue()


def dataurl_to_png(data_url: str) -> bytes:
    """그림판이 보낸 data URL을 PNG 바이트로 바꾼다."""
    if not data_url or "," not in data_url:
        raise ValueError("그림 데이터가 없어요.")
    raw = base64.b64decode(data_url.split(",", 1)[1])
    img = _flatten(Image.open(io.BytesIO(raw)))
    out = io.BytesIO()
    img.save(out, format="PNG", optimize=True)
    return out.getvalue()


def bytes_to_dataurl(raw: bytes, mime: str = "image/png") -> str:
    return f"data:{mime};base64," + base64.b64encode(raw).decode("ascii")
