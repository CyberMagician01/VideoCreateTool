# VideoCreateTool
一款便于您创作短剧的具有前端以及完备后端的工具，具有提示剧情以及角色等等短剧要素的功能

## .env 配置（七牛云 AK/SK）

请在项目根目录创建 `.env` 并配置：

```env
AK=你的七牛AK
SK=你的七牛SK

DEFAULT_PROVIDER=qiniu

# 七牛云文本模型网关（OpenAI 兼容）
QINIU_LLM_BASE_URL=https://api.qnaigc.com/v1
QINIU_LLM_MODEL=qwen-plus
QINIU_LLM_FALLBACK_MODELS=deepseek-v3,qwen-turbo,glm-4-flash
QINIU_TEXT_API_KEY=你的文本模型API_KEY

# 七牛云视频网关（viduq3-turbo）
QINIU_VIDEO_BASE_URL=https://api.qnaigc.com
QINIU_VIDEO_MODEL=viduq3-turbo
QINIU_VIDEO_CREATE_PATH=/queue/fal-ai/vidu/q3/text-to-video/turbo
QINIU_VIDEO_TASK_PATH_TEMPLATE=/queue/fal-ai/vidu/requests/{task_id}/status
QINIU_VIDU_Q3_TEXT_TO_VIDEO_PATH=/queue/fal-ai/vidu/q3/text-to-video/turbo
QINIU_VIDU_Q3_IMAGE_TO_VIDEO_PATH=/queue/fal-ai/vidu/q3/image-to-video/turbo
QINIU_VIDU_Q3_START_END_TO_VIDEO_PATH=/queue/fal-ai/vidu/q3/start-end-to-video/turbo
QINIU_ENABLE_ASYNC_HEADER=true
QINIU_VIDEO_API_KEY=你的视频模型API_KEY
```

请勿提交密钥到仓库，避免产生风险与费用。
