import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
DB_PATH = DATA_DIR / "projects.db"


def _env_int(name: str, default: int) -> int:
    value = str(os.getenv(name, str(default))).strip()
    try:
        return int(value)
    except ValueError:
        return default

QINIU_AK = os.getenv("QINIU_AK", os.getenv("AK", "")).strip()
QINIU_SK = os.getenv("QINIU_SK", os.getenv("SK", "")).strip()

QINIU_TEXT_API_KEY = os.getenv(
    "QINIU_TEXT_API_KEY",
    os.getenv("text_api_key", os.getenv("OPENAI_API_KEY", "")),
).strip()

QINIU_VIDEO_API_KEY = os.getenv(
    "QINIU_VIDEO_API_KEY",
    os.getenv("video_api_key", ""),
).strip()

QINIU_LLM_MODEL = os.getenv("QINIU_LLM_MODEL", os.getenv("QWEN_MODEL", "qwen-plus"))
QINIU_LLM_BASE_URL = os.getenv(
    "QINIU_LLM_BASE_URL",
    os.getenv("QWEN_BASE_URL", os.getenv("OPENAI_BASE_URL", "")),
).strip()
QINIU_LLM_TIMEOUT = _env_int("QINIU_LLM_TIMEOUT", 120)
QINIU_LLM_TIMEOUT_RETRIES = _env_int("QINIU_LLM_TIMEOUT_RETRIES", 1)
QINIU_IMAGE_MODEL = os.getenv("QINIU_IMAGE_MODEL", "").strip()
QINIU_IMAGE_BASE_URL = os.getenv("QINIU_IMAGE_BASE_URL", QINIU_LLM_BASE_URL).strip()
QINIU_IMAGE_GENERATE_PATH = os.getenv("QINIU_IMAGE_GENERATE_PATH", "/images/generations").strip()
QINIU_IMAGE_TASK_PATH_TEMPLATE = os.getenv("QINIU_IMAGE_TASK_PATH_TEMPLATE", "/images/tasks/{task_id}").strip()
QINIU_IMAGE_SIZE = os.getenv("QINIU_IMAGE_SIZE", "1024x1536").strip()
QINIU_IMAGE_RESPONSE_FORMAT = os.getenv("QINIU_IMAGE_RESPONSE_FORMAT", "url").strip().lower()

QINIU_VIDEO_MODEL = os.getenv("QINIU_VIDEO_MODEL", os.getenv("WAN_MODEL", "wan2.6-t2v"))
QINIU_VIDEO_BASE_URL = os.getenv(
    "QINIU_VIDEO_BASE_URL",
    os.getenv("WAN_BASE_URL", ""),
).strip()

QINIU_VIDEO_CREATE_PATH = os.getenv(
    "QINIU_VIDEO_CREATE_PATH",
    "/services/aigc/video-generation/video-synthesis",
).strip()

QINIU_VIDEO_TASK_PATH_TEMPLATE = os.getenv(
    "QINIU_VIDEO_TASK_PATH_TEMPLATE",
    "/tasks/{task_id}",
).strip()

QINIU_VIDU_Q3_TEXT_TO_VIDEO_PATH = os.getenv(
    "QINIU_VIDU_Q3_TEXT_TO_VIDEO_PATH",
    "/queue/fal-ai/vidu/q3/text-to-video/turbo",
).strip()

QINIU_VIDU_Q3_IMAGE_TO_VIDEO_PATH = os.getenv(
    "QINIU_VIDU_Q3_IMAGE_TO_VIDEO_PATH",
    "/queue/fal-ai/vidu/q3/image-to-video/turbo",
).strip()

QINIU_VIDU_Q3_START_END_TO_VIDEO_PATH = os.getenv(
    "QINIU_VIDU_Q3_START_END_TO_VIDEO_PATH",
    "/queue/fal-ai/vidu/q3/start-end-to-video/turbo",
).strip()

QINIU_WEB_SEARCH_PATH = os.getenv(
    "QINIU_WEB_SEARCH_PATH",
    "/search/web",
).strip()

QINIU_LLM_FALLBACK_MODELS = [
    item.strip()
    for item in os.getenv("QINIU_LLM_FALLBACK_MODELS", "").split(",")
    if item.strip()
]

QINIU_ENABLE_ASYNC_HEADER = os.getenv(
    "QINIU_ENABLE_ASYNC_HEADER",
    "true",
).strip().lower() in {"1", "true", "yes", "on"}

QINIU_KODO_BUCKET = os.getenv("QINIU_KODO_BUCKET", "").strip()
QINIU_KODO_PUBLIC_DOMAIN = os.getenv("QINIU_KODO_PUBLIC_DOMAIN", "").strip()
QINIU_KODO_UPLOAD_HOST = os.getenv("QINIU_KODO_UPLOAD_HOST", "https://up.qiniup.com").strip()

DEFAULT_PROVIDER = os.getenv("DEFAULT_PROVIDER", "qiniu")

MODEL_PROVIDERS = {
    "qiniu": {
        "name": "七牛云大模型网关",
        "model": QINIU_LLM_MODEL,
        "base_url": QINIU_LLM_BASE_URL,
        "type": "qiniu_openai_compatible",
        "requires_qiniu_credential": True,
    }
}

# 文本模型价格，单位：元 / 百万 tokens。实际计费时输入和输出分开算。
MODEL_PRICES_PER_1M = {
    "deepseek-v3": {"input": 2.0, "input_cache_hit": 0.5, "output": 8.0},
    "deepseek-chat": {"input": 2.0, "input_cache_hit": 0.5, "output": 8.0},
    "qwen-plus": {"input": 0.8, "output": 2.0},
    "qwen-turbo": {"input": 0.3, "output": 0.6},
    "glm-4-flash": {"input": 0.06, "output": 0.06},
    "default": {"input": 1.0, "output": 1.0},
}


def _get_model_price_per_1m(model: str) -> dict[str, float]:
    model_key = str(model or "").strip().lower()
    if model_key in MODEL_PRICES_PER_1M:
        return MODEL_PRICES_PER_1M[model_key]

    for key, price in MODEL_PRICES_PER_1M.items():
        if key != "default" and key in model_key:
            return price
    return MODEL_PRICES_PER_1M["default"]


# 兼容旧成本字段：这里保留“综合每千 tokens 单价”，新逻辑不再直接用它做精算。
MODEL_COSTS = {
    key: (price["input"] + price["output"]) / 2 / 1000
    for key, price in MODEL_PRICES_PER_1M.items()
}


# 视频模型价格，单位：元 / 秒。根据模型、分辨率、是否使用参考图分别计费。
VIDEO_PRICES_PER_SECOND = {
    "viduq3-turbo": {
        "540p": 0.25,
        "720p": 0.375,
        "1080p": 0.4375,
    },
    "kling-v1-5": {
        "720p": {"no_reference": 0.8, "with_reference": 1.2},
        "1080p": {"no_reference": 0.8, "with_reference": 1.2},
    },
    "default": {
        "720p": 0.375,
    },
}


def _normalize_video_resolution(size_or_resolution: str) -> str:
    text = str(size_or_resolution or "").strip().lower().replace("x", "*")
    mapping = {
        "540p": "540p",
        "720p": "720p",
        "1080p": "1080p",
        "960*540": "540p",
        "1280*720": "720p",
        "1920*1080": "1080p",
    }
    return mapping.get(text, "720p")


def _get_video_price_per_second(model: str, size_or_resolution: str, *, with_reference: bool = False) -> float:
    model_key = str(model or "").strip().lower()
    price_table = VIDEO_PRICES_PER_SECOND.get(model_key)
    if price_table is None:
        for key, value in VIDEO_PRICES_PER_SECOND.items():
            if key != "default" and key in model_key:
                price_table = value
                break
    if price_table is None:
        price_table = VIDEO_PRICES_PER_SECOND["default"]

    resolution = _normalize_video_resolution(size_or_resolution)
    price = price_table.get(resolution) or price_table.get("720p")
    if isinstance(price, dict):
        return float(price["with_reference"] if with_reference else price["no_reference"])
    return float(price or 0.0)


# 图片生成价格，单位：元 / 张。没有明确价格的模型默认不计入，避免虚高。
IMAGE_PRICES_PER_TASK = {
    "kling-v1-5": 0.02,
    "kling-v1-5-t2i": 0.02,
    "default": 0.0,
}


def _get_image_price_per_task(model: str) -> float:
    model_key = str(model or "").strip().lower()
    if model_key in IMAGE_PRICES_PER_TASK:
        return float(IMAGE_PRICES_PER_TASK[model_key])
    for key, price in IMAGE_PRICES_PER_TASK.items():
        if key != "default" and key in model_key:
            return float(price)
    return float(IMAGE_PRICES_PER_TASK["default"])

# 新增：降级规则，同provider下fallback models
FALLBACK_RULES = {
    "qiniu": QINIU_LLM_FALLBACK_MODELS or ["qwen-turbo"],
}
