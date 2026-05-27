"""
图片预处理服务
根据目标 API 类型，对图片进行格式转换、压缩和缩放。

Realtime API 限制：
  - 格式：必须 JPEG
  - 大小：Base64 编码后 ≤ 256KB（原始 ≤ 190KB）
  - 分辨率：推荐 480p/720p，最高 1080p

非实时 API 限制：
  - 格式：无严格限制（推荐 JPEG）
  - 大小：Base64 编码后 ≤ 10MB
  - 分辨率：按 token 计费，默认最多约 1146×1146
"""
import base64
import io
from enum import Enum

from PIL import Image


class TargetAPI(str, Enum):
    REALTIME = "realtime"
    NON_REALTIME = "non_realtime"


# Realtime 限制
REALTIME_MAX_B64_SIZE = 256 * 1024  # 256KB
REALTIME_MAX_RAW_SIZE = 190 * 1024  # 190KB
REALTIME_MAX_RESOLUTION = (1280, 720)  # 720p
REALTIME_QUALITY_START = 80

# 非实时限制
NON_REALTIME_MAX_B64_SIZE = 10 * 1024 * 1024  # 10MB
NON_REALTIME_MAX_RESOLUTION = (1920, 1080)  # 1080p
NON_REALTIME_QUALITY_START = 90


def process_image(
    image_data: bytes,
    target: TargetAPI = TargetAPI.REALTIME,
) -> str:
    """
    预处理图片，返回符合目标 API 限制的 Base64 JPEG 字符串。

    Args:
        image_data: 原始图片字节数据（任意格式）
        target: 目标 API 类型

    Returns:
        Base64 编码的 JPEG 字符串（不含 data:image/jpeg;base64, 前缀）

    Raises:
        ValueError: 图片无法压缩到目标大小
    """
    if target == TargetAPI.REALTIME:
        max_b64_size = REALTIME_MAX_B64_SIZE
        max_resolution = REALTIME_MAX_RESOLUTION
        quality_start = REALTIME_QUALITY_START
    else:
        max_b64_size = NON_REALTIME_MAX_B64_SIZE
        max_resolution = NON_REALTIME_MAX_RESOLUTION
        quality_start = NON_REALTIME_QUALITY_START

    # 1. 打开图片
    img = Image.open(io.BytesIO(image_data))

    # 2. 转 RGB（去掉 alpha 通道等）
    if img.mode not in ("RGB", "L"):
        img = img.convert("RGB")

    # 3. 缩放到最大分辨率内
    img = _resize_to_fit(img, max_resolution)

    # 4. 逐步降低质量直到满足大小限制
    quality = quality_start
    while quality >= 10:
        buffer = io.BytesIO()
        img.save(buffer, format="JPEG", quality=quality, optimize=True)
        jpeg_bytes = buffer.getvalue()
        b64_str = base64.b64encode(jpeg_bytes).decode()

        if len(b64_str) <= max_b64_size:
            return b64_str

        # 还是太大，降质量
        quality -= 10

    # 质量降到最低还是太大，继续缩小分辨率
    for scale in [0.75, 0.5, 0.35, 0.25]:
        new_size = (int(img.width * scale), int(img.height * scale))
        resized = img.resize(new_size, Image.LANCZOS)
        buffer = io.BytesIO()
        resized.save(buffer, format="JPEG", quality=50, optimize=True)
        jpeg_bytes = buffer.getvalue()
        b64_str = base64.b64encode(jpeg_bytes).decode()

        if len(b64_str) <= max_b64_size:
            return b64_str

    raise ValueError(f"图片无法压缩到 {max_b64_size // 1024}KB 以内")


def process_image_from_b64(
    image_b64: str,
    target: TargetAPI = TargetAPI.REALTIME,
) -> str:
    """
    从 Base64 字符串输入，预处理后返回符合限制的 Base64 JPEG。

    Args:
        image_b64: 输入的 Base64 图片数据（可能是 PNG/JPEG/任意格式）
        target: 目标 API 类型

    Returns:
        处理后的 Base64 JPEG 字符串
    """
    # 去掉可能的 data:image/xxx;base64, 前缀
    if "," in image_b64 and image_b64.index(",") < 100:
        image_b64 = image_b64.split(",", 1)[1]

    image_data = base64.b64decode(image_b64)

    # 如果已经满足大小限制且是 JPEG，直接返回
    if target == TargetAPI.REALTIME and len(image_b64) <= REALTIME_MAX_B64_SIZE:
        # 检查是否是 JPEG（JPEG 开头 FFD8）
        if image_data[:2] == b'\xff\xd8':
            return image_b64

    return process_image(image_data, target)


def process_image_from_path(
    file_path: str,
    target: TargetAPI = TargetAPI.REALTIME,
) -> str:
    """
    从文件路径读取图片，预处理后返回 Base64 JPEG。

    Args:
        file_path: 图片文件路径
        target: 目标 API 类型

    Returns:
        处理后的 Base64 JPEG 字符串
    """
    with open(file_path, "rb") as f:
        image_data = f.read()
    return process_image(image_data, target)


def _resize_to_fit(img: Image.Image, max_resolution: tuple) -> Image.Image:
    """等比缩放图片使其不超过 max_resolution"""
    max_w, max_h = max_resolution
    if img.width <= max_w and img.height <= max_h:
        return img

    ratio = min(max_w / img.width, max_h / img.height)
    new_size = (int(img.width * ratio), int(img.height * ratio))
    return img.resize(new_size, Image.LANCZOS)
