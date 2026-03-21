# Changelog

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
