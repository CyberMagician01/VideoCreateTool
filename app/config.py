import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
DB_PATH = DATA_DIR / "projects.db"

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