# VideoCreateTool
一款便于您创作短剧的具有前端以及完备后端的工具，具有提示剧情以及角色等等短剧要素的功能

## .env 配置（七牛云 AK/SK）

请在项目根目录创建 `.env` 并配置：

```env
QINIU_AK=你的七牛AK
QINIU_SK=你的七牛SK

# 文本模型网关（OpenAI 兼容）
QINIU_LLM_BASE_URL=https://你的七牛网关地址/compatible-mode/v1
QINIU_LLM_MODEL=qwen-plus

# 视频网关
QINIU_VIDEO_BASE_URL=https://你的七牛网关地址/api/v1
QINIU_VIDEO_MODEL=wan2.6-t2v
QINIU_VIDEO_CREATE_PATH=/services/aigc/video-generation/video-synthesis
QINIU_VIDEO_TASK_PATH_TEMPLATE=/tasks/{task_id}
QINIU_ENABLE_ASYNC_HEADER=true

DEFAULT_PROVIDER=qiniu
```

请勿提交密钥到仓库，避免产生风险与费用。
