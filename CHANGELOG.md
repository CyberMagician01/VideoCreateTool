# Changelog

## 2026-04-09

### Added
- 视频实验室新增图生视频上传交互：拖拽上传、上传进度条、删除已选图片按钮。
- 新增后端接口 `POST /api/video/upload-image`，支持接收本地图片并上传到七牛对象存储后返回公网 URL。
- 新增 Kodo 配置项：`QINIU_KODO_BUCKET`、`QINIU_KODO_PUBLIC_DOMAIN`、`QINIU_KODO_UPLOAD_HOST`。

### Changed
- 创建视频任务与长视频任务时，自动推断并携带 `video_mode`（`text/image/start_end`）。
- 七牛 Kodo 上传失败时增加详细错误透传，便于快速定位问题。
- 针对 "incorrect region" 场景，上传逻辑按七牛返回的机房域名自动重试。

### Fixed
- 修复图生参考图在页面切换或刷新后丢失：项目状态持久化新增 `image_url`、`start_image_url`、`end_image_url`。
- 修复本地地址（localhost/内网）被误用于图生任务导致远端模型无法读取的问题（前端增加 URL 安全校验与提示）。

## 2026-03-21

### Added
- 新增 q3 视频接口路径配置：
  - `/queue/fal-ai/vidu/q3/text-to-video/turbo`
  - `/queue/fal-ai/vidu/q3/image-to-video/turbo`
  - `/queue/fal-ai/vidu/q3/start-end-to-video/turbo`
- 视频实验室新增图片输入项：
  - 图生首帧 URL
  - 首尾帧模式首帧 URL
  - 首尾帧模式尾帧 URL
- 新增分辨率下拉选项：540p、720p、1080p。

### Changed
- 默认视频模型调整为 `viduq3-turbo`。
- 后端视频任务创建逻辑改为按输入自动选路由：
  - 仅文本 -> 文生视频
  - 提供 `image_url` -> 图生视频
  - 提供 `start_image_url + end_image_url` -> 首尾帧生视频
- 视频任务查询结果统一映射为前端可直接消费的结构（包含 `task_id/task_status/video_url`）。
- 单段时长输入范围调整为 `1-16` 秒。

### Fixed
- 修复七牛视频网关路径不匹配导致的 `not found or method not allowed` 问题。
- 修复不同接口响应格式差异导致的任务状态显示异常。
